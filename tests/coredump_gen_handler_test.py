import os
import time
import sys
import pyfakefs
import unittest
from pyfakefs.fake_filesystem_unittest import Patcher
from swsscommon import swsscommon
from utilities_common.general import load_module_from_source
from utilities_common.db import Db
from .mock_tables import dbconnector

sys.path.append("scripts")
import coredump_gen_handler as cdump_mod


def set_auto_ts_cfg(redis_mock, auto_invoke_ts="disabled",
                    core_cleanup="disabled",
                    rate_limit_interval="0",
                    max_core_size="0",
                    since_cfg="None"):
    redis_mock.set(cdump_mod.CFG_DB, cdump_mod.AUTO_TS, cdump_mod.CFG_INVOC_TS, auto_invoke_ts)
    redis_mock.set(cdump_mod.CFG_DB, cdump_mod.AUTO_TS, cdump_mod.COOLOFF, rate_limit_interval)
    redis_mock.set(cdump_mod.CFG_DB, cdump_mod.AUTO_TS, cdump_mod.CFG_CORE_USAGE, max_core_size)
    redis_mock.set(cdump_mod.CFG_DB, cdump_mod.AUTO_TS, cdump_mod.CFG_CORE_CLEANUP, core_cleanup)
    redis_mock.set(cdump_mod.CFG_DB, cdump_mod.AUTO_TS, cdump_mod.CFG_SINCE, since_cfg)


def set_feature_table_cfg(redis_mock, ts="disabled", rate_limit_interval="0", container_name="swss"):
    redis_mock.set(cdump_mod.CFG_DB, cdump_mod.FEATURE.format(container_name), cdump_mod.TS, ts)
    redis_mock.set(cdump_mod.CFG_DB, cdump_mod.AUTO_TS_RATE_INTV, container_name, rate_limit_interval)


def populate_state_db(redis_mock,
                      ts_map={"sonic_dump_random1.tar.gz": "orchagent;1575985;orchagent",
                              "sonic_dump_random2.tar.gz": "syncd;1575988;syncd"},
                      crit_proc={"swss;orchagent": "123;orchagent"}):
    for field, value in ts_map.items():
        redis_mock.set(cdump_mod.STATE_DB, cdump_mod.TS_MAP, field, value)
    for field, value in crit_proc.items():
        redis_mock.set(cdump_mod.STATE_DB, cdump_mod.CRITICAL_PROC, field, value)


class TestCoreDumpCreationEvent(unittest.TestCase):

    def setUp(self):
        cdump_mod.WAIT_BUFFER = 1
        cdump_mod.SLEEP_FOR = 0.25

    def test_invoc_ts_state_db_update(self):
        """
        Scenario: CFG_INVOC_TS is enabled. CFG_CORE_CLEANUP is disabled and no rate_limit_interval is provided
                  Check if techsupport is invoked, file is created and State DB is updated
        """
        db_wrap = Db()
        redis_mock = db_wrap.db
        set_auto_ts_cfg(redis_mock, auto_invoke_ts="enabled")
        set_feature_table_cfg(redis_mock, ts="enabled")
        populate_state_db(redis_mock)
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
            cls = cdump_mod.CriticalProcCoreDumpHandle("orchagent.12345.123.core.gz", redis_mock)
            cls.handle_core_dump_creation_event()
            cdump_mod.handle_coredump_cleanup("orchagent.12345.123.core.gz", redis_mock)
            assert "sonic_dump_random1.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random2.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random3.tar.gz" in os.listdir(cdump_mod.TS_DIR)
        final_state = redis_mock.get_all(cdump_mod.STATE_DB, cdump_mod.TS_MAP)
        assert "sonic_dump_random1.tar.gz" in final_state
        assert "sonic_dump_random2.tar.gz" in final_state
        assert "sonic_dump_random3.tar.gz" in final_state
        assert "orchagent" in final_state["sonic_dump_random3.tar.gz"]

    def test_global_rate_limit_interval(self):
        """
        Scenario: CFG_INVOC_TS is enabled. CFG_CORE_CLEANUP is enabled
                  Global rate_limit_interval is not passed yet.  Check if techsupport isn't invoked.
        """
        db_wrap = Db()
        redis_mock = db_wrap.db
        set_auto_ts_cfg(redis_mock, auto_invoke_ts="enabled", rate_limit_interval="1")
        set_feature_table_cfg(redis_mock, ts="enabled")
        populate_state_db(redis_mock)
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
            cls = cdump_mod.CriticalProcCoreDumpHandle("orchagent.12345.123.core.gz", redis_mock)
            cls.handle_core_dump_creation_event()
            cdump_mod.handle_coredump_cleanup("orchagent.12345.123.core.gz", redis_mock)
            assert "sonic_dump_random1.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random2.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random3.tar.gz" not in os.listdir(cdump_mod.TS_DIR)
        final_state = redis_mock.get_all(cdump_mod.STATE_DB, cdump_mod.TS_MAP)
        assert "sonic_dump_random1.tar.gz" in final_state
        assert "sonic_dump_random2.tar.gz" in final_state
        assert "sonic_dump_random3.tar.gz" not in final_state

    def test_per_proc_rate_limit_interval(self):
        """
        Scenario: CFG_INVOC_TS is enabled. CFG_CORE_CLEANUP is disabled. Global Cooloff is passed
                  But Per Proc rate_limit_interval is not passed yet. Check if techsupport isn't invoked
        """
        db_wrap = Db()
        redis_mock = db_wrap.db
        set_auto_ts_cfg(redis_mock, auto_invoke_ts="enabled", rate_limit_interval="0.25")
        set_feature_table_cfg(redis_mock, ts="enabled", rate_limit_interval="10")
        populate_state_db(redis_mock, ts_map={"sonic_dump_random1.tar.gz":
                                              "orchagent;{};orchagent".format(int(time.time()))})
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
            patcher.fs.create_file("/var/core/orchagent.12345.123.core.gz")
            cls = cdump_mod.CriticalProcCoreDumpHandle("orchagent.12345.123.core.gz", redis_mock)
            time.sleep(0.25)  # wait for global rate_limit_interval to pass
            cls.handle_core_dump_creation_event()
            assert "sonic_dump_random1.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random3.tar.gz" not in os.listdir(cdump_mod.TS_DIR)
        final_state = redis_mock.get_all(cdump_mod.STATE_DB, cdump_mod.TS_MAP)
        assert "sonic_dump_random1.tar.gz" in final_state
        assert "sonic_dump_random3.tar.gz" not in final_state

    def test_invoc_ts_after_rate_limit_interval(self):
        """
        Scenario: CFG_INVOC_TS is enabled. CFG_CORE_CLEANUP is disabled.
                  All the rate_limit_interval's are passed. Check if techsupport is invoked
        """
        db_wrap = Db()
        redis_mock = db_wrap.db
        set_auto_ts_cfg(redis_mock, auto_invoke_ts="enabled", rate_limit_interval="0.1")
        set_feature_table_cfg(redis_mock, ts="enabled", rate_limit_interval="0.25")
        populate_state_db(redis_mock, ts_map={"sonic_dump_random1.tar.gz":
                                              "orchagent;{};orchagent".format(int(time.time()))})
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
            cls = cdump_mod.CriticalProcCoreDumpHandle("orchagent.12345.123.core.gz", redis_mock)
            time.sleep(0.25)  # wait for all the rate_limit_interval's to pass
            cls.handle_core_dump_creation_event()
            assert "sonic_dump_random1.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random3.tar.gz" in os.listdir(cdump_mod.TS_DIR)
        final_state = redis_mock.get_all(cdump_mod.STATE_DB, cdump_mod.TS_MAP)
        assert "sonic_dump_random1.tar.gz" in final_state
        assert "sonic_dump_random3.tar.gz" in final_state
        assert "orchagent" in final_state["sonic_dump_random3.tar.gz"]

    def test_core_dump_with_no_exit_event(self):
        """
        Scenario: CFG_INVOC_TS is enabled. CFG_CORE_CLEANUP is disabled.
                  Core Dump is found but no relevant exit_event entry is found in STATE_DB.
        """
        db_wrap = Db()
        redis_mock = db_wrap.db
        set_auto_ts_cfg(redis_mock, auto_invoke_ts="enabled")
        set_feature_table_cfg(redis_mock, ts="enabled", container_name="snmp")
        populate_state_db(redis_mock, {}, {})
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
            cls = cdump_mod.CriticalProcCoreDumpHandle("snmpd.12345.123.core.gz", redis_mock)
            cls.handle_core_dump_creation_event()
            assert "sonic_dump_random3.tar.gz" not in os.listdir(cdump_mod.TS_DIR)
        final_state = redis_mock.get_all(cdump_mod.STATE_DB, cdump_mod.TS_MAP)
        assert not final_state

    def test_core_dump_with_exit_event_unknown_cmd(self):
        """
        Scenario: CFG_INVOC_TS is enabled. CFG_CORE_CLEANUP is disabled.
                  Core Dump is found but the comm in exit_event entry is <unknown>
        """
        db_wrap = Db()
        redis_mock = db_wrap.db
        set_auto_ts_cfg(redis_mock, auto_invoke_ts="enabled")
        set_feature_table_cfg(redis_mock, ts="enabled", container_name="snmp")
        populate_state_db(redis_mock, {}, {"snmp;snmp-subagent": "123;<unknown>"})
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
            cls = cdump_mod.CriticalProcCoreDumpHandle("python3.12345.123.core.gz", redis_mock)
            cls.handle_core_dump_creation_event()
            assert "sonic_dump_random3.tar.gz" in os.listdir(cdump_mod.TS_DIR)
        final_state = redis_mock.get_all(cdump_mod.STATE_DB, cdump_mod.TS_MAP)
        assert "snmp-subagent" in final_state["sonic_dump_random3.tar.gz"]

    def test_feature_table_not_set(self):
        """
        Scenario: CFG_INVOC_TS is enabled. CFG_CORE_CLEANUP is disabled.
                  The auto-techsupport in Feature table is not enabled for the core-dump generated
                  Check if techsupport is not invoked
        """
        db_wrap = Db()
        redis_mock = db_wrap.db
        set_auto_ts_cfg(redis_mock, auto_invoke_ts="enabled")
        set_feature_table_cfg(redis_mock, ts="disabled", container_name="snmp")
        populate_state_db(redis_mock, {}, {"snmp:snmp-subagent": "123;python3"})
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
            cls = cdump_mod.CriticalProcCoreDumpHandle("python3.12345.123.core.gz", redis_mock)
            cls.handle_core_dump_creation_event()
            cdump_mod.handle_coredump_cleanup("python3.12345.123.core.gz", redis_mock)
            assert "sonic_dump_random3.tar.gz" not in os.listdir(cdump_mod.TS_DIR)

    def test_since_argument(self):
        """
        Scenario: CFG_INVOC_TS is enabled. CFG_CORE_CLEANUP is disabled.
                  Check if techsupport is invoked and since argument in properly applied
        """
        db_wrap = Db()
        redis_mock = db_wrap.db
        set_auto_ts_cfg(redis_mock, auto_invoke_ts="enabled", since_cfg="4 days ago")
        set_feature_table_cfg(redis_mock, ts="enabled")
        populate_state_db(redis_mock)
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
            cls = cdump_mod.CriticalProcCoreDumpHandle("orchagent.12345.123.core.gz", redis_mock)
            cls.handle_core_dump_creation_event()
            cdump_mod.handle_coredump_cleanup("orchagent.12345.123.core.gz", redis_mock)
            assert "sonic_dump_random1.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random2.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random3.tar.gz" in os.listdir(cdump_mod.TS_DIR)
        final_state = redis_mock.get_all(cdump_mod.STATE_DB, cdump_mod.TS_MAP)
        assert "sonic_dump_random1.tar.gz" in final_state
        assert "sonic_dump_random2.tar.gz" in final_state
        assert "sonic_dump_random3.tar.gz" in final_state
        assert "orchagent" in final_state["sonic_dump_random3.tar.gz"]

    def test_invalid_since_argument(self):
        """
        Scenario: CFG_INVOC_TS is enabled. CFG_CORE_CLEANUP is disabled.
                  Check if techsupport is invoked and an invalid since argument in identified
        """
        db_wrap = Db()
        redis_mock = db_wrap.db
        set_auto_ts_cfg(redis_mock, auto_invoke_ts="enabled", since_cfg="whatever")
        set_feature_table_cfg(redis_mock, ts="enabled")
        populate_state_db(redis_mock)
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
            cls = cdump_mod.CriticalProcCoreDumpHandle("orchagent.12345.123.core.gz", redis_mock)
            cls.handle_core_dump_creation_event()
            cdump_mod.handle_coredump_cleanup("orchagent.12345.123.core.gz", redis_mock)
            assert "sonic_dump_random1.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random2.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random3.tar.gz" in os.listdir(cdump_mod.TS_DIR)
        final_state = redis_mock.get_all(cdump_mod.STATE_DB, cdump_mod.TS_MAP)
        assert "sonic_dump_random1.tar.gz" in final_state
        assert "sonic_dump_random2.tar.gz" in final_state
        assert "sonic_dump_random3.tar.gz" in final_state
        assert "orchagent" in final_state["sonic_dump_random3.tar.gz"]

    def test_core_dump_cleanup(self):
        """
        Scenario: CFG_CORE_CLEANUP is enabled. core-dump limit is crossed
                  Verify Whether is cleanup is performed
        """
        db_wrap = Db()
        redis_mock = db_wrap.db
        set_auto_ts_cfg(redis_mock, core_cleanup="enabled", max_core_size="6.0")
        with Patcher() as patcher:
            patcher.fs.set_disk_usage(1000, path="/var/core/")
            patcher.fs.create_file("/var/core/orchagent.12345.123.core.gz", st_size=25)
            patcher.fs.create_file("/var/core/lldpmgrd.12345.22.core.gz", st_size=25)
            patcher.fs.create_file("/var/core/python3.12345.21.core.gz", st_size=25)
            cdump_mod.handle_coredump_cleanup("python3.12345.21.core.gz", redis_mock)
            current_fs = os.listdir(cdump_mod.CORE_DUMP_DIR)
            assert len(current_fs) == 2
            assert "orchagent.12345.123.core.gz" not in current_fs
            assert "lldpmgrd.12345.22.core.gz" in current_fs
            assert "python3.12345.21.core.gz" in current_fs

    def test_max_core_size_limit_not_crossed(self):
        """
        Scenario: CFG_CORE_CLEANUP is enabled. core-dump limit is crossed
                  Verify Whether is cleanup is performed
        """
        db_wrap = Db()
        redis_mock = db_wrap.db
        set_auto_ts_cfg(redis_mock, core_cleanup="enabled", max_core_size="5.0")
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
            cdump_mod.handle_coredump_cleanup("python3.12345.21.core.gz", redis_mock)
            current_fs = os.listdir(cdump_mod.CORE_DUMP_DIR)
            assert len(current_fs) == 3
            assert "orchagent.12345.123.core.gz" in current_fs
            assert "lldpmgrd.12345.22.core.gz" in current_fs
            assert "python3.12345.21.core.gz" in current_fs
