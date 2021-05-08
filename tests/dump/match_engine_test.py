import json, os, sys
import jsonpatch
import unittest
import pytest
from unittest.mock import MagicMock, Mock

from dump.redis_match import MatchEngine, error_dict, MatchRequest

test_path = os.path.join(os.path.abspath(__file__),"../")
mock_db_path = os.path.join(test_path,"mock_tables")

sys.path.append(test_path)
#sys.path.append(modules_path)

from mock_tables import dbconnector


@pytest.fixture(scope="module", autouse=True)
def mock_setup():
    print("SETUP")
    os.environ['UTILITIES_UNIT_TESTING'] = "1"
    dbconnector.dedicated_dbs['CONFIG_DB'] = os.path.join(mock_db_path, "config_db.json") 
    dbconnector.dedicated_dbs['APPL_DB'] = os.path.join(mock_db_path, "appl_db.json") 
    dbconnector.dedicated_dbs['ASIC_DB'] = os.path.join(mock_db_path, "asic_db.json")
    dbconnector.dedicated_dbs['STATE_DB'] = os.path.join(mock_db_path, "state_db.json")
    yield
    print("TEARDOWN")
    os.environ["UTILITIES_UNIT_TESTING"] = "0"

class TestInvalidRequest(unittest.TestCase):
    
    def __init__(self, *args, **kwargs):
        super(TestInvalidRequest, self).__init__(*args, **kwargs)
        self.match_engine = MatchEngine()
    
    def test_bad_request(self):
        req = []
        ret = self.match_engine.fetch(req)
        assert ret["error"] == error_dict["INV_REQ"]
    
    def test_no_source(self):
        req = MatchRequest()
        ret = self.match_engine.fetch(req)
        assert ret["error"] == error_dict["NO_SRC"]
    
    def test_vague_source(self):  
        req = MatchRequest()
        req.db = "CONFIG_DB"
        req.file = "/etc/sonic/copp_cfg.json"
        ret = self.match_engine.fetch(req)
        assert ret["error"] == error_dict["SRC_VAGUE"]
    
    def test_no_file(self):  
        req = MatchRequest()
        req.file = os.path.join(mock_db_path, "random_db.json")
        ret = self.match_engine.fetch(req)
        assert ret["error"] == error_dict["NO_FILE"]

    def test_invalid_db(self):  
        req = MatchRequest()
        req.db = "CONFIGURATION_DB"
        ret = self.match_engine.fetch(req)
        assert ret["error"] == error_dict["INV_DB"]
    
    def test_bad_key_regex(self):  
        req = MatchRequest()
        req.db = "CONFIG_DB"
        req.table = "PORT"
        req.key_regex = ""
        ret = self.match_engine.fetch(req)
        assert ret["error"] == error_dict["NO_KEY"]
    
    def test_no_value(self):  
        req = MatchRequest()
        req.db = "APPL_DB"
        req.table = "COPP_TABLE"
        req.key_regex = "*"
        req.field = "trap_ids"
        req.value = ""
        ret = self.match_engine.fetch(req)
        assert ret["error"] == error_dict["NO_VALUE"]
    
    def test_no_table(self):  
        req = MatchRequest()
        req.db = "APPL_DB"
        req.table = ""
        req.key_regex = "*"
        req.field = "trap_ids"
        req.value = "bgpv6"
        ret = self.match_engine.fetch(req)
        assert ret["error"] == error_dict["NO_TABLE"]
    
    def test_invalid_table(self):
        
        req = MatchRequest()
        req.db = "CONFIG_DB"
        req.table = "COPP_TRAP"
        req.key_regex = "*"
        req.field = "trap_ids"
        req.value = "sample_packet"
        ret = self.match_engine.fetch(req)
        assert ret["error"] == error_dict["INV_TABLE"]

class TestMatchEngine(unittest.TestCase):
    
    def __init__(self, *args, **kwargs):
        super(TestInvalidRequest, self).__init__(*args, **kwargs)
        self.match_engine = MatchEngine()
    
    def test_key_regex_wildcard(self):
        req = MatchRequest()
        req.db = "CONFIG_DB"
        req.table = "SFLOW_COLLECTOR"
        req.key_regex = ".*"
        ret = self.match_engine.fetch(req)
        assert ret["error"] == ""
        assert len(ret["keys"]) == 2
        assert "SFLOW_COLLECTOR|ser5" in ret['keys']
        assert "SFLOW_COLLECTOR|prod" in ret['keys'] 
    
    def test_key_regex_complex(self):
        req = MatchRequest()
        req.db = "CONFIG_DB"
        req.table = "ACL_RULE"
        req.key_regex = "EVER.*\|*"
        ret = self.match_engine.fetch(req)
        assert ret["error"] == ""
        assert len(ret["keys"]) == 2
        assert "ACL_RULE|EVERFLOW|RULE_6" in ret['keys']
        assert "ACL_RULE|EVERFLOW|RULE_08" in ret['keys'] 
    
    def test_field_value_match(self):
        req = MatchRequest()
        req.db = "CONFIG_DB"
        req.table = "ACL_TABLE"
        req.field = "policy_desc"
        req.value = "SSH_ONLY"
        ret = self.match_engine.fetch(req)
        assert ret["error"] == ""
        assert len(ret["keys"]) == 1
        assert "ACL_TABLE|SSH_ONLY" in ret['keys']
        
    def test_field_value_match_list_type(self):
        req = MatchRequest()
        req.db = "APPL_DB"
        req.table = "PORT_TABLE"
        req.field = "lanes"
        req.value = "202"
        ret = self.match_engine.fetch(req)
        assert ret["error"] == ""
        assert len(ret["keys"]) == 1
        assert "PORT_TABLE|Ethernet200" in ret['keys']
    
    def test_field_value_no_match(self):
        req = MatchRequest()
        req.db = "STATE_DB"
        req.table = "FAN_INFO"
        req.key_regex = ".*"
        req.field = "led_status"
        req.value = "yellow"
        ret = self.match_engine.fetch(req)
        assert ret["error"] == ""
        assert len(ret["keys"]) == 0
    
    def test_return_keys(self):
        req = MatchRequest()
        req.db = "STATE_DB"
        req.table = "REBOOT_CAUSE"
        req.return_fields = "cause"
        ret = self.match_engine.fetch(req)
        assert ret["error"] == ""
        assert len(ret["keys"]) == 2
        assert "warm-reboot" == ret["return_values"]["REBOOT_CAUSE|2020_10_09_04_53_58"]
        assert "reboot" == ret["return_values"]["REBOOT_CAUSE|2020_10_09_02_33_06"]
    
    def test_return_fields_with_key_filtering(self):
        req = MatchRequest()
        req.db = "STATE_DB"
        req.table = "REBOOT_CAUSE"
        req.key_regex = "2020_10_09_02.*"
        req.return_fields = "cause"
        ret = self.match_engine.fetch(req)
        assert ret["error"] == ""
        assert len(ret["keys"]) == 1
        assert "reboot" == ret["return_values"]["REBOOT_CAUSE|2020_10_09_02_33_06"]
    
    def test_return_fields_with_field_value_filtering(self):
        req = MatchRequest()
        req.db = "STATE_DB"
        req.table = "CHASSIS_MODULE_TABLE"
        req.field = "oper_status"
        req.value = "Offline"
        req.return_fields = "slot"
        ret = self.match_engine.fetch(req)
        assert ret["error"] == ""
        assert len(ret["keys"]) == 1
        assert "18" == ret["return_values"]["CHASSIS_MODULE_TABLE|FABRIC-CARD1"]
    
    def test_return_fields_with_all_filtering(self):
        req = MatchRequest()
        req.db = "STATE_DB"
        req.table = "VXLAN_TUNNEL_TABLE"
        req.key_regex = "EVPN_25\.25\.25\.2.*"
        req.field = "operstatus"
        req.value = "down"
        req.return_fields = "src_ip"
        ret = self.match_engine.fetch(req)
        assert ret["error"] == ""
        assert len(ret["keys"]) == 3
        assert "1.1.1.1" == ret["return_values"]["VXLAN_TUNNEL_TABLE|EVPN_25.25.25.25"]
        assert "1.1.1.1" == ret["return_values"]["VXLAN_TUNNEL_TABLE|EVPN_25.25.25.26"]
        assert "1.1.1.1" == ret["return_values"]["VXLAN_TUNNEL_TABLE|EVPN_25.25.25.27"]
    
    def test_just_keys_false(self):
        req = MatchRequest()
        req.db = "APPL_DB"
        req.table = "SFLOW"
        req.key_regex = "global"
        req.just_keys = False
        ret = self.match_engine.fetch(req)
        assert ret["error"] == ""
        assert len(ret["keys"]) == 1
        recv_dict = ret["keys"][0]
        assert isinstance(recv_dict, dict)
        exp_dict =  {"SFLOW:global": {"admin_state": "up", "polling_interval": "0"}}
        assert set(exp_dict.keys()) == set(recv_dict.keys())
        assert "admin_state" in recv_dict["SFLOW:global"]
        assert "polling_interval" in recv_dict["SFLOW:global"]
        assert recv_dict["SFLOW:global"]["admin_state"] == exp_dict["SFLOW:global"]["admin_state"]
        assert recv_dict["SFLOW:global"]["polling_interval"] == exp_dict["SFLOW:global"]["polling_interval"]
    
    def test_file_source(self):
        req = MatchRequest()
        req.file = os.path.join(os.path.abspath(__file__),"files/copp_cfg.json")
        req.table = "COPP_TABLE"
        req.field = "trap_ids"
        req.value = "arp_req"
        ret = self.match_engine.fetch(req)
        assert ret["error"] == ""
        assert len(ret["keys"]) == 1
        assert "arp" in ret["keys"]      
        
    
    
    
    
    
    
    
    
    
    
    
    
