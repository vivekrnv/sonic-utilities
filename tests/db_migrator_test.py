import os
import pytest
import sys

from swsssdk import SonicV2Connector
from sonic_py_common import device_info

from .mock_tables import dbconnector

import config.main as config
from utilities_common.db import Db

test_path = os.path.dirname(os.path.abspath(__file__))
mock_db_path = os.path.join(test_path, "db_migrator_input")
modules_path = os.path.dirname(test_path)
scripts_path = os.path.join(modules_path, "scripts")
sys.path.insert(0, test_path)
sys.path.insert(0, modules_path)
sys.path.insert(0, scripts_path)

os.environ["PATH"] += os.pathsep + scripts_path

def get_sonic_version_info_mlnx():
    return {'asic_type': 'mellanox'}


class TestMellanoxBufferMigrator(object):
    @classmethod
    def setup_class(cls):
        cls.config_db_tables_to_verify = ['BUFFER_POOL', 'BUFFER_PROFILE', 'BUFFER_PG', 'DEFAULT_LOSSLESS_BUFFER_PARAMETER', 'LOSSLESS_TRAFFIC_PATTERN', 'VERSIONS', 'DEVICE_METADATA']
        cls.appl_db_tables_to_verify = ['BUFFER_POOL_TABLE:*', 'BUFFER_PROFILE_TABLE:*', 'BUFFER_PG_TABLE:*', 'BUFFER_QUEUE:*', 'BUFFER_PORT_INGRESS_PROFILE_LIST:*', 'BUFFER_PORT_EGRESS_PROFILE_LIST:*']
        cls.warm_reboot_from_version = 'version_1_0_5'
        cls.warm_reboot_to_version = 'version_2_0_0'

        cls.version_list = ['version_1_0_1', 'version_1_0_2', 'version_1_0_3', 'version_1_0_4', 'version_1_0_5', 'version_2_0_0']

        os.environ['UTILITIES_UNIT_TESTING'] = "2"

    @classmethod
    def teardown_class(cls):
        os.environ['UTILITIES_UNIT_TESTING'] = "0"

    def make_db_name_by_sku_topo_version(self, sku, topo, version):
        return sku + '-' + topo + '-' + version

    def mock_dedicated_config_db(self, filename):
        jsonfile = os.path.join(mock_db_path, 'config_db', filename)
        dbconnector.dedicated_dbs['CONFIG_DB'] = jsonfile
        db = Db()
        return db

    def mock_dedicated_state_db(self):
        dbconnector.dedicated_dbs['STATE_DB'] = os.path.join(mock_db_path, 'state_db')

    def mock_dedicated_appl_db(self, filename):
        jsonfile = os.path.join(mock_db_path, 'appl_db', filename)
        dbconnector.dedicated_dbs['APPL_DB'] = jsonfile
        appl_db = SonicV2Connector(host='127.0.0.1')
        appl_db.connect(appl_db.APPL_DB)
        return appl_db

    def clear_dedicated_mock_dbs(self):
        dbconnector.dedicated_dbs['CONFIG_DB'] = None
        dbconnector.dedicated_dbs['STATE_DB'] = None
        dbconnector.dedicated_dbs['APPL_DB'] = None

    def check_config_db(self, result, expected):
        for table in self.config_db_tables_to_verify:
            assert result.get_table(table) == expected.get_table(table)

    def check_appl_db(self, result, expected):
        for table in self.appl_db_tables_to_verify:
            keys = expected.keys(expected.APPL_DB, table)
            if keys is None:
                continue
            for key in keys:
                assert expected.get_all(expected.APPL_DB, key) == result.get_all(result.APPL_DB, key)

    def advance_version_for_expected_database(self, migrated_db, expected_db):
        # In case there are new db versions greater than the latest one that mellanox buffer migrator is interested,
        # we just advance the database version in the expected database to make the test pass
        expected_dbversion = expected_db.get_entry('VERSIONS', 'DATABASE')
        dbmgtr_dbversion = migrated_db.get_entry('VERSIONS', 'DATABASE')
        if expected_dbversion and dbmgtr_dbversion:
            if expected_dbversion['VERSION'] == self.version_list[-1] and dbmgtr_dbversion['VERSION'] > expected_dbversion['VERSION']:
                expected_dbversion['VERSION'] = dbmgtr_dbversion['VERSION']
                expected_db.set_entry('VERSIONS', 'DATABASE', expected_dbversion)

    @pytest.mark.parametrize('scenario',
                             ['empty-config',
                              'non-default-config',
                              'non-default-xoff',
                              'non-default-lossless-profile-in-pg',
                              'non-default-lossy-profile-in-pg',
                              'non-default-pg'
                             ])
    def test_mellanox_buffer_migrator_negative_cold_reboot(self, scenario):
        db_before_migrate = scenario + '-input'
        db_after_migrate = scenario + '-expected'
        device_info.get_sonic_version_info = get_sonic_version_info_mlnx
        db = self.mock_dedicated_config_db(db_before_migrate)
        import db_migrator
        dbmgtr = db_migrator.DBMigrator(None)
        dbmgtr.migrate()
        expected_db = self.mock_dedicated_config_db(db_after_migrate)
        self.advance_version_for_expected_database(dbmgtr.configDB, expected_db.cfgdb)
        self.check_config_db(dbmgtr.configDB, expected_db.cfgdb)
        assert not dbmgtr.mellanox_buffer_migrator.is_buffer_config_default

    @pytest.mark.parametrize('sku_version',
                             [('ACS-MSN2700', 'version_1_0_1'),
                              ('Mellanox-SN2700', 'version_1_0_1'),
                              ('Mellanox-SN2700-Single-Pool', 'version_1_0_4'),
                              ('Mellanox-SN2700-C28D8', 'version_1_0_1'),
                              ('Mellanox-SN2700-C28D8-Single-Pool', 'version_1_0_4'),
                              ('Mellanox-SN2700-D48C8', 'version_1_0_1'),
                              ('Mellanox-SN2700-D48C8-Single-Pool', 'version_1_0_4'),
                              ('Mellanox-SN2700-D40C8S8', 'version_1_0_5'),
                              ('ACS-MSN3700', 'version_1_0_2'),
                              ('ACS-MSN3800', 'version_1_0_5'),
                              ('Mellanox-SN3800-C64', 'version_1_0_5'),
                              ('Mellanox-SN3800-D112C8', 'version_1_0_5'),
                              ('Mellanox-SN3800-D24C52', 'version_1_0_5'),
                              ('Mellanox-SN3800-D28C50', 'version_1_0_5'),
                              ('ACS-MSN4700', 'version_1_0_4')
                             ])
    @pytest.mark.parametrize('topo', ['t0', 't1'])
    def test_mellanox_buffer_migrator_for_cold_reboot(self, sku_version, topo):
        device_info.get_sonic_version_info = get_sonic_version_info_mlnx
        sku, start_version = sku_version
        version = start_version
        start_index = self.version_list.index(start_version)

        # start_version represents the database version from which the SKU is supported
        # For each SKU,
        # migration from any version between start_version and the current version (inclusive) to the current version will be verified
        for version in self.version_list[start_index:]:
            _ = self.mock_dedicated_config_db(self.make_db_name_by_sku_topo_version(sku, topo, version))
            import db_migrator
            dbmgtr = db_migrator.DBMigrator(None)
            dbmgtr.migrate()
            # Eventually, the config db should be migrated to the latest version
            expected_db = self.mock_dedicated_config_db(self.make_db_name_by_sku_topo_version(sku, topo, self.version_list[-1]))
            self.advance_version_for_expected_database(dbmgtr.configDB, expected_db.cfgdb)
            self.check_config_db(dbmgtr.configDB, expected_db.cfgdb)
            assert dbmgtr.mellanox_buffer_migrator.is_buffer_config_default

        self.clear_dedicated_mock_dbs()

    def mellanox_buffer_migrator_warm_reboot_runner(self, input_config_db, input_appl_db, expected_config_db, expected_appl_db, is_buffer_config_default_expected):
        expected_config_db = self.mock_dedicated_config_db(expected_config_db)
        expected_appl_db = self.mock_dedicated_appl_db(expected_appl_db)
        self.mock_dedicated_state_db()
        _ = self.mock_dedicated_config_db(input_config_db)
        _ = self.mock_dedicated_appl_db(input_appl_db)

        import db_migrator
        dbmgtr = db_migrator.DBMigrator(None)
        dbmgtr.migrate()
        self.advance_version_for_expected_database(dbmgtr.configDB, expected_config_db.cfgdb)
        assert dbmgtr.mellanox_buffer_migrator.is_buffer_config_default == is_buffer_config_default_expected
        self.check_config_db(dbmgtr.configDB, expected_config_db.cfgdb)
        self.check_appl_db(dbmgtr.appDB, expected_appl_db)

        self.clear_dedicated_mock_dbs()

    @pytest.mark.parametrize('sku',
                             ['ACS-MSN2700',
                              'Mellanox-SN2700', 'Mellanox-SN2700-Single-Pool', 'Mellanox-SN2700-C28D8', 'Mellanox-SN2700-C28D8-Single-Pool',
                              'Mellanox-SN2700-D48C8', 'Mellanox-SN2700-D48C8-Single-Pool',
                              'Mellanox-SN2700-D40C8S8',
                              'ACS-MSN3700',
                              'ACS-MSN3800',
                              'Mellanox-SN3800-C64',
                              'Mellanox-SN3800-D112C8',
                              'Mellanox-SN3800-D24C52',
                              'Mellanox-SN3800-D28C50',
                              'ACS-MSN4700'
                             ])
    @pytest.mark.parametrize('topo', ['t0', 't1'])
    def test_mellanox_buffer_migrator_for_warm_reboot(self, sku, topo):
        device_info.get_sonic_version_info = get_sonic_version_info_mlnx
        # Eventually, the config db should be migrated to the latest version
        expected_db_name = self.make_db_name_by_sku_topo_version(sku, topo, self.warm_reboot_to_version)
        input_db_name = self.make_db_name_by_sku_topo_version(sku, topo, self.warm_reboot_from_version)
        self.mellanox_buffer_migrator_warm_reboot_runner(input_db_name, input_db_name, expected_db_name, expected_db_name, True)

    def test_mellanox_buffer_migrator_negative_nondefault_for_warm_reboot(self):
        device_info.get_sonic_version_info = get_sonic_version_info_mlnx
        expected_config_db = 'non-default-config-expected'
        expected_appl_db = 'non-default-expected'
        input_config_db = 'non-default-config-input'
        input_appl_db = 'non-default-input'
        self.mellanox_buffer_migrator_warm_reboot_runner(input_config_db, input_appl_db, expected_config_db, expected_appl_db, False)
