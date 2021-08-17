import os, time
import sys
import pyfakefs
import unittest
from pyfakefs.fake_filesystem_unittest import Patcher
from swsscommon import swsscommon
from utilities_common.general import load_module_from_source
from .shared_state_mock import RedisSingleton, MockConn

curr_test_path = os.path.abspath(os.path.join(os.path.abspath(__file__), "../"))
test_dir_path = os.path.dirname(curr_test_path)
modules_path = os.path.dirname(test_dir_path)
scripts_path = os.path.join(modules_path, 'scripts')
sys.path.insert(0, modules_path)

# Load the file under test
script_path = os.path.join(scripts_path, 'coredump_gen_handler')
cdump_mod = load_module_from_source('coredump_gen_handler', script_path)

# Mock the SonicV2Connector
cdump_mod.SonicV2Connector = MockConn

# Mock Handle to the data inside the Redis
RedisHandle = RedisSingleton.getInstance()


def mock_syslog(level, msg):
    print("SYSLOG: " + msg)

cdump_mod.syslog.syslog = mock_syslog


def set_auto_ts_cfg(**kwargs):
    invoke_ts = kwargs[cdump_mod.CFG_INVOC_TS] if cdump_mod.CFG_INVOC_TS in kwargs else "disabled"
    core_cleanup = kwargs[cdump_mod.CFG_CORE_CLEANUP] if cdump_mod.CFG_CORE_CLEANUP in kwargs else "disabled"
    cooloff = kwargs[cdump_mod.COOLOFF] if cdump_mod.COOLOFF in kwargs else "0"
    core_usage = kwargs[cdump_mod.CFG_CORE_USAGE] if cdump_mod.CFG_CORE_USAGE in kwargs else "0"
    since_cfg = kwargs[cdump_mod.CFG_SINCE] if cdump_mod.CFG_SINCE in kwargs else "None"
    if cdump_mod.CFG_DB not in RedisHandle.data:
        RedisHandle.data[cdump_mod.CFG_DB] = {}
    RedisHandle.data[cdump_mod.CFG_DB][cdump_mod.AUTO_TS] = {cdump_mod.CFG_INVOC_TS: invoke_ts,
                                                             cdump_mod.COOLOFF: cooloff,
                                                             cdump_mod.CFG_CORE_USAGE: core_usage,
                                                             cdump_mod.CFG_CORE_CLEANUP: core_cleanup,
                                                             cdump_mod.CFG_SINCE: since_cfg}


def set_feature_table_cfg(ts="disabled", cooloff="0", container_name="swss"):
    if cdump_mod.CFG_DB not in RedisHandle.data:
        RedisHandle.data[cdump_mod.CFG_DB] = {}
    RedisHandle.data[cdump_mod.CFG_DB][cdump_mod.FEATURE.format(container_name)] = {cdump_mod.TS: ts,
                                                                                    cdump_mod.COOLOFF: cooloff}


def populate_state_db(use_default=True, data=None):
    if use_default:
        data = {cdump_mod.TS_MAP: {"sonic_dump_random1.tar.gz": "portsyncd;1575985;portsyncd",
                                   "sonic_dump_random2.tar.gz": "syncd;1575988;syncd"},
                cdump_mod.CRITICAL_PROC: {"swss;orchagent": "123;orchagent"}}
    if cdump_mod.STATE_DB not in RedisHandle.data:
        RedisHandle.data[cdump_mod.STATE_DB] = {}
    RedisHandle.data[cdump_mod.STATE_DB][cdump_mod.TS_MAP] = {}
    RedisHandle.data[cdump_mod.STATE_DB][cdump_mod.CRITICAL_PROC] = {}
    for key in data:
        RedisHandle.data[cdump_mod.STATE_DB][key] = data[key]


class TestCoreDumpCreationEvent(unittest.TestCase):

    def setUp(self):
        cdump_mod.WAIT_BUFFER = 1
        cdump_mod.SLEEP_FOR = 0.25

    def test_invoc_ts_state_db_update(self):
        """
        Scenario: CFG_INVOC_TS is enabled. CFG_CORE_CLEANUP is disabled and no cooloff is provided
                  Check if techsupport is invoked, file is created and State DB is updated
        """
        RedisSingleton.clearState()
        set_auto_ts_cfg(auto_invoke_ts="enabled")
        set_feature_table_cfg(ts="enabled")
        populate_state_db(True)
        with Patcher() as patcher:
            def mock_cmd(cmd):
                cmd_str = " ".join(cmd)
                if "show techsupport" in cmd_str:
                    patcher.fs.create_file("/var/dump/sonic_dump_random3.tar.gz")
                else:
                    return 1, "", "Command Not Found"
                return 0, "", ""
            cdump_mod.subprocess_exec = mock_cmd
            patcher.fs.create_file("/var/dump/sonic_dump_random1.tar.gz")
            patcher.fs.create_file("/var/dump/sonic_dump_random2.tar.gz")
            patcher.fs.create_file("/var/core/orchagent.12345.123.core.gz")
            cls = cdump_mod.CriticalProcCoreDumpHandle("orchagent.12345.123.core.gz")
            cls.handle_core_dump_creation_event()
            cdump_mod.handle_coredump_cleanup("orchagent.12345.123.core.gz")
            assert "sonic_dump_random1.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random2.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random3.tar.gz" in os.listdir(cdump_mod.TS_DIR)
        assert "sonic_dump_random1.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "sonic_dump_random2.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "sonic_dump_random3.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "orchagent" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]["sonic_dump_random3.tar.gz"]

    def test_global_cooloff(self):
        """
        Scenario: CFG_INVOC_TS is enabled. CFG_CORE_CLEANUP is enabled
                  Global cooloff is not passed yet.  Check if techsupport isn't invoked.
        """
        RedisSingleton.clearState()
        set_auto_ts_cfg(auto_invoke_ts="enabled", cooloff="1")
        set_feature_table_cfg(ts="enabled")
        populate_state_db(True)
        with Patcher() as patcher:
            def mock_cmd(cmd):
                cmd_str = " ".join(cmd)
                if "show techsupport" in cmd_str:
                    patcher.fs.create_file("/var/dump/sonic_dump_random3.tar.gz")
                else:
                    return 1, "", "Command Not Found"
                return 0, "", ""
            cdump_mod.subprocess_exec = mock_cmd
            patcher.fs.create_file("/var/dump/sonic_dump_random1.tar.gz")
            patcher.fs.create_file("/var/dump/sonic_dump_random2.tar.gz")
            patcher.fs.create_file("/var/core/orchagent.12345.123.core.gz")
            cls = cdump_mod.CriticalProcCoreDumpHandle("orchagent.12345.123.core.gz")
            cls.handle_core_dump_creation_event()
            cdump_mod.handle_coredump_cleanup("orchagent.12345.123.core.gz")
            assert "sonic_dump_random1.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random2.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random3.tar.gz" not in os.listdir(cdump_mod.TS_DIR)
        assert "sonic_dump_random1.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "sonic_dump_random2.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "sonic_dump_random3.tar.gz" not in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]

    def test_per_proc_cooloff(self):
        """
        Scenario: CFG_INVOC_TS is enabled. CFG_CORE_CLEANUP is disabled. Global Cooloff is passed
                  But Per Proc cooloff is not passed yet. Check if techsupport isn't invoked
        """
        RedisSingleton.clearState()
        set_auto_ts_cfg(state="enabled", cooloff="0.25")
        set_feature_table_cfg(ts="enabled", cooloff="10")
        populate_state_db(True)
        with Patcher() as patcher:
            def mock_cmd(cmd):
                cmd_str = " ".join(cmd)
                if "show techsupport" in cmd_str:
                    patcher.fs.create_file("/var/dump/sonic_dump_random3.tar.gz")
                else:
                    return 1, "", "Command Not Found"
                return 0, "", ""
            cdump_mod.subprocess_exec = mock_cmd
            patcher.fs.create_file("/var/dump/sonic_dump_random1.tar.gz") 
            patcher.fs.create_file("/var/dump/sonic_dump_random2.tar.gz")
            patcher.fs.create_file("/var/core/orchagent.12345.123.core.gz")
            cls = cdump_mod.CriticalProcCoreDumpHandle("orchagent.12345.123.core.gz")
            time.sleep(0.25)  # wait for global cooloff to pass
            cls.handle_core_dump_creation_event()
            assert "sonic_dump_random1.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random2.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random3.tar.gz" not in os.listdir(cdump_mod.TS_DIR)
        assert "sonic_dump_random1.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "sonic_dump_random2.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "sonic_dump_random3.tar.gz" not in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]

    def test_invoc_ts_after_cooloff(self):
        """
        Scenario: CFG_INVOC_TS is enabled. CFG_CORE_CLEANUP is disabled.
                  All the cooloff's are passed. Check if techsupport is invoked
        """
        RedisSingleton.clearState()
        set_auto_ts_cfg(auto_invoke_ts="enabled", cooloff="0.1")
        set_feature_table_cfg(ts="enabled", cooloff="0.25")
        populate_state_db(True)
        with Patcher() as patcher:
            def mock_cmd(cmd):
                cmd_str = " ".join(cmd)
                if "show techsupport" in cmd_str:
                    patcher.fs.create_file("/var/dump/sonic_dump_random3.tar.gz")
                else:
                    return 1, "", "Command Not Found"
                return 0, "", ""
            cdump_mod.subprocess_exec = mock_cmd
            patcher.fs.create_file("/var/dump/sonic_dump_random1.tar.gz")
            patcher.fs.create_file("/var/dump/sonic_dump_random2.tar.gz")
            patcher.fs.create_file("/var/core/orchagent.12345.123.core.gz")
            cls = cdump_mod.CriticalProcCoreDumpHandle("orchagent.12345.123.core.gz")
            time.sleep(0.25)  # wait for all the cooloff's to pass
            cls.handle_core_dump_creation_event()
            assert "sonic_dump_random1.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random2.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random3.tar.gz" in os.listdir(cdump_mod.TS_DIR)
        assert "sonic_dump_random1.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "sonic_dump_random2.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "sonic_dump_random3.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "orchagent" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]["sonic_dump_random3.tar.gz"]

    def test_core_dump_with_no_exit_event(self):
        """
        Scenario: CFG_INVOC_TS is enabled. CFG_CORE_CLEANUP is disabled.
                  Core Dump is found but no relevant exit_event entry is found in STATE_DB.
        """
        RedisSingleton.clearState()
        set_auto_ts_cfg(auto_invoke_ts="enabled")
        set_feature_table_cfg(ts="enabled")
        populate_state_db(False, {})
        with Patcher() as patcher:
            def mock_cmd(cmd):
                cmd_str = " ".join(cmd)
                if "show techsupport" in cmd_str:
                    patcher.fs.create_file("/var/dump/sonic_dump_random3.tar.gz")
                else:
                    return 1, "", "Command Not Found"
                return 0, "", ""
            cdump_mod.subprocess_exec = mock_cmd
            patcher.fs.create_file("/var/dump/sonic_dump_random1.tar.gz")
            patcher.fs.create_file("/var/core/snmpd.12345.123.core.gz")
            cls = cdump_mod.CriticalProcCoreDumpHandle("snmpd.12345.123.core.gz")
            cls.handle_core_dump_creation_event()
            assert "sonic_dump_random3.tar.gz" not in os.listdir(cdump_mod.TS_DIR)
        assert "sonic_dump_random3.tar.gz" not in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]

    def test_core_dump_with_exit_event_unknown_cmd(self):
        """
        Scenario: CFG_INVOC_TS is enabled. CFG_CORE_CLEANUP is disabled.
                  Core Dump is found but the comm in exit_event entry is <unknown>
        """
        RedisSingleton.clearState()
        set_auto_ts_cfg(auto_invoke_ts="enabled")
        set_feature_table_cfg(ts="enabled", container_name="snmp")
        populate_state_db(False, {cdump_mod.CRITICAL_PROC: {"snmp;snmp-subagent": "123;<unknown>"}})
        with Patcher() as patcher:
            def mock_cmd(cmd):
                cmd_str = " ".join(cmd)
                if "show techsupport" in cmd_str:
                    patcher.fs.create_file("/var/dump/sonic_dump_random3.tar.gz")
                else:
                    return 1, "", "Command Not Found"
                return 0, "", ""
            cdump_mod.subprocess_exec = mock_cmd
            patcher.fs.create_file("/var/dump/sonic_dump_random1.tar.gz")
            patcher.fs.create_file("/var/core/python3.12345.123.core.gz")
            cls = cdump_mod.CriticalProcCoreDumpHandle("python3.12345.123.core.gz")
            cls.handle_core_dump_creation_event()
            assert "sonic_dump_random3.tar.gz" in os.listdir(cdump_mod.TS_DIR)
        assert "snmp-subagent" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]["sonic_dump_random3.tar.gz"]

    def test_feature_table_not_set(self):
        """
        Scenario: CFG_INVOC_TS is enabled. CFG_CORE_CLEANUP is disabled.
                  The auto-techsupport in Feature table is not enabled for the core-dump generated
                  Check if techsupport is not invoked
        """
        RedisSingleton.clearState()
        set_auto_ts_cfg(auto_invoke_ts="enabled")
        set_feature_table_cfg(ts="disabled", container_name="snmp")
        populate_state_db(False, {"snmp:snmp-subagent": "123;python3"})
        with Patcher() as patcher:
            def mock_cmd(cmd):
                cmd_str = " ".join(cmd)
                if "show techsupport" in cmd_str:
                    patcher.fs.create_file("/var/dump/sonic_dump_random3.tar.gz")
                else:
                    return 1, "", "Command Not Found"
                return 0, "", ""
            cdump_mod.subprocess_exec = mock_cmd
            patcher.fs.create_file("/var/dump/sonic_dump_random1.tar.gz")
            patcher.fs.create_file("/var/core/python3.12345.123.core.gz")
            cls = cdump_mod.CriticalProcCoreDumpHandle("python3.12345.123.core.gz")
            cls.handle_core_dump_creation_event()
            cdump_mod.handle_coredump_cleanup("python3.12345.123.core.gz")
            assert "sonic_dump_random3.tar.gz" not in os.listdir(cdump_mod.TS_DIR)

    def test_since_argument(self):
        """
        Scenario: CFG_INVOC_TS is enabled. CFG_CORE_CLEANUP is disabled.
                  Check if techsupport is invoked and since argument in properly applied
        """
        RedisSingleton.clearState()
        set_auto_ts_cfg(auto_invoke_ts="enabled", cooloff="0.1", since="4 days ago")
        set_feature_table_cfg(ts="enabled", cooloff="0.2")
        populate_state_db(True)
        with Patcher() as patcher:
            def mock_cmd(cmd):
                cmd_str = " ".join(cmd)
                if "show techsupport --since '4 days ago'" in cmd_str:
                    patcher.fs.create_file("/var/dump/sonic_dump_random3.tar.gz")
                    return 0, "", ""
                elif "date --date='4 days ago'" in cmd_str:
                    return 0, "", ""
                else:
                    return 1, "", "Invalid Command"
            cdump_mod.subprocess_exec = mock_cmd
            patcher.fs.create_file("/var/dump/sonic_dump_random1.tar.gz") 
            patcher.fs.create_file("/var/dump/sonic_dump_random2.tar.gz")
            patcher.fs.create_file("/var/core/orchagent.12345.123.core.gz")
            cls = cdump_mod.CriticalProcCoreDumpHandle("orchagent.12345.123.core.gz")
            time.sleep(0.2)  # wait for cooloff to pass
            cls.handle_core_dump_creation_event()
            cdump_mod.handle_coredump_cleanup("orchagent.12345.123.core.gz")
            assert "sonic_dump_random1.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random2.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random3.tar.gz" in os.listdir(cdump_mod.TS_DIR)
        assert "sonic_dump_random1.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "sonic_dump_random2.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "sonic_dump_random3.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "orchagent" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]["sonic_dump_random3.tar.gz"]

    def test_invalid_since_argument(self):
        """
        Scenario: CFG_INVOC_TS is enabled. CFG_CORE_CLEANUP is disabled.
                  Check if techsupport is invoked and an invalid since argument in identified
        """
        RedisSingleton.clearState()
        set_auto_ts_cfg(auto_invoke_ts="enabled", cooloff="0.1", since="whatever")
        set_feature_table_cfg(ts="enabled", cooloff="0.2")
        populate_state_db(True)
        with Patcher() as patcher:
            def mock_cmd(cmd):
                cmd_str = " ".join(cmd)
                if "show techsupport --since '2 days ago'" in cmd_str:
                    patcher.fs.create_file("/var/dump/sonic_dump_random3.tar.gz")
                    return 0, "", ""
                elif "date --date='whatever'" in cmd_str:
                    return 1, "", "Invalid Date Format"
                else:
                    return 1, "", ""
            cdump_mod.subprocess_exec = mock_cmd
            patcher.fs.create_file("/var/dump/sonic_dump_random1.tar.gz")
            patcher.fs.create_file("/var/dump/sonic_dump_random2.tar.gz")
            patcher.fs.create_file("/var/core/orchagent.12345.123.core.gz")
            cls = cdump_mod.CriticalProcCoreDumpHandle("orchagent.12345.123.core.gz")
            time.sleep(0.2)  # wait for cooloff to pass
            cls.handle_core_dump_creation_event()
            cdump_mod.handle_coredump_cleanup("orchagent.12345.123.core.gz")
            assert "sonic_dump_random1.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random2.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random3.tar.gz" in os.listdir(cdump_mod.TS_DIR)
        assert "sonic_dump_random1.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "sonic_dump_random2.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "sonic_dump_random3.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "orchagent" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]["sonic_dump_random3.tar.gz"]

    def test_core_dump_cleanup(self):
        """
        Scenario: CFG_CORE_CLEANUP is enabled. core-dump limit is crossed
                  Verify Whether is cleanup is performed
        """
        RedisSingleton.clearState()
        set_auto_ts_cfg(coredump_cleanup="enabled", core_usage="6.0")
        with Patcher() as patcher:
            patcher.fs.set_disk_usage(1000, path="/var/core/")
            patcher.fs.create_file("/var/core/orchagent.12345.123.core.gz", st_size=25)
            patcher.fs.create_file("/var/core/lldpmgrd.12345.22.core.gz", st_size=25)
            patcher.fs.create_file("/var/core/python3.12345.21.core.gz", st_size=25)
            cdump_mod.handle_coredump_cleanup("python3.12345.21.core.gz")
            current_fs = os.listdir(cdump_mod.CORE_DUMP_DIR)
            assert len(current_fs) == 2
            assert "orchagent.12345.123.core.gz" not in current_fs
            assert "lldpmgrd.12345.22.core.gz" in current_fs
            assert "python3.12345.21.core.gz" in current_fs

    def test_core_usage_limit_not_crossed(self):
        """
        Scenario: CFG_CORE_CLEANUP is enabled. core-dump limit is crossed
                  Verify Whether is cleanup is performed
        """
        RedisSingleton.clearState()
        set_auto_ts_cfg(coredump_cleanup="enabled", core_usage="5.0")
        with Patcher() as patcher:
            def mock_cmd(cmd):
                cmd_str = " ".join(cmd)
                if "show techsupport" in cmd_str:
                    patcher.fs.create_file("/var/dump/sonic_dump_random3.tar.gz")
                return 0, "", ""
            patcher.fs.set_disk_usage(2000, path="/var/core/")
            patcher.fs.create_file("/var/core/orchagent.12345.123.core.gz", st_size=25)
            patcher.fs.create_file("/var/core/lldpmgrd.12345.22.core.gz", st_size=25)
            patcher.fs.create_file("/var/core/python3.12345.21.core.gz", st_size=25)
            cdump_mod.handle_coredump_cleanup("python3.12345.21.core.gz")
            current_fs = os.listdir(cdump_mod.CORE_DUMP_DIR)
            assert len(current_fs) == 3
            assert "orchagent.12345.123.core.gz" in current_fs
            assert "lldpmgrd.12345.22.core.gz" in current_fs
            assert "python3.12345.21.core.gz" in current_fs
