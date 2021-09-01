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


def set_auto_ts_cfg(redis_mock, state="disabled",
                    rate_limit_interval="0",
                    max_core_size="0.0",
                    since_cfg="None"):
    redis_mock.set(cdump_mod.CFG_DB, cdump_mod.AUTO_TS, cdump_mod.CFG_STATE, state)
    redis_mock.set(cdump_mod.CFG_DB, cdump_mod.AUTO_TS, cdump_mod.COOLOFF, rate_limit_interval)
    redis_mock.set(cdump_mod.CFG_DB, cdump_mod.AUTO_TS, cdump_mod.CFG_CORE_USAGE, max_core_size)
    redis_mock.set(cdump_mod.CFG_DB, cdump_mod.AUTO_TS, cdump_mod.CFG_SINCE, since_cfg)


def set_feature_table_cfg(redis_mock, ts="disabled", rate_limit_interval="0", container_name="swss"):
    redis_mock.set(cdump_mod.CFG_DB, cdump_mod.FEATURE.format(container_name), cdump_mod.TS, ts)
    redis_mock.set(cdump_mod.CFG_DB, cdump_mod.AUTO_TS_RATE_INTV, container_name, rate_limit_interval)


def set_auto_ts_dump_info(redis_mock, ts_dump, core_dump, timestamp, crit_proc):
    key = cdump_mod.TS_MAP + "|" + ts_dump
    redis_mock.set(cdump_mod.STATE_DB, key, cdump_mod.CORE_DUMP, core_dump)
    redis_mock.set(cdump_mod.STATE_DB, key, cdump_mod.TIMESTAMP, timestamp)
    redis_mock.set(cdump_mod.STATE_DB, key, cdump_mod.CRIT_PROC, crit_proc)


def populate_state_db(redis_mock,
                      ts_map={"sonic_dump_random1": "orchagent;1575985;orchagent",
                              "sonic_dump_random2": "syncd;1575988;syncd"},
                      crit_proc_mp={"swss;orchagent": "123;orchagent"}):
    for dump, value in ts_map.items():
        core_dump, timestamp, crit_proc = value.split(";")
        set_auto_ts_dump_info(redis_mock, dump, core_dump, timestamp, crit_proc)
    for field, value in crit_proc_mp.items():
        redis_mock.set(cdump_mod.STATE_DB, cdump_mod.CRITICAL_PROC, field, value)
    print(redis_mock.keys(cdump_mod.STATE_DB, cdump_mod.TS_MAP+"*"))


def verify_post_exec_state(redis_mock, cdump_expect=[], cdumps_not_expect=[], crit_proc_mp={}):
    final_state = redis_mock.keys(cdump_mod.STATE_DB, cdump_mod.TS_MAP+"*")
    for dump in cdump_expect:
        assert cdump_mod.TS_MAP+"|"+dump in final_state
    for dump in cdumps_not_expect:
        assert cdump_mod.TS_MAP+"|"+dump not in final_state
    for dump, crit_proc in crit_proc_mp.items():
        key = cdump_mod.TS_MAP+"|"+dump
        assert crit_proc in redis_mock.get(cdump_mod.STATE_DB, key, cdump_mod.CRIT_PROC)


class TestCoreDumpCreationEvent(unittest.TestCase):

    def setUp(self):
        cdump_mod.TIME_BUF = 1
        cdump_mod.WAIT_BUFFER = 1
        cdump_mod.INIT_SLEEP = 0.25
        cdump_mod.EXP_FACTOR = 1

    def test_invoc_ts_state_db_update(self):
        """
        Scenario: CFG_STATE is enabled. CFG_CORE_CLEANUP is disabled and no rate_limit_interval is provided
                  Check if techsupport is invoked, file is created and State DB is updated
        """
        db_wrap = Db()
        redis_mock = db_wrap.db
        set_auto_ts_cfg(redis_mock, state="enabled")
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
        cdump_expect = ["sonic_dump_random1", "sonic_dump_random2", "sonic_dump_random3"]
        verify_post_exec_state(redis_mock, cdump_expect)


    def test_global_rate_limit_interval(self):
        """
        Scenario: CFG_STATE is enabled.
                  Global rate_limit_interval is not passed yet.  Check if techsupport isn't invoked.
        """
        db_wrap = Db()
        redis_mock = db_wrap.db
        set_auto_ts_cfg(redis_mock, state="enabled", rate_limit_interval="1")
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
        cdump_expect = ["sonic_dump_random1", "sonic_dump_random2"]
        cdump_not_expect = ["sonic_dump_random3"]
        verify_post_exec_state(redis_mock, cdump_expect, cdump_not_expect)

    def test_per_proc_rate_limit_interval(self):
        """
        Scenario: CFG_STATE is enabled. Global rate_limit_interval is passed
                  But Per Proc rate_limit_interval is not passed yet. Check if techsupport isn't invoked
        """
        db_wrap = Db()
        redis_mock = db_wrap.db
        set_auto_ts_cfg(redis_mock, state="enabled", rate_limit_interval="0.25")
        set_feature_table_cfg(redis_mock, ts="enabled", rate_limit_interval="10")
        populate_state_db(redis_mock, ts_map={"sonic_dump_random1":
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
        verify_post_exec_state(redis_mock, ["sonic_dump_random1"], ["sonic_dump_random3"])

    def test_invoc_ts_after_rate_limit_interval(self):
        """
        Scenario: CFG_STATE is enabled.
                  All the rate_limit_interval's are passed. Check if techsupport is invoked
        """
        db_wrap = Db()
        redis_mock = db_wrap.db
        set_auto_ts_cfg(redis_mock, state="enabled", rate_limit_interval="0.1")
        set_feature_table_cfg(redis_mock, ts="enabled", rate_limit_interval="0.25")
        populate_state_db(redis_mock, ts_map={"sonic_dump_random1":
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
        crit_proc_mp = {"sonic_dump_random3": "orchagent"}
        verify_post_exec_state(redis_mock, ["sonic_dump_random1", "sonic_dump_random3"], [], crit_proc_mp)

    def test_core_dump_with_no_exit_event(self):
        """
        Scenario: CFG_STATE is enabled.
                  Core Dump is found but no relevant exit_event entry is found in STATE_DB.
        """
        db_wrap = Db()
        redis_mock = db_wrap.db
        set_auto_ts_cfg(redis_mock, state="enabled")
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
        final_state = redis_mock.keys(cdump_mod.STATE_DB, cdump_mod.TS_MAP+"*")
        assert not final_state

    def test_core_dump_with_exit_event_unknown_cmd(self):
        """
        Scenario: CFG_STATE is enabled.
                  Core Dump is found but the comm in exit_event entry is <unknown>
        """
        db_wrap = Db()
        redis_mock = db_wrap.db
        set_auto_ts_cfg(redis_mock, state="enabled")
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
        crit_proc_mp = {"sonic_dump_random3": "snmp-subagent"}
        verify_post_exec_state(redis_mock, [], [], crit_proc_mp)


    def test_feature_table_not_set(self):
        """
        Scenario: CFG_STATE is enabled. 
                  The auto-techsupport in Feature table is not enabled for the core-dump generated
                  Check if techsupport is not invoked
        """
        db_wrap = Db()
        redis_mock = db_wrap.db
        set_auto_ts_cfg(redis_mock, state="enabled")
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
        Scenario: CFG_STATE is enabled.
                  Check if techsupport is invoked and since argument in properly applied
        """
        db_wrap = Db()
        redis_mock = db_wrap.db
        set_auto_ts_cfg(redis_mock, state="enabled", since_cfg="4 days ago")
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
        expect = ["sonic_dump_random1", "sonic_dump_random2", "sonic_dump_random3"]
        crit_proc_mp = {"sonic_dump_random3": "orchagent"}
        verify_post_exec_state(redis_mock, expect, [], crit_proc_mp)


    def test_invalid_since_argument(self):
        """
        Scenario: CFG_STATE is enabled.
                  Check if techsupport is invoked and an invalid since argument in identified
        """
        db_wrap = Db()
        redis_mock = db_wrap.db
        set_auto_ts_cfg(redis_mock, state="enabled", since_cfg="whatever")
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
        expect = ["sonic_dump_random1", "sonic_dump_random2", "sonic_dump_random3"]
        crit_proc_mp = {"sonic_dump_random3": "orchagent"}
        verify_post_exec_state(redis_mock, expect, [], crit_proc_mp)

    def test_core_dump_cleanup(self):
        """
        Scenario: CFG_STATE is enabled. core-dump limit is crossed
                  Verify Whether is cleanup is performed
        """
        db_wrap = Db()
        redis_mock = db_wrap.db
        set_auto_ts_cfg(redis_mock, state="enabled", max_core_size="6.0")
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
        Scenario: CFG_STATE is enabled. core-dump limit is crossed
                  Verify Whether is cleanup is performed
        """
        db_wrap = Db()
        redis_mock = db_wrap.db
        set_auto_ts_cfg(redis_mock, state="enabled", max_core_size="5.0")
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
