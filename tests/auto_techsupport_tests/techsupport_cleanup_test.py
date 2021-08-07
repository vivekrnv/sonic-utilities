import os
import sys
import pytest
import pyfakefs 
import unittest
from pyfakefs.fake_filesystem_unittest import Patcher
from utilities_common.general import load_module_from_source

from .mock_tables import dbconnector

test_path = os.path.dirname(os.path.abspath(__file__))
modules_path = os.path.dirname(test_path)
scripts_path = os.path.join(modules_path, 'scripts')
sys.path.insert(0, modules_path)

# Load the file under test
script_path = os.path.join(scripts_path, 'techsupport_cleanup')
ts_mod = load_module_from_source('techsupport_cleanup', script_path)

ts_mod.SonicV2Connector = dbconnector.SonicV2Connector
redis_handle = dbconnector.SonicV2Connector(host="127.0.0.1")

"""
AUTO_TS = "AUTO_TECHSUPPORT|global"
CFG_DB = "CONFIG_DB"
CFG_STATE = "state"
CFG_MAX_TS = "max_techsupport_size"
TS_DIR = "/var/dump"
TS_PTRN = "sonic_dump_*.tar*"
TIME_BUF = 20

# State DB Attributes
STATE_DB = "STATE_DB"
TS_MAP = "AUTO_TECHSUPPORT|TS_CORE_MAP"
"""

class TestTechsupportCreationEvent(unittest.TestCase):
    
    def setUp(self):
        self.orig_time_buf = ts_mod.TIME_BUF
        ts_mod.TIME_BUF = 1 # Patch the buf to 1 sec
        redis_handle.connect("CONFIG_DB")
        redis_handle.connect("STATE_DB")

    def tearDown(self):
        ts_mod.TIME_BUF = self.orig_time_buf
    
    def set_auto_ts_cfg(self, **kwargs):
        state = kwargs[ts_mod.CFG_STATE] if ts_mod.CFG_STATE in kwargs else "disabled"
        max_ts = kwargs[ts_mod.CFG_MAX_TS] if ts_mod.CFG_MAX_TS in kwargs else "0"
        redis_handle.set(ts_mod.CFG_DB, ts_mod.AUTO_TS, ts_mod.CFG_STATE, state)
        redis_handle.set(ts_mod.CFG_DB, ts_mod.AUTO_TS, ts_mod.CFG_MAX_TS, max_ts)
        print("state: {}, max_techsupport_size: {}".format(state, max_ts))
    
    def test_no_cleanup(self):
        self.set_auto_ts_cfg(state="enabled", max_techsupport_size="10")
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
        self.set_auto_ts_cfg(state="enabled", max_techsupport_size="5")
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
        
        
    
    