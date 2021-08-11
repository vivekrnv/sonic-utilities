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

def set_auto_ts_cfg(**kwargs):
    state = kwargs[cdump_mod.CFG_STATE] if cdump_mod.CFG_STATE in kwargs else "disabled"
    cooloff = kwargs[cdump_mod.COOLOFF] if cdump_mod.COOLOFF in kwargs else "0"
    core_usage = kwargs[cdump_mod.CFG_CORE_USAGE] if cdump_mod.CFG_CORE_USAGE in kwargs else "0"
    since_cfg = kwargs[cdump_mod.CFG_SINCE] if cdump_mod.CFG_SINCE in kwargs else "None"
    if cdump_mod.CFG_DB not in RedisHandle.data:
        RedisHandle.data[cdump_mod.CFG_DB] = {}
    RedisHandle.data[cdump_mod.CFG_DB][cdump_mod.AUTO_TS] = {cdump_mod.CFG_STATE : state, 
                                                         cdump_mod.COOLOFF : cooloff,
                                                         cdump_mod.CFG_CORE_USAGE : core_usage} 

def set_feature_table_cfg(ts="disabled", cooloff="0", container_name="swss"):
    if cdump_mod.CFG_DB not in RedisHandle.data:
        RedisHandle.data[cdump_mod.CFG_DB] = {}
    RedisHandle.data[cdump_mod.CFG_DB][cdump_mod.FEATURE.format(container_name)] = {cdump_mod.TS : ts,
                                                                                    cdump_mod.COOLOFF : cooloff}
                                            
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
    elif "date --date=\"2 days ago\"" in cmd:
        return 0, "", ""
    elif "date --date=\"random\"" in cmd:
        return 1, "", "Invalid Date Format"
    else:
        return 1, "", "Invalid Command: "

class TestCoreDumpCreationEvent(unittest.TestCase):
     
    def test_invoc_ts_without_cooloff(self):
        """
        Scenario: AUTO_TECHSUPPORT is enabled. No global Cooloff and per process cooloff specified
                  Check if techsupport is invoked and file is created
        """
        RedisSingleton.clearState()
        set_auto_ts_cfg(state="enabled")
        set_feature_table_cfg(ts="enabled")
        with Patcher() as patcher:
            def mock_cmd(cmd):
                cmd_str = " ".join(cmd)
                if "show techsupport" in cmd_str:
                    patcher.fs.create_file("/var/dump/sonic_dump_random999.tar.gz")
                else:
                    return mock_generic_cmd(cmd_str)
                return 0, "", ""
            cdump_mod.subprocess_exec = mock_cmd 
            patcher.fs.create_file("/var/dump/sonic_dump_random998.tar.gz")
            patcher.fs.create_file("/var/core/orchagent.12345.123.core.gz")
            cls = cdump_mod.CoreDumpCreateHandle("orchagent.12345.123.core.gz")
            cls.handle_core_dump_creation_event()
            assert "sonic_dump_random999.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random998.tar.gz" in os.listdir(cdump_mod.TS_DIR)
    
    def test_invoc_ts_state_db_update(self):
        """
        Scenario: AUTO_TECHSUPPORT is enabled. No global Cooloff and per process cooloff specified
                  Check if techsupport is invoked, file is created and State DB in updated
        """
        RedisSingleton.clearState()
        set_auto_ts_cfg(state="enabled")
        set_feature_table_cfg(ts="enabled")
        RedisHandle.data["STATE_DB"] = {}
        RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP] = {"sonic_dump_random1.tar.gz" : "portsyncd;1575985",
                                                          "sonic_dump_random2.tar.gz" : "syncd;1575988"}
        with Patcher() as patcher:
            def mock_cmd(cmd):
                cmd_str = " ".join(cmd)
                if "show techsupport" in cmd_str:
                    patcher.fs.create_file("/var/dump/sonic_dump_random3.tar.gz")
                else:
                    return mock_generic_cmd(cmd_str)
                return 0, "", ""
            cdump_mod.subprocess_exec = mock_cmd
            patcher.fs.create_file("/var/dump/sonic_dump_random1.tar.gz") 
            patcher.fs.create_file("/var/dump/sonic_dump_random2.tar.gz")
            patcher.fs.create_file("/var/core/orchagent.12345.123.core.gz")
            cls = cdump_mod.CoreDumpCreateHandle("orchagent.12345.123.core.gz")
            cls.handle_core_dump_creation_event()
            assert "sonic_dump_random1.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random2.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random3.tar.gz" in os.listdir(cdump_mod.TS_DIR)
        assert "sonic_dump_random1.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "sonic_dump_random2.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "sonic_dump_random3.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "orchagent" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]["sonic_dump_random3.tar.gz"]
    
    def test_global_cooloff(self):
        """
        Scenario: AUTO_TECHSUPPORT is enabled. But global cooloff is not passed
                  Check if techsupport is not invoked
        """
        RedisSingleton.clearState()
        set_auto_ts_cfg(state="enabled", cooloff="1")
        set_feature_table_cfg(ts="enabled")
        RedisHandle.data["STATE_DB"] = {}
        RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP] = {"sonic_dump_random1.tar.gz" : "portsyncd;1575985",
                                                          "sonic_dump_random2.tar.gz" : "syncd;1575988"}
        with Patcher() as patcher:
            def mock_cmd(cmd):
                cmd_str = " ".join(cmd)
                if "show techsupport" in cmd_str:
                    patcher.fs.create_file("/var/dump/sonic_dump_random3.tar.gz")
                else:
                    return mock_generic_cmd(cmd_str)
                return 0, "", ""
            cdump_mod.subprocess_exec = mock_cmd
            patcher.fs.create_file("/var/dump/sonic_dump_random1.tar.gz") 
            patcher.fs.create_file("/var/dump/sonic_dump_random2.tar.gz")
            patcher.fs.create_file("/var/core/orchagent.12345.123.core.gz")
            cls = cdump_mod.CoreDumpCreateHandle("orchagent.12345.123.core.gz")
            cls.handle_core_dump_creation_event()
            assert "sonic_dump_random1.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random2.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random3.tar.gz" not in os.listdir(cdump_mod.TS_DIR)
        assert "sonic_dump_random1.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "sonic_dump_random2.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "sonic_dump_random3.tar.gz" not in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
    
    def test_per_proc_cooloff(self):
        """
        Scenario: AUTO_TECHSUPPORT is enabled. Global Cooloff is passed but per process isn't
                  Check if techsupport is not invoked
        """
        RedisSingleton.clearState()
        set_auto_ts_cfg(state="enabled", cooloff="0.25")
        set_feature_table_cfg(ts="enabled", cooloff="10")
        RedisHandle.data["STATE_DB"] = {}
        RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP] = {"sonic_dump_random1.tar.gz" : "orchagent;{}".format(int(time.time())),
                                                          "sonic_dump_random2.tar.gz" : "syncd;1575988"}
        with Patcher() as patcher:
            def mock_cmd(cmd):
                cmd_str = " ".join(cmd)
                if "show techsupport" in cmd_str:
                    patcher.fs.create_file("/var/dump/sonic_dump_random3.tar.gz")
                else:
                    return mock_generic_cmd(cmd_str)
                return 0, "", ""
            cdump_mod.subprocess_exec = mock_cmd
            patcher.fs.create_file("/var/dump/sonic_dump_random1.tar.gz") 
            patcher.fs.create_file("/var/dump/sonic_dump_random2.tar.gz")
            patcher.fs.create_file("/var/core/orchagent.12345.123.core.gz")
            cls = cdump_mod.CoreDumpCreateHandle("orchagent.12345.123.core.gz")
            time.sleep(0.5) # wait for cooloff to pass
            cls.handle_core_dump_creation_event()
            assert "sonic_dump_random1.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random2.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random3.tar.gz" not in os.listdir(cdump_mod.TS_DIR)
        assert "sonic_dump_random1.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "sonic_dump_random2.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "sonic_dump_random3.tar.gz" not in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
    
    def test_invoc_ts_after_cooloff(self):
        """
        Scenario: AUTO_TECHSUPPORT is enabled. Global Cooloff and per proc cooloff is passed
                  Check if techsupport is invoked
        """
        RedisSingleton.clearState()
        set_auto_ts_cfg(state="enabled", cooloff="0.1")
        set_feature_table_cfg(ts="enabled", cooloff="0.5")
        RedisHandle.data["STATE_DB"] = {}
        RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP] = {"sonic_dump_random1.tar.gz" : "orchagent;{}".format(int(time.time())),
                                                          "sonic_dump_random2.tar.gz" : "syncd;1575988"}
        with Patcher() as patcher:
            def mock_cmd(cmd):
                cmd_str = " ".join(cmd)
                if "show techsupport" in cmd_str:
                    patcher.fs.create_file("/var/dump/sonic_dump_random3.tar.gz")
                else:
                    return mock_generic_cmd(cmd_str)
                return 0, "", ""
            cdump_mod.subprocess_exec = mock_cmd
            patcher.fs.create_file("/var/dump/sonic_dump_random1.tar.gz") 
            patcher.fs.create_file("/var/dump/sonic_dump_random2.tar.gz")
            patcher.fs.create_file("/var/core/orchagent.12345.123.core.gz")
            cls = cdump_mod.CoreDumpCreateHandle("orchagent.12345.123.core.gz")
            time.sleep(0.5) # wait for cooloff to pass
            cls.handle_core_dump_creation_event()
            assert "sonic_dump_random1.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random2.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random3.tar.gz" in os.listdir(cdump_mod.TS_DIR)
        assert "sonic_dump_random1.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "sonic_dump_random2.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "sonic_dump_random3.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "orchagent" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]["sonic_dump_random3.tar.gz"]
    
    def test_non_critical_proc(self):
        """
        Scenario: AUTO_TECHSUPPORT is enabled. A Non-critical Process dump is used to invoke this script
                  Check if techsupport is not invoked
        """
        RedisSingleton.clearState()
        set_auto_ts_cfg(state="enabled")
        set_feature_table_cfg(ts="enabled")
        RedisHandle.data["STATE_DB"] = {}
        RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP] = {"sonic_dump_random1.tar.gz" : "portsyncd;1575985",
                                                          "sonic_dump_random2.tar.gz" : "syncd;1575988"}
        with Patcher() as patcher:
            def mock_cmd(cmd):
                cmd_str = " ".join(cmd)
                if "show techsupport" in cmd_str:
                    patcher.fs.create_file("/var/dump/sonic_dump_random3.tar.gz")
                else:
                    return mock_generic_cmd(cmd_str)
                return 0, "", ""
            cdump_mod.subprocess_exec = mock_cmd
            patcher.fs.create_file("/var/dump/sonic_dump_random1.tar.gz") 
            patcher.fs.create_file("/var/dump/sonic_dump_random2.tar.gz")
            patcher.fs.create_file("/var/core/snmpd.12345.123.core.gz")
            cls = cdump_mod.CoreDumpCreateHandle("snmpd.12345.123.core.gz")
            cls.handle_core_dump_creation_event()
            assert "sonic_dump_random1.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random2.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random3.tar.gz" not in os.listdir(cdump_mod.TS_DIR)
        assert "sonic_dump_random1.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "sonic_dump_random2.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "sonic_dump_random3.tar.gz" not in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
    
    def test_feature_table_not_set(self):
        """
        Scenario: AUTO_TECHSUPPORT is enabled. A critical Process dump is used to invoke this script
                  But it is not enabled in FEATURE|* table. Check if techsupport is not invoked
        """
        RedisSingleton.clearState()
        set_auto_ts_cfg(state="enabled")
        set_feature_table_cfg(ts="disabled", cooloff="0.2", container_name="syncd")
        RedisHandle.data["STATE_DB"] = {}
        RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP] = {"sonic_dump_random1.tar.gz" : "portsyncd;{}".format(int(time.time())),
                                                          "sonic_dump_random2.tar.gz" : "syncd;1575988"}
        with Patcher() as patcher:
            def mock_cmd(cmd):
                cmd_str = " ".join(cmd)
                if "show techsupport" in cmd_str:
                    patcher.fs.create_file("/var/dump/sonic_dump_random3.tar.gz")
                else:
                    return mock_generic_cmd(cmd_str)
                return 0, "", ""
            cdump_mod.subprocess_exec = mock_cmd
            patcher.fs.create_file("/var/dump/sonic_dump_random1.tar.gz") 
            patcher.fs.create_file("/var/dump/sonic_dump_random2.tar.gz")
            patcher.fs.create_file("/var/core/portsyncd.12345.123.core.gz")
            cls = cdump_mod.CoreDumpCreateHandle("portsyncd.12345.123.core.gz")
            time.sleep(0.2)
            cls.handle_core_dump_creation_event()
            assert "sonic_dump_random1.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random2.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random3.tar.gz" not in os.listdir(cdump_mod.TS_DIR)
        assert "sonic_dump_random1.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "sonic_dump_random2.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "sonic_dump_random3.tar.gz" not in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
    
    def test_since_argument(self):
        """
        Scenario: AUTO_TECHSUPPORT is enabled. Global Cooloff and per proc cooloff is passed
                  Check if techsupport is invoked and since argument in properly applied
        """
        RedisSingleton.clearState()
        set_auto_ts_cfg(state="enabled", cooloff="0.1", since="random")
        set_feature_table_cfg(ts="enabled", cooloff="0.5")
        RedisHandle.data["STATE_DB"] = {}
        RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP] = {"sonic_dump_random1.tar.gz" : "orchagent;{}".format(int(time.time())),
                                                          "sonic_dump_random2.tar.gz" : "syncd;1575988"}
        with Patcher() as patcher:
            def mock_cmd(cmd):
                cmd_str = " ".join(cmd)
                if "show techsupport --since \"2 days ago\"" in cmd_str:
                    patcher.fs.create_file("/var/dump/sonic_dump_random3.tar.gz")
                else:
                    return mock_generic_cmd(cmd_str)
                return 0, "", ""
            cdump_mod.subprocess_exec = mock_cmd
            patcher.fs.create_file("/var/dump/sonic_dump_random1.tar.gz") 
            patcher.fs.create_file("/var/dump/sonic_dump_random2.tar.gz")
            patcher.fs.create_file("/var/core/orchagent.12345.123.core.gz")
            cls = cdump_mod.CoreDumpCreateHandle("orchagent.12345.123.core.gz")
            time.sleep(0.5) # wait for cooloff to pass
            cls.handle_core_dump_creation_event()
            assert "sonic_dump_random1.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random2.tar.gz" in os.listdir(cdump_mod.TS_DIR)
            assert "sonic_dump_random3.tar.gz" in os.listdir(cdump_mod.TS_DIR)
        assert "sonic_dump_random1.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "sonic_dump_random2.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "sonic_dump_random3.tar.gz" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]
        assert "orchagent" in RedisHandle.data["STATE_DB"][cdump_mod.TS_MAP]["sonic_dump_random3.tar.gz"]
        