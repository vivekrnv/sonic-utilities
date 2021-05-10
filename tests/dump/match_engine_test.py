import json, os, sys
import jsonpatch
import unittest
import pytest
from dump.redis_match import MatchEngine, error_dict, MatchRequest
from deepdiff import DeepDiff

test_path = os.path.join(os.path.abspath(__file__),"../")
mock_db_path = os.path.join(test_path,"mock_tables")

sys.path.append(test_path)

from mock_tables import dbconnector

@pytest.fixture(scope="module", autouse=True)
def mock_setup():
    print("SETUP")
    dbconnector.dedicated_dbs['CONFIG_DB'] = os.path.join(mock_db_path, "config_db.json") 
    dbconnector.dedicated_dbs['APPL_DB'] = os.path.join(mock_db_path, "appl_db.json") 
    dbconnector.dedicated_dbs['ASIC_DB'] = os.path.join(mock_db_path, "asic_db.json")
    dbconnector.dedicated_dbs['STATE_DB'] = os.path.join(mock_db_path, "state_db.json")
    os.environ["VERBOSE"] = "1"
    yield
    print("TEARDOWN")
    os.environ["VERBOSE"] = "0"


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
    
    def test_bad_key_pattern(self):  
        req = MatchRequest()
        req.db = "CONFIG_DB"
        req.table = "PORT"
        req.key_pattern = ""
        ret = self.match_engine.fetch(req)
        assert ret["error"] == error_dict["NO_KEY"]
    
    def test_no_value(self):  
        req = MatchRequest()
        req.db = "APPL_DB"
        req.table = "COPP_TABLE"
        req.key_pattern = "*"
        req.field = "trap_ids"
        req.value = ""
        ret = self.match_engine.fetch(req)
        assert ret["error"] == error_dict["NO_VALUE"]
    
    def test_no_table(self):  
        req = MatchRequest()
        req.db = "APPL_DB"
        req.table = ""
        req.key_pattern = "*"
        req.field = "trap_ids"
        req.value = "bgpv6"
        ret = self.match_engine.fetch(req)
        assert ret["error"] == error_dict["NO_TABLE"]
    
    def test_just_keys_return_fields_compat(self):
        req = MatchRequest()
        req.db = "APPL_DB"
        req.table = "COPP_TABLE"
        req.key_pattern = "*"
        req.field = "trap_ids"
        req.value = ""
        req.just_keys = False
        req.return_fields = ["trap_group"]
        ret = self.match_engine.fetch(req)
        assert ret["error"] == error_dict["JUST_KEYS_COMPAT"]
    
    def test_invalid_combination(self):
        
        req = MatchRequest()
        req.db = "CONFIG_DB"
        req.table = "COPP_TRAP"
        req.key_pattern = "*"
        req.field = "trap_ids"
        req.value = "sample_packet"
        ret = self.match_engine.fetch(req)
        assert ret["error"] == error_dict["INV_PTTRN"]
    
    def test_return_fields_bad_format(self):
        req = MatchRequest()
        req.db = "STATE_DB"
        req.table = "REBOOT_CAUSE"
        req.return_fields = "cause"
        ret = self.match_engine.fetch(req)
        assert ret["error"] == error_dict["BAD_FORMAT_RE_FIELDS"]

class TestMatchEngine(unittest.TestCase):
    
    def __init__(self, *args, **kwargs):
        super(TestMatchEngine, self).__init__(*args, **kwargs)
        self.match_engine = MatchEngine()
    
    def test_key_pattern_wildcard(self):
        req = MatchRequest()
        req.db = "CONFIG_DB"
        req.table = "SFLOW_COLLECTOR"
        req.key_pattern = "*"
        ret = self.match_engine.fetch(req)
        assert ret["error"] == ""
        assert len(ret["keys"]) == 2
        assert "SFLOW_COLLECTOR|ser5" in ret['keys']
        assert "SFLOW_COLLECTOR|prod" in ret['keys'] 
    
    def test_key_pattern_complex(self):
        req = MatchRequest()
        req.db = "CONFIG_DB"
        req.table = "ACL_RULE"
        req.key_pattern = "EVERFLOW*"
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
        assert "PORT_TABLE:Ethernet200" in ret['keys']
    
    def test_for_no_match(self):
        req = MatchRequest()
        req.db = "ASIC_DB"
        req.table = "ASIC_STATE:SAI_OBJECT_TYPE_SWITCH"
        req.field = "SAI_SWITCH_ATTR_SRC_MAC_ADDRESS"
        req.value = "DE:AD:EE:EE:EE"
        ret = self.match_engine.fetch(req)
        assert ret["error"] == ""
        assert len(ret["keys"]) == 0
    
    def test_for_no_key_match(self):
        req = MatchRequest()
        req.db = "ASIC_DB"
        req.table = "ASIC_STATE:SAI_OBJECT_TYPE_SWITCH"
        req.key_pattern = "oid:0x22*"
        ret = self.match_engine.fetch(req)
        assert ret["error"] == error_dict["INV_PTTRN"]
    
    def test_field_value_no_match(self):
        req = MatchRequest()
        req.db = "STATE_DB"
        req.table = "FAN_INFO"
        req.key_pattern = "*"
        req.field = "led_status"
        req.value = "yellow"
        ret = self.match_engine.fetch(req)
        assert ret["error"] == ""
        assert len(ret["keys"]) == 0
    
    def test_return_keys(self):
        req = MatchRequest()
        req.db = "STATE_DB"
        req.table = "REBOOT_CAUSE"
        req.return_fields = ["cause"]
        ret = self.match_engine.fetch(req)
        assert ret["error"] == ""
        assert len(ret["keys"]) == 2
        assert "warm-reboot" == ret["return_values"]["REBOOT_CAUSE|2020_10_09_04_53_58"]["cause"]
        assert "reboot" == ret["return_values"]["REBOOT_CAUSE|2020_10_09_02_33_06"]["cause"]
    
    def test_return_fields_with_key_filtering(self):
        req = MatchRequest()
        req.db = "STATE_DB"
        req.table = "REBOOT_CAUSE"
        req.key_pattern = "2020_10_09_02*"
        req.return_fields = ["cause"]
        ret = self.match_engine.fetch(req)
        assert ret["error"] == ""
        assert len(ret["keys"]) == 1
        assert "reboot" == ret["return_values"]["REBOOT_CAUSE|2020_10_09_02_33_06"]["cause"]
    
    def test_return_fields_with_field_value_filtering(self):
        req = MatchRequest()
        req.db = "STATE_DB"
        req.table = "CHASSIS_MODULE_TABLE"
        req.field = "oper_status"
        req.value = "Offline"
        req.return_fields = ["slot"]
        ret = self.match_engine.fetch(req)
        assert ret["error"] == ""
        assert len(ret["keys"]) == 1
        assert "18" == ret["return_values"]["CHASSIS_MODULE_TABLE|FABRIC-CARD1"]["slot"]
    
    def test_return_fields_with_all_filtering(self):
        req = MatchRequest()
        req.db = "STATE_DB"
        req.table = "VXLAN_TUNNEL_TABLE"
        req.key_pattern = "EVPN_25.25.25.2*"
        req.field = "operstatus"
        req.value = "down"
        req.return_fields = ["src_ip"]
        ret = self.match_engine.fetch(req)
        assert ret["error"] == ""
        assert len(ret["keys"]) == 3
        assert "1.1.1.1" == ret["return_values"]["VXLAN_TUNNEL_TABLE|EVPN_25.25.25.25"]["src_ip"]
        assert "1.1.1.1" == ret["return_values"]["VXLAN_TUNNEL_TABLE|EVPN_25.25.25.26"]["src_ip"]
        assert "1.1.1.1" == ret["return_values"]["VXLAN_TUNNEL_TABLE|EVPN_25.25.25.27"]["src_ip"]
    
    def test_just_keys_false(self):
        req = MatchRequest()
        req.db = "CONFIG_DB"
        req.table = "SFLOW"
        req.key_pattern = "global"
        req.just_keys = False
        ret = self.match_engine.fetch(req)
        assert ret["error"] == ""
        assert len(ret["keys"]) == 1
        recv_dict = ret["keys"][0]
        assert isinstance(recv_dict, dict)
        exp_dict =  {"SFLOW|global": {"admin_state": "up", "polling_interval": "0"}}
        ddiff = DeepDiff(exp_dict, recv_dict)
        assert not ddiff, ddiff
    
        
    def test_file_source(self):
        req = MatchRequest()
        req.file = os.path.join(os.path.dirname(__file__),"files/copp_cfg.json")
        req.table = "COPP_TRAP"
        req.field = "trap_ids"
        req.value = "arp_req"
        ret = self.match_engine.fetch(req)
        assert ret["error"] == ""
        assert len(ret["keys"]) == 1
        assert "arp" in ret["keys"] 
        
    def test_file_source_with_key_ptrn(self):
        req = MatchRequest()
        req.file = os.path.join(os.path.dirname(__file__),"files/copp_cfg.json")
        req.table = "COPP_GROUP"
        req.key_pattern = "queue4*"
        req.field = "red_action"
        req.value = "drop"
        ret = self.match_engine.fetch(req)
        assert ret["error"] == ""
        assert len(ret["keys"]) == 1
        assert "queue4_group2" in ret["keys"] 
