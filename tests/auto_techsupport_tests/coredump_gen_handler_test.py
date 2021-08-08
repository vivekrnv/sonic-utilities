import os
import sys
import pyfakefs 
import unittest
from pyfakefs.fake_filesystem_unittest import Patcher
from swsscommon import swsscommon
from .shared_state_mock import RedisSingleton, MockConn
from utilities_common.general import load_module_from_source

# Mock the SonicV2Connector
swsscommon.SonicV2Connector = MockConn

curr_test_path = os.path.abspath(os.path.join(os.path.abspath(__file__), "../"))
test_dir_path = os.path.dirname(curr_test_path)
modules_path = os.path.dirname(test_dir_path)
scripts_path = os.path.join(modules_path, 'scripts')
sys.path.insert(0, modules_path)

# Load the file under test
script_path = os.path.join(scripts_path, 'coredump_gen_handler')
cdump_mod = load_module_from_source('coredump_gen_handler', script_path)

# Mock Handle to the data inside the Redis
RedisHandle = RedisSingleton.getInstance()

def set_auto_ts_cfg(**kwargs):
    state = kwargs[cdump_mod.CFG_STATE] if cdump_mod.CFG_STATE in kwargs else "disabled"
    cooloff = kwargs[cdump_mod.COOLOFF] if cdump_mod.COOLOFF in kwargs else "0"
    core_usage = kwargs[cdump_mod.CFG_CORE_USAGE] if cdump_mod.CFG_CORE_USAGE in kwargs else "0"
    if cdump_mod.CFG_DB not in RedisHandle.data:
        RedisHandle.data[cdump_mod.CFG_DB] = {}
    RedisHandle.data[cdump_mod.CFG_DB][cdump_mod.AUTO_TS] = {cdump_mod.CFG_STATE : state, 
                                                         cdump_mod.COOLOFF : cooloff,
                                                         cdump_mod.CFG_CORE_USAGE : core_usage} 

def set_feature_table_cfg(ts_swss="disabled", ts_syncd="disabled", cooloff_swss="0", cooloff_syncd="0"):
    if cdump_mod.CFG_DB not in RedisHandle.data:
        RedisHandle.data[cdump_mod.CFG_DB] = {}
    RedisHandle.data[cdump_mod.CFG_DB][cdump_mod.FEATURE.format("swss")] = {cdump_mod.TS : ts_swss,
                                                                            cdump_mod.COOLOFF : cooloff_swss}
    RedisHandle.data[cdump_mod.CFG_DB][cdump_mod.FEATURE.format("syncd")] =  {cdump_mod.TS : ts_syncd,
                                                                              cdump_mod.COOLOFF : cooloff_syncd}
                                            
swss_critical_proc = """\
program:orchagent
program:portsyncd
program:neighsyncd
program:vlanmgrd
program:intfmgrd
program:portmgrd
program:buffermgrd
program:vrfmgrd
program:nbrmgrd
program:vxlanmgrd
"""

syncd_critical_proc = """\
program:syncd
"""

def mock_generic_cmd(cmd):
    if "docker exec -t swss cat /etc/supervisor/critical_processes" in cmd:
        return 0, swss_critical_proc, ""
    elif "docker exec -t syncd cat /etc/supervisor/critical_processes" in cmd:
        return 0, syncd_critical_proc, ""
    else:
        print("ERR: Invalid Command Invoked: " + cmd)
        return 1, "", "Invalid Command: "

class TestCoreDumpCreationEvent(unittest.TestCase):
    
    def setUp(self):
        self.orig_time_buf = cdump_mod.TIME_BUF
        cdump_mod.TIME_BUF = 0.5 # Patch the buf 

    def tearDown(self):
        cdump_mod.TIME_BUF = self.orig_time_buf
    
    def test_invoc_ts_without_cooloff(self):
        """
        Scenario: AUTO_TECHSUPPORT is enabled. No gloal Cooloff and per process cooloff specified
                  Check if techsupport is invoked and file is created
        """
        RedisSingleton.clearState()
        set_auto_ts_cfg(state="enabled")
        set_feature_table_cfg(ts_swss="enabled")
        with Patcher() as patcher:
            def mock_cmd(cmd):
                cmd_str = " ".join(cmd)
                if "show techsupport" in cmd_str:
                    patcher.fs.create_file("/var/dump/sonic_dump_random999.tar.gz")
                else:
                    return mock_generic_cmd(cmd)
                return 0, "", ""
            cdump_mod.subprocess_exec = mock_cmd 
            patcher.fs.create_file("/var/dump/sonic_dump_random998.tar.gz")
            patcher.fs.create_file("/var/core/orchagent.12345.123.core.gz")
            cls = cdump_mod.CoreDumpCreateHandle("orchagent.12345.123.core.gz")
            cls.handle_core_dump_creation_event()
            assert "sonic_dump_random999.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random998.tar.gz" in os.listdir(cdump_mod.TS_DIR)
        