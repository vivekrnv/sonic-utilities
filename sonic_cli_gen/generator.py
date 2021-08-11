#!/usr/bin/env python

import os
import pkgutil
import jinja2

from sonic_cli_gen.yang_parser import YangParser

templates_path = '/usr/share/sonic/templates/sonic-cli-gen/'


class CliGenerator:
    """ SONiC CLI generator. This class provides public API
    for sonic-cli-gen python library. It can generate config,
    show CLI plugins.

        Attributes:
            loader: the loaded j2 templates
            env: j2 central object
            logger: logger
    """

    def __init__(self, logger):
        """ Initialize CliGenerator. """

        self.loader = jinja2.FileSystemLoader(templates_path)
        self.env = jinja2.Environment(loader=self.loader)
        self.logger = logger

    def generate_cli_plugin(self, cli_group, plugin_name):
        """ Generate click CLI plugin and put it to:
            /usr/local/lib/<python>/dist-packages/<CLI group>/plugins/auto/
        """

        parser = YangParser(yang_model_name=plugin_name,
                            config_db_path='configDB',
                            allow_tbl_without_yang=True,
                            debug=False)
        # yang_dict will be used as an input for templates located in
        # /usr/share/sonic/templates/sonic-cli-gen/
        yang_dict = parser.parse_yang_model()
        plugin_path = get_cli_plugin_path(cli_group, plugin_name + '_yang.py')
        template = self.env.get_template(cli_group + '.py.j2')
        with open(plugin_path, 'w') as plugin_py:
            plugin_py.write(template.render(yang_dict))
            self.logger.info(' Auto-generation successful! Location: {}'.format(plugin_path))

    def remove_cli_plugin(self, cli_group, plugin_name):
        """ Remove CLI plugin from directory:
            /usr/local/lib/<python>/dist-packages/<CLI group>/plugins/auto/
        """
        plugin_path = get_cli_plugin_path(cli_group, plugin_name + '_yang.py')
        if os.path.exists(plugin_path):
            os.remove(plugin_path)
            self.logger.info(' {} was removed.'.format(plugin_path))
        else:
            self.logger.info(' Path {} doest NOT exist!'.format(plugin_path))


def get_cli_plugin_path(command, plugin_name):
    pkg_loader = pkgutil.get_loader(f'{command}.plugins.auto')
    if pkg_loader is None:
        raise Exception(f'Failed to get plugins path for {command} CLI')
    plugins_pkg_path = os.path.dirname(pkg_loader.path)

    return os.path.join(plugins_pkg_path, plugin_name)

