import os
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
script_path = os.path.join(scripts_path, 'techsupport_cleanup')
ts_mod = load_module_from_source('techsupport_cleanup', script_path)

# Mock the SonicV2Connector
ts_mod.SonicV2Connector = MockConn

# Mock Handle to the data inside the Redis
RedisHandle = RedisSingleton.getInstance()


def set_auto_ts_cfg(**kwargs):
    ts_cleanup = kwargs[ts_mod.CFG_TS_CLEANUP] if ts_mod.CFG_TS_CLEANUP in kwargs else "disabled"
    max_ts = kwargs[ts_mod.CFG_MAX_TS] if ts_mod.CFG_MAX_TS in kwargs else "0"
    RedisHandle.data[ts_mod.CFG_DB] = {ts_mod.AUTO_TS : {ts_mod.CFG_TS_CLEANUP : ts_cleanup,
                                                         ts_mod.CFG_MAX_TS : max_ts}}


class TestTechsupportCreationEvent(unittest.TestCase):

    def test_no_cleanup_state_disabled(self):
        """
        Scenario: TS_CLEANUP is disabled.  Check no cleanup is performed,
                  even though the techsupport limit is already crossed
        """
        RedisSingleton.clearState()
        set_auto_ts_cfg(max_techsupport_size="5")
        with Patcher() as patcher:
            patcher.fs.set_disk_usage(1000, path="/var/dump/")
            patcher.fs.create_file("/var/dump/sonic_dump_random1.tar.gz", st_size=30)
            patcher.fs.create_file("/var/dump/sonic_dump_random2.tar.gz", st_size=30)
            patcher.fs.create_file("/var/dump/sonic_dump_random3.tar.gz", st_size=30)
            ts_mod.handle_techsupport_creation_event("/var/dump/sonic_dump_random3.tar.gz")
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
        RedisSingleton.clearState()
        set_auto_ts_cfg(techsupport_cleanup="enabled", max_techsupport_size="10")
        with Patcher() as patcher:
            patcher.fs.set_disk_usage(1000, path="/var/dump/")
            patcher.fs.create_file("/var/dump/sonic_dump_random1.tar.gz", st_size=30)
            patcher.fs.create_file("/var/dump/sonic_dump_random2.tar.gz", st_size=30)
            patcher.fs.create_file("/var/dump/sonic_dump_random3.tar.gz", st_size=30)
            ts_mod.handle_techsupport_creation_event("/var/dump/sonic_dump_random3.tar.gz")
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
        RedisSingleton.clearState()
        set_auto_ts_cfg(techsupport_cleanup="enabled", max_techsupport_size="5")
        with Patcher() as patcher:
            patcher.fs.set_disk_usage(1000, path="/var/dump/")
            patcher.fs.create_file("/var/dump/sonic_dump_random1.tar.gz", st_size=25)
            patcher.fs.create_file("/var/dump/sonic_dump_random2.tar.gz", st_size=25)
            patcher.fs.create_file("/var/dump/sonic_dump_random3.tar.gz", st_size=25)
            ts_mod.handle_techsupport_creation_event("/var/dump/sonic_dump_random3.tar.gz")
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
        RedisSingleton.clearState()
        set_auto_ts_cfg(techsupport_cleanup="enabled", max_techsupport_size="5")
        RedisHandle.data["STATE_DB"] = {}
        RedisHandle.data["STATE_DB"][ts_mod.TS_MAP] = {"sonic_dump_random1.tar.gz": "orchagent;1575985",
                                                       "sonic_dump_random2.tar.gz": "syncd;1575988"}
        with Patcher() as patcher:
            patcher.fs.set_disk_usage(1000, path="/var/dump/")
            patcher.fs.create_file("/var/dump/sonic_dump_random1.tar.gz", st_size=25)
            patcher.fs.create_file("/var/dump/sonic_dump_random2.tar.gz", st_size=25)
            patcher.fs.create_file("/var/dump/sonic_dump_random3.tar.gz", st_size=25)
            ts_mod.handle_techsupport_creation_event("/var/dump/sonic_dump_random3.tar.gz")
            current_fs = os.listdir(ts_mod.TS_DIR)
            print(current_fs)
            assert len(current_fs) == 2
            assert "sonic_dump_random1.tar.gz" not in current_fs
            assert "sonic_dump_random2.tar.gz" in current_fs
            assert "sonic_dump_random3.tar.gz" in current_fs
        assert "sonic_dump_random2.tar.gz" in RedisHandle.data["STATE_DB"][ts_mod.TS_MAP]
        assert "sonic_dump_random1.tar.gz" not in RedisHandle.data["STATE_DB"][ts_mod.TS_MAP]