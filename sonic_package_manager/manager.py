#!/usr/bin/env python

import contextlib
import functools
import os
import pkgutil
import tempfile
from inspect import signature
from typing import Any, Iterable, Callable, Dict, Optional

import docker
import filelock
from sonic_py_common import device_info

from sonic_package_manager import utils
from sonic_package_manager.constraint import (
    VersionConstraint,
    PackageConstraint
)
from sonic_package_manager.database import (
    PACKAGE_MANAGER_LOCK_FILE,
    PackageDatabase
)
from sonic_package_manager.dockerapi import DockerApi
from sonic_package_manager.errors import (
    PackageManagerError,
    PackageDependencyError,
    PackageComponentDependencyError,
    PackageConflictError,
    PackageComponentConflictError,
    PackageInstallationError,
    PackageSonicRequirementError,
    PackageUninstallationError,
    PackageUpgradeError
)
from sonic_package_manager.logger import log
from sonic_package_manager.metadata import MetadataResolver
from sonic_package_manager.package import Package
from sonic_package_manager.progress import ProgressManager
from sonic_package_manager.reference import PackageReference
from sonic_package_manager.registry import RegistryResolver
from sonic_package_manager.service_creator.creator import (
    ServiceCreator,
    run_command
)
from sonic_package_manager.service_creator.feature import FeatureRegistry
from sonic_package_manager.service_creator.sonic_db import SonicDB
from sonic_package_manager.service_creator.utils import in_chroot
from sonic_package_manager.source import (
    PackageSource,
    LocalSource,
    RegistrySource,
    TarballSource
)
from sonic_package_manager.utils import DockerReference
from sonic_package_manager.version import (
    Version,
    VersionRange,
    version_to_tag,
    tag_to_version
)


@contextlib.contextmanager
def failure_ignore(ignore: bool):
    """ Ignores failures based on parameter passed. """

    try:
        yield
    except Exception as err:
        if ignore:
            log.warning(f'ignoring error {err}')
        else:
            raise


def under_lock(func: Callable) -> Callable:
    """ Execute operations under lock. """

    @functools.wraps(func)
    def wrapped_function(*args, **kwargs):
        self = args[0]
        with self.lock:
            return func(*args, **kwargs)

    return wrapped_function


def opt_check(func: Callable) -> Callable:
    """ Check kwargs for function. """

    @functools.wraps(func)
    def wrapped_function(*args, **kwargs):
        sig = signature(func)
        unsupported_opts = [opt for opt in kwargs if opt not in sig.parameters]
        if unsupported_opts:
            raise PackageManagerError(
                f'Unsupported options {unsupported_opts} for {func.__name__}'
            )
        return func(*args, **kwargs)

    return wrapped_function


def rollback(func, *args, **kwargs):
    """ Used in rollback callbacks to ignore failure
    but proceed with rollback. Error will be printed
    but not fail the whole procedure of rollback. """

    @functools.wraps(func)
    def wrapper():
        try:
            func(*args, **kwargs)
        except Exception as err:
            log.error(f'failed in rollback: {err}')

    return wrapper


def package_constraint_to_reference(constraint: PackageConstraint) -> PackageReference:
    package_name, version_constraint = constraint.name, constraint.constraint
    # Allow only specific version for now.
    # Later we can improve package manager to support
    # installing packages using expressions like 'package>1.0.0'
    if version_constraint == VersionRange():  # empty range means any version
        return PackageReference(package_name, None)
    if not isinstance(version_constraint, Version):
        raise PackageManagerError(f'Can only install specific version. '
                                  f'Use only following expression "{package_name}=<version>" '
                                  f'to install specific version')
    return PackageReference(package_name, version_to_tag(version_constraint))


def parse_reference_expression(expression):
    try:
        return package_constraint_to_reference(PackageConstraint.parse(expression))
    except ValueError:
        # if we failed to parse the expression as constraint expression
        # we will try to parse it as reference
        return PackageReference.parse(expression)


def validate_package_base_os_constraints(package: Package, sonic_version_info: Dict[str, str]):
    """ Verify that all dependencies on base OS components are met.
    Args:
        package: Package to check constraints for.
        sonic_version_info: SONiC components version information.
    Raises:
        PackageSonicRequirementError: in case dependency is not satisfied.
    """

    base_os_constraints = package.manifest['package']['base-os'].components
    for component, constraint in base_os_constraints.items():
        if component not in sonic_version_info:
            raise PackageSonicRequirementError(package.name, component, constraint)

        version = Version.parse(sonic_version_info[component])

        if not constraint.allows_all(version):
            raise PackageSonicRequirementError(package.name, component, constraint, version)


def validate_package_tree(packages: Dict[str, Package]):
    """ Verify that all dependencies are met in all packages passed to this function.
    Args:
        packages: list of packages to check
    Raises:
        PackageDependencyError: if dependency is missing
        PackageConflictError: if there is a conflict between packages
    """

    for name, package in packages.items():
        log.debug(f'checking dependencies for {name}')
        for dependency in package.manifest['package']['depends']:
            dependency_package = packages.get(dependency.name)
            if dependency_package is None:
                raise PackageDependencyError(package.name, dependency)

            installed_version = dependency_package.version
            log.debug(f'dependency package is installed {dependency.name}: {installed_version}')
            if not dependency.constraint.allows_all(installed_version):
                raise PackageDependencyError(package.name, dependency, installed_version)

            dependency_components = dependency.components
            if not dependency_components:
                dependency_components = {}
                for component, version in package.components.items():
                    implicit_constraint = VersionConstraint.parse(f'^{version.major}.{version.minor}.0')
                    dependency_components[component] = implicit_constraint

            for component, constraint in dependency_components.items():
                if component not in dependency_package.components:
                    raise PackageComponentDependencyError(package.name, dependency,
                                                          component, constraint)

                component_version = dependency_package.components[component]
                log.debug(f'dependency package {dependency.name}: '
                          f'component {component} version is {component_version}')

                if not constraint.allows_all(component_version):
                    raise PackageComponentDependencyError(package.name, dependency, component,
                                                          constraint, component_version)

        log.debug(f'checking conflicts for {name}')
        for conflict in package.manifest['package']['breaks']:
            conflicting_package = packages.get(conflict.name)
            if conflicting_package is None:
                continue

            installed_version = conflicting_package.version
            log.debug(f'conflicting package is installed {conflict.name}: {installed_version}')
            if conflict.constraint.allows_all(installed_version):
                raise PackageConflictError(package.name, conflict, installed_version)

            for component, constraint in conflicting_package.components.items():
                if component not in conflicting_package.components:
                    continue

                component_version = conflicting_package.components[component]
                log.debug(f'conflicting package {dependency.name}: '
                          f'component {component} version is {component_version}')

                if constraint.allows_all(component_version):
                    raise PackageComponentConflictError(package.name, dependency, component,
                                                        constraint, component_version)


def validate_package_cli_can_be_skipped(package: Package, skip: bool):
    """ Checks whether package CLI installation can be skipped.

    Args:
        package: Package to validate
        skip: Whether to skip installing CLI

    Raises:
        PackageManagerError

    """

    if package.manifest['cli']['mandatory'] and skip:
        raise PackageManagerError(f'CLI is mandatory for package {package.name} '
                                  f'but it was requested to be not installed')
    elif skip:
        log.warning(f'Package {package.name} CLI plugin will not be installed')


class PackageManager:
    """ SONiC Package Manager. This class provides public API
    for sonic_package_manager python library. It has functionality
    for installing, uninstalling, updating SONiC packages as well as
    retrieving information about the packages from different sources. """

    def __init__(self,
                 docker_api: DockerApi,
                 registry_resolver: RegistryResolver,
                 database: PackageDatabase,
                 metadata_resolver: MetadataResolver,
                 service_creator: ServiceCreator,
                 device_information: Any,
                 lock: filelock.FileLock):
        """ Initialize PackageManager. """

        self.lock = lock
        self.docker = docker_api
        self.registry_resolver = registry_resolver
        self.database = database
        self.metadata_resolver = metadata_resolver
        self.service_creator = service_creator
        self.feature_registry = service_creator.feature_registry
        self.is_multi_npu = device_information.is_multi_npu()
        self.num_npus = device_information.get_num_npus()
        self.version_info = device_information.get_sonic_version_info()

    @under_lock
    def add_repository(self, *args, **kwargs):
        """ Add repository to package database
        and commit database content.

        Args:
            args: Arguments to pass to PackageDatabase.add_package
            kwargs: Keyword arguments to pass to PackageDatabase.add_package
        """

        self.database.add_package(*args, **kwargs)
        self.database.commit()

    @under_lock
    def remove_repository(self, name: str):
        """ Remove repository from package database
        and commit database content.

        Args:
            name: package name
        """

        self.database.remove_package(name)
        self.database.commit()

    @under_lock
    def install(self,
                expression: Optional[str] = None,
                repotag: Optional[str] = None,
                tarball: Optional[str] = None,
                **kwargs):
        """ Install/Upgrade SONiC Package from either an expression
        representing the package and its version, repository and tag or
        digest in same format as "docker pulL" accepts or an image tarball path.

        Args:
            expression: SONiC Package reference expression
            repotag: Install/Upgrade from REPO[:TAG][@DIGEST]
            tarball: Install/Upgrade from tarball, path to tarball file
            kwargs: Install/Upgrade options for self.install_from_source
        Raises:
            PackageManagerError
        """

        source = self.get_package_source(expression, repotag, tarball)
        package = source.get_package()

        if self.is_installed(package.name):
            self.upgrade_from_source(source, **kwargs)
        else:
            self.install_from_source(source, **kwargs)

    @under_lock
    @opt_check
    def install_from_source(self,
                            source: PackageSource,
                            force=False,
                            enable=False,
                            default_owner='local',
                            skip_host_plugins=False):
        """ Install SONiC Package from source represented by PackageSource.
        This method contains the logic of package installation.

        Args:
            source: SONiC Package source.
            force: Force the installation.
            enable: If True the installed feature package will be enabled.
            default_owner: Owner of the installed package.
            skip_host_plugins: Skip CLI plugin installation.
        Raises:
            PackageManagerError
        """

        package = source.get_package()
        name = package.name

        with failure_ignore(force):
            if self.is_installed(name):
                raise PackageInstallationError(f'{name} is already installed')

        version = package.manifest['package']['version']
        feature_state = 'enabled' if enable else 'disabled'
        installed_packages = self._get_installed_packages_and(package)

        with failure_ignore(force):
            validate_package_base_os_constraints(package, self.version_info)
            validate_package_tree(installed_packages)
            validate_package_cli_can_be_skipped(package, skip_host_plugins)

        # After all checks are passed we proceed to actual installation

        # When installing package from a tarball or directly from registry
        # package name may not be in database.
        if not self.database.has_package(package.name):
            self.database.add_package(package.name, package.repository)

        try:
            with contextlib.ExitStack() as exits:
                source.install(package)
                exits.callback(rollback(source.uninstall, package))

                self.service_creator.create(package, state=feature_state, owner=default_owner)
                exits.callback(rollback(self.service_creator.remove, package))

                if not skip_host_plugins:
                    self._install_cli_plugins(package)
                    exits.callback(rollback(self._uninstall_cli_plugins, package))

                exits.pop_all()
        except Exception as err:
            raise PackageInstallationError(f'Failed to install {package.name}: {err}')
        except KeyboardInterrupt:
            raise

        package.entry.installed = True
        package.entry.version = version
        self.database.update_package(package.entry)
        self.database.commit()

    @under_lock
    @opt_check
    def uninstall(self, name: str, force=False):
        """ Uninstall SONiC Package referenced by name. The uninstallation
        can be forced if force argument is True.

        Args:
            name: SONiC Package name.
            force: Force the installation.
        Raises:
            PackageManagerError
        """

        with failure_ignore(force):
            if not self.is_installed(name):
                raise PackageUninstallationError(f'{name} is not installed')

        package = self.get_installed_package(name)
        service_name = package.manifest['service']['name']

        with failure_ignore(force):
            if self.feature_registry.is_feature_enabled(service_name):
                raise PackageUninstallationError(
                    f'{service_name} is enabled. Disable the feature first')

        if package.built_in:
            raise PackageUninstallationError(
                f'Cannot uninstall built-in package {package.name}')

        installed_packages = self._get_installed_packages_except(package)

        with failure_ignore(force):
            validate_package_tree(installed_packages)

        # After all checks are passed we proceed to actual uninstallation

        try:
            self._uninstall_cli_plugins(package)
            self.service_creator.remove(package)

            # Clean containers based on this image
            containers = self.docker.ps(filters={'ancestor': package.image_id},
                                        all=True)
            for container in containers:
                self.docker.rm(container.id, force=True)

            self.docker.rmi(package.image_id, force=True)
            package.entry.image_id = None
        except Exception as err:
            raise PackageUninstallationError(
                f'Failed to uninstall {package.name}: {err}'
            )

        package.entry.installed = False
        package.entry.version = None
        self.database.update_package(package.entry)
        self.database.commit()

    @under_lock
    @opt_check
    def upgrade_from_source(self,
                            source: PackageSource,
                            force=False,
                            skip_host_plugins=False,
                            allow_downgrade=False):
        """ Upgrade SONiC Package to a version the package reference
        expression specifies. Can force the upgrade if force parameter
        is True. Force can allow a package downgrade.

        Args:
            source: SONiC Package source
            force: Force the upgrade.
            skip_host_plugins: Skip host OS plugins installation.
            allow_downgrade: Flag to allow package downgrade.
        Raises:
            PackageManagerError
        """

        new_package = source.get_package()
        name = new_package.name

        with failure_ignore(force):
            if not self.is_installed(name):
                raise PackageUpgradeError(f'{name} is not installed')

        old_package = self.get_installed_package(name)

        if old_package.built_in:
            raise PackageUpgradeError(
                f'Cannot upgrade built-in package {old_package.name}'
            )

        old_feature = old_package.manifest['service']['name']
        new_feature = new_package.manifest['service']['name']
        old_version = old_package.manifest['package']['version']
        new_version = new_package.manifest['package']['version']

        with failure_ignore(force):
            if old_version == new_version:
                raise PackageUpgradeError(f'{new_version} is already installed')

            # TODO: Not all packages might support downgrade.
            # We put a check here but we understand that for some packages
            # the downgrade might be safe to do. There can be a variable in manifest
            # describing package downgrade ability or downgrade-able versions.
            if new_version < old_version and not allow_downgrade:
                raise PackageUpgradeError(
                    f'Request to downgrade from {old_version} to {new_version}. '
                    f'Downgrade might be not supported by the package'
                )

        # remove currently installed package from the list
        installed_packages = self._get_installed_packages_and(new_package)

        with failure_ignore(force):
            validate_package_base_os_constraints(new_package, self.version_info)
            validate_package_tree(installed_packages)
            validate_package_cli_can_be_skipped(new_package, skip_host_plugins)

        # After all checks are passed we proceed to actual upgrade

        try:
            with contextlib.ExitStack() as exits:
                self._uninstall_cli_plugins(old_package)
                exits.callback(rollback(self._install_cli_plugins, old_package))

                source.install(new_package)
                exits.callback(rollback(source.uninstall, new_package))

                if self.feature_registry.is_feature_enabled(old_feature):
                    self._systemctl_action(old_package, 'stop')
                    exits.callback(rollback(self._systemctl_action,
                                            old_package, 'start'))

                self.service_creator.remove(old_package, deregister_feature=False)
                exits.callback(rollback(self.service_creator.create,
                                        old_package, register_feature=False))

                # Clean containers based on the old image
                containers = self.docker.ps(filters={'ancestor': old_package.image_id},
                                            all=True)
                for container in containers:
                    self.docker.rm(container.id, force=True)

                self.service_creator.create(new_package, register_feature=False)
                exits.callback(rollback(self.service_creator.remove, new_package,
                                        register_feature=False))

                if self.feature_registry.is_feature_enabled(new_feature):
                    self._systemctl_action(new_package, 'start')
                    exits.callback(rollback(self._systemctl_action,
                                            new_package, 'stop'))

                if not skip_host_plugins:
                    self._install_cli_plugins(new_package)
                    exits.callback(rollback(self._uninstall_cli_plugin, old_package))

                self.docker.rmi(old_package.image_id, force=True)

                exits.pop_all()
        except Exception as err:
            raise PackageUpgradeError(f'Failed to upgrade {new_package.name}: {err}')
        except KeyboardInterrupt:
            raise

        new_package_entry = new_package.entry
        new_package_entry.installed = True
        new_package_entry.version = new_version
        self.database.update_package(new_package_entry)
        self.database.commit()

    @under_lock
    @opt_check
    def reset(self, name: str, force: bool = False, skip_host_plugins: bool = False):
        """ Reset package to defaults version

        Args:
            name: SONiC Package name.
            force: Force the installation.
            skip_host_plugins: Skip host plugins installation.
        Raises:
            PackageManagerError
        """

        with failure_ignore(force):
            if not self.is_installed(name):
                raise PackageManagerError(f'{name} is not installed')

        package = self.get_installed_package(name)
        default_reference = package.entry.default_reference
        if default_reference is None:
            raise PackageManagerError(f'package {name} has no default reference')

        package_ref = PackageReference(name, default_reference)
        source = self.get_package_source(package_ref=package_ref)
        self.upgrade_from_source(source, force=force,
                                 allow_downgrade=True,
                                 skip_host_plugins=skip_host_plugins)

    @under_lock
    def migrate_packages(self,
                         old_package_database: PackageDatabase,
                         dockerd_sock: Optional[str] = None):
        """
        Migrate packages from old database. This function can do a comparison between 
        current database and the database passed in as argument. If the package is 
        missing in the current database it will be added. If the package is installed 
        in the passed database and in the current it is not installed it will be 
        installed with a passed database package version. If the package is installed 
        in the passed database and it is installed in the current database but with 
        older version the package will be upgraded to the never version. If the package 
        is installed in the passed database and in the current it is installed but with 
        never version - no actions are taken. If dockerd_sock parameter is passed, the 
        migration process will use loaded images from docker library of the currently 
        installed image.

        Args:
            old_package_database: SONiC Package Database to migrate packages from.
            dockerd_sock: Path to dockerd socket.
        Raises:
            PackageManagerError
        """

        self._migrate_package_database(old_package_database)

        def migrate_package(old_package_entry,
                            new_package_entry):
            """ Migrate package routine

            Args:
                old_package_entry: Entry in old package database.
                new_package_entry: Entry in new package database.
            """

            name = new_package_entry.name
            version = new_package_entry.version

            if dockerd_sock:
                # dockerd_sock is defined, so use docked_sock to connect to
                # dockerd and fetch package image from it.
                log.info(f'installing {name} from old docker library')
                docker_api = DockerApi(docker.DockerClient(base_url=f'unix://{dockerd_sock}'))

                image = docker_api.get_image(old_package_entry.image_id)

                with tempfile.NamedTemporaryFile('wb') as file:
                    for chunk in image.save(named=True):
                        file.write(chunk)

                    self.install(tarball=file.name)
            else:
                log.info(f'installing {name} version {version}')

                self.install(f'{name}={version}')

        # TODO: Topological sort packages by their dependencies first.
        for old_package in old_package_database:
            if not old_package.installed or old_package.built_in:
                continue

            log.info(f'migrating package {old_package.name}')

            new_package = self.database.get_package(old_package.name)

            if new_package.installed:
                if old_package.version > new_package.version:
                    log.info(f'{old_package.name} package version is greater '
                             f'then installed in new image: '
                             f'{old_package.version} > {new_package.version}')
                    log.info(f'upgrading {new_package.name} to {old_package.version}')
                    new_package.version = old_package.version
                    migrate_package(old_package, new_package)
                else:
                    log.info(f'skipping {new_package.name} as installed version is newer')
            elif new_package.default_reference is not None:
                new_package_ref = PackageReference(new_package.name, new_package.default_reference)
                package_source = self.get_package_source(package_ref=new_package_ref)
                package = package_source.get_package()
                new_package_default_version = package.manifest['package']['version']
                if old_package.version > new_package_default_version:
                    log.info(f'{old_package.name} package version is lower '
                             f'then the default in new image: '
                             f'{old_package.version} > {new_package_default_version}')
                    new_package.version = old_package.version
                    migrate_package(old_package, new_package)
                else:
                    self.install(f'{new_package.name}={new_package_default_version}')
            else:
                # No default version and package is not installed.
                # Migrate old package same version.
                new_package.version = old_package.version
                migrate_package(old_package, new_package)

            self.database.commit()

    def get_installed_package(self, name: str) -> Package:
        """ Get installed package by name.

        Args:
            name: package name.
        Returns:
            Package object.
        """

        package_entry = self.database.get_package(name)
        source = LocalSource(package_entry,
                             self.database,
                             self.docker,
                             self.metadata_resolver)
        return source.get_package()

    def get_package_source(self,
                           package_expression: Optional[str] = None,
                           repository_reference: Optional[str] = None,
                           tarboll_path: Optional[str] = None,
                           package_ref: Optional[PackageReference] = None):
        """ Returns PackageSource object based on input source.

        Args:
             package_expression: SONiC Package expression string
             repository_reference: Install from REPO[:TAG][@DIGEST]
             tarboll_path: Install from image tarball
             package_ref: Package reference object
        Returns:
            SONiC Package object.
         Raises:
             ValueError if no source specified.
        """

        if package_expression:
            ref = parse_reference_expression(package_expression)
            return self.get_package_source(package_ref=ref)
        elif repository_reference:
            repo_ref = DockerReference.parse(repository_reference)
            repository = repo_ref['name']
            reference = repo_ref['tag'] or repo_ref['digest']
            reference = reference or 'latest'
            return RegistrySource(repository,
                                  reference,
                                  self.database,
                                  self.docker,
                                  self.metadata_resolver)
        elif tarboll_path:
            return TarballSource(tarboll_path,
                                 self.database,
                                 self.docker,
                                 self.metadata_resolver)
        elif package_ref:
            package_entry = self.database.get_package(package_ref.name)

            # Determine the reference if not specified.
            # If package is installed assume the installed
            # one is requested, otherwise look for default
            # reference defined for this package. In case package
            # does not have a default reference raise an error.
            if package_ref.reference is None:
                if package_entry.installed:
                    return LocalSource(package_entry,
                                       self.database,
                                       self.docker,
                                       self.metadata_resolver)
                if package_entry.default_reference is not None:
                    package_ref.reference = package_entry.default_reference
                else:
                    raise PackageManagerError(f'No default reference tag. '
                                              f'Please specify the version or tag explicitly')

            return RegistrySource(package_entry.repository,
                                  package_ref.reference,
                                  self.database,
                                  self.docker,
                                  self.metadata_resolver)
        else:
            raise ValueError('No package source provided')

    def get_package_available_versions(self,
                                       name: str,
                                       all: bool = False) -> Iterable:
        """ Returns a list of available versions for package.

        Args:
            name: Package name.
            all: If set to True will return all tags including
                 those which do not follow semantic versioning.
        Returns:
            List of versions
        """
        package_info = self.database.get_package(name)
        registry = self.registry_resolver.get_registry_for(package_info.repository)
        available_tags = registry.tags(package_info.repository)

        def is_semantic_ver_tag(tag: str) -> bool:
            try:
                tag_to_version(tag)
                return True
            except ValueError:
                pass
            return False

        if all:
            return available_tags

        return map(tag_to_version, filter(is_semantic_ver_tag, available_tags))

    def is_installed(self, name: str) -> bool:
        """ Returns boolean whether a package called name is installed.

        Args:
            name: Package name.
        Returns:
            True if package is installed, False otherwise.
        """

        if not self.database.has_package(name):
            return False
        package_info = self.database.get_package(name)
        return package_info.installed

    def get_installed_packages(self) -> Dict[str, Package]:
        """ Returns a dictionary of installed packages where
        keys are package names and values are package objects.

        Returns:
            Installed packages dictionary.
        """

        return {
            entry.name: self.get_installed_package(entry.name)
            for entry in self.database if entry.installed
        }

    def _migrate_package_database(self, old_package_database: PackageDatabase):
        """ Performs part of package migration process.
        For every package in  old_package_database that is not listed in current
        database add a corresponding entry to current database. """

        for package in old_package_database:
            if not self.database.has_package(package.name):
                self.database.add_package(package.name,
                                          package.repository,
                                          package.description,
                                          package.default_reference)

    def _get_installed_packages_and(self, package: Package) -> Dict[str, Package]:
        """ Returns a dictionary of installed packages with their names as keys
        adding a package provided in the argument. """

        packages = self.get_installed_packages()
        packages[package.name] = package
        return packages

    def _get_installed_packages_except(self, package: Package) -> Dict[str, Package]:
        """ Returns a dictionary of installed packages with their names as keys
        removing a package provided in the argument. """

        packages = self.get_installed_packages()
        packages.pop(package.name)
        return packages

    # TODO: Replace with "config feature" command.
    # The problem with current "config feature" command
    # is that it is asynchronous, thus can't be used
    # for package upgrade purposes where we need to wait
    # till service stops before upgrading docker image.
    # It would be really handy if we could just call
    # something like: "config feature state <name> <state> --wait"
    # instead of operating on systemd service since
    # this is basically a duplicated code from "hostcfgd".
    def _systemctl_action(self, package: Package, action: str):
        """ Execute systemctl action for a service supporting
        multi-asic services. """

        name = package.manifest['service']['name']
        host_service = package.manifest['service']['host-service']
        asic_service = package.manifest['service']['asic-service']
        single_instance = host_service or (asic_service and not self.is_multi_npu)
        multi_instance = asic_service and self.is_multi_npu

        if in_chroot():
            return

        if single_instance:
            run_command(f'systemctl {action} {name}')
        if multi_instance:
            for npu in range(self.num_npus):
                run_command(f'systemctl {action} {name}@{npu}')

    @staticmethod
    def _get_cli_plugin_name(package: Package):
        return utils.make_python_identifier(package.name) + '.py'

    @classmethod
    def _get_cli_plugin_path(cls, package: Package, command):
        pkg_loader = pkgutil.get_loader(f'{command}.plugins')
        if pkg_loader is None:
            raise PackageManagerError(f'Failed to get plugins path for {command} CLI')
        plugins_pkg_path = os.path.dirname(pkg_loader.path)
        return os.path.join(plugins_pkg_path, cls._get_cli_plugin_name(package))

    def _install_cli_plugins(self, package: Package):
        for command in ('show', 'config', 'clear'):
            self._install_cli_plugin(package, command)

    def _uninstall_cli_plugins(self, package: Package):
        for command in ('show', 'config', 'clear'):
            self._uninstall_cli_plugin(package, command)

    def _install_cli_plugin(self, package: Package, command: str):
        image_plugin_path = package.manifest['cli'][command]
        if not image_plugin_path:
            return
        host_plugin_path = self._get_cli_plugin_path(package, command)
        self.docker.extract(package.entry.image_id, image_plugin_path, host_plugin_path)

    def _uninstall_cli_plugin(self, package: Package, command: str):
        image_plugin_path = package.manifest['cli'][command]
        if not image_plugin_path:
            return
        host_plugin_path = self._get_cli_plugin_path(package, command)
        if os.path.exists(host_plugin_path):
            os.remove(host_plugin_path)

    @staticmethod
    def get_manager() -> 'PackageManager':
        """ Creates and returns PackageManager instance.

        Returns:
            PackageManager
        """

        docker_api = DockerApi(docker.from_env())
        registry_resolver = RegistryResolver()
        return PackageManager(DockerApi(docker.from_env(), ProgressManager()),
                              registry_resolver,
                              PackageDatabase.from_file(),
                              MetadataResolver(docker_api, registry_resolver),
                              ServiceCreator(FeatureRegistry(SonicDB), SonicDB),
                              device_info,
                              filelock.FileLock(PACKAGE_MANAGER_LOCK_FILE, timeout=0))
