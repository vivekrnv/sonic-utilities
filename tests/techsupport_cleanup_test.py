import os
import sys
import pyfakefs
import unittest
from pyfakefs.fake_filesystem_unittest import Patcher
from swsscommon import swsscommon
from utilities_common.general import load_module_from_source
from utilities_common.db import Db
from .mock_tables import dbconnector

sys.path.append("scripts")
import techsupport_cleanup as ts_mod


def set_auto_ts_cfg(redis_mock, ts_cleanup="disabled", max_ts="0"):
    redis_mock.set(ts_mod.CFG_DB, ts_mod.AUTO_TS, ts_mod.CFG_TS_CLEANUP, ts_cleanup)
    redis_mock.set(ts_mod.CFG_DB, ts_mod.AUTO_TS, ts_mod.CFG_MAX_TS, max_ts)


class TestTechsupportCreationEvent(unittest.TestCase):

    def test_no_cleanup_state_disabled(self):
        """
        Scenario: TS_CLEANUP is disabled.  Check no cleanup is performed,
                  even though the techsupport limit is already crossed
        """
        db_wrap = Db()
        redis_mock = db_wrap.db
        set_auto_ts_cfg(redis_mock, max_ts="5")
        with Patcher() as patcher:
            patcher.fs.set_disk_usage(1000, path="/var/dump/")
            patcher.fs.create_file("/var/dump/sonic_dump_random1.tar.gz", st_size=30)
            patcher.fs.create_file("/var/dump/sonic_dump_random2.tar.gz", st_size=30)
            patcher.fs.create_file("/var/dump/sonic_dump_random3.tar.gz", st_size=30)
            ts_mod.handle_techsupport_creation_event("/var/dump/sonic_dump_random3.tar.gz", redis_mock)
            current_fs = os.listdir(ts_mod.TS_DIR)
            print(current_fs)
            assert len(current_fs) == 3
            assert "sonic_dump_random1.tar.gz" in current_fs
            assert "sonic_dump_random2.tar.gz" in current_fs
            assert "sonic_dump_random3.tar.gz" in current_fs

    def test_no_cleanup_state_enabled(self):
        """
        Scenario: TS_CLEANUP is enabled.
                  Verify no cleanup is performed, as the techsupport limit haven't crossed yet
        """
        db_wrap = Db()
        redis_mock = db_wrap.db
        set_auto_ts_cfg(redis_mock, ts_cleanup="enabled", max_ts="10")
        with Patcher() as patcher:
            patcher.fs.set_disk_usage(1000, path="/var/dump/")
            patcher.fs.create_file("/var/dump/sonic_dump_random1.tar.gz", st_size=30)
            patcher.fs.create_file("/var/dump/sonic_dump_random2.tar.gz", st_size=30)
            patcher.fs.create_file("/var/dump/sonic_dump_random3.tar.gz", st_size=30)
            ts_mod.handle_techsupport_creation_event("/var/dump/sonic_dump_random3.tar.gz", redis_mock)
            current_fs = os.listdir(ts_mod.TS_DIR)
            print(current_fs)
            assert len(current_fs) == 3
            assert "sonic_dump_random1.tar.gz" in current_fs
            assert "sonic_dump_random2.tar.gz" in current_fs
            assert "sonic_dump_random3.tar.gz" in current_fs

    def test_dump_cleanup(self):
        """
        Scenario: TS_CLEANUP is enabled. techsupport size limit is crosed
                  Verify Whether is cleanup is performed or not
        """
        db_wrap = Db()
        redis_mock = db_wrap.db
        set_auto_ts_cfg(redis_mock, ts_cleanup="enabled", max_ts="5")
        with Patcher() as patcher:
            patcher.fs.set_disk_usage(1000, path="/var/dump/")
            patcher.fs.create_file("/var/dump/sonic_dump_random1.tar.gz", st_size=25)
            patcher.fs.create_file("/var/dump/sonic_dump_random2.tar.gz", st_size=25)
            patcher.fs.create_file("/var/dump/sonic_dump_random3.tar.gz", st_size=25)
            ts_mod.handle_techsupport_creation_event("/var/dump/sonic_dump_random3.tar.gz", redis_mock)
            current_fs = os.listdir(ts_mod.TS_DIR)
            assert len(current_fs) == 2
            assert "sonic_dump_random1.tar.gz" not in current_fs
            assert "sonic_dump_random2.tar.gz" in current_fs
            assert "sonic_dump_random3.tar.gz" in current_fs

    def test_state_db_update(self):
        """
        Scenario: TS_CLEANUP is enabled. techsupport size limit is crosed
                  Verify Whether is cleanup is performed and the state_db is updated
        """
        db_wrap = Db()
        redis_mock = db_wrap.db
        set_auto_ts_cfg(redis_mock, ts_cleanup="enabled", max_ts="5")
        redis_mock.set(ts_mod.STATE_DB, ts_mod.TS_MAP, "sonic_dump_random1.tar.gz", "orchagent;1575985;orchagent")
        redis_mock.set(ts_mod.STATE_DB, ts_mod.TS_MAP, "sonic_dump_random2.tar.gz", "syncd;1575988;syncd")
        with Patcher() as patcher:
            patcher.fs.set_disk_usage(1000, path="/var/dump/")
            patcher.fs.create_file("/var/dump/sonic_dump_random1.tar.gz", st_size=25)
            patcher.fs.create_file("/var/dump/sonic_dump_random2.tar.gz", st_size=25)
            patcher.fs.create_file("/var/dump/sonic_dump_random3.tar.gz", st_size=25)
            ts_mod.handle_techsupport_creation_event("/var/dump/sonic_dump_random3.tar.gz", redis_mock)
            current_fs = os.listdir(ts_mod.TS_DIR)
            print(current_fs)
            assert len(current_fs) == 2
            assert "sonic_dump_random1.tar.gz" not in current_fs
            assert "sonic_dump_random2.tar.gz" in current_fs
            assert "sonic_dump_random3.tar.gz" in current_fs
        final_state = redis_mock.get_all(ts_mod.STATE_DB, ts_mod.TS_MAP)
        assert "sonic_dump_random2.tar.gz" in final_state
        assert "sonic_dump_random1.tar.gz" not in final_state