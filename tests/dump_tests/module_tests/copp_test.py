import json, os, sys
import jsonpatch
import unittest
import pytest
from deepdiff import DeepDiff
from mock import patch
from dump.helper import create_template_dict, sort_lists
from dump.plugins.copp import Copp

module_tests_path = os.path.dirname(__file__)
dump_tests_path = os.path.join(module_tests_path, "../")
copp_files_path = os.path.join(dump_tests_path,"files","copp")
sys.path.append(dump_tests_path)
sys.path.append(module_tests_path)

from module_tests.mock_sonicv2connector import MockSonicV2Connector

dedicated_dbs = {}
dedicated_dbs['CONFIG_DB'] = os.path.join(copp_files_path, "config_db.json") 
dedicated_dbs['APPL_DB'] = os.path.join(copp_files_path, "appl_db.json") 
dedicated_dbs['ASIC_DB'] = os.path.join(copp_files_path, "asic_db.json")
dedicated_dbs['STATE_DB'] = os.path.join(copp_files_path, "state_db.json")

def mock_connector(host, namespace):
    return MockSonicV2Connector(dedicated_dbs, namespace)

@pytest.fixture(scope="module", autouse=True)
def verbosity_setup():
    print("SETUP")
    os.environ["VERBOSE"] = "1"
    yield
    print("TEARDOWN")
    os.environ["VERBOSE"] = "0"

@patch("dump.match_infra.SonicV2Connector", mock_connector)
@patch("dump.plugins.copp.Copp.CONFIG_FILE", os.path.join(dump_tests_path, "files/copp_cfg.json"))
class TestCoppModule(unittest.TestCase):
    
    def test_usr_cfg_trap_and_copp_cfg_file_grp(self):
        '''
        Scenario: A custom COPP_TRAP table entry is defined by the user and the relevant Trap Group is configured through the copp_cfg file 
        '''
        params = {}
        params[Copp.ARG_NAME] = "snmp"
        params["namespace"] = ""
        m_copp = Copp()
        returned = m_copp.execute(params)
        print(returned)
        expect = create_template_dict(dbs=["CONFIG_FILE", "CONFIG_DB", "APPL_DB", "ASIC_DB", "STATE_DB"])
        expect["CONFIG_FILE"]["keys"].append("COPP_GROUP|queue4_group2")
        expect["CONFIG_DB"]["keys"].append("COPP_TRAP|snmp_grp")
        expect["APPL_DB"]["keys"].append("COPP_TABLE:queue4_group2")
        expect["STATE_DB"]["keys"].extend(["COPP_GROUP_TABLE|queue4_group2", "COPP_TRAP_TABLE|snmp_grp"])
        expect["ASIC_DB"]["keys"].extend(["ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF_TRAP:oid:0x220000000004dc", "ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF_TRAP_GROUP:oid:0x110000000004da", 
                                          "ASIC_STATE:SAI_OBJECT_TYPE_POLICER:oid:0x120000000004db","ASIC_STATE:SAI_OBJECT_TYPE_QUEUE:oid:0x150000000002a0"])
        ddiff = DeepDiff(returned, expect, ignore_order=True)
        assert not ddiff, ddiff
    
    def test_copp_cfg_file_trap_and_copp_cfg_file_grp(self):
        '''
        Scenario: Both the Trap ID and Trap Group are configured through copp_cfg file
        '''
        params = {}
        params[Copp.ARG_NAME] = "arp_resp"
        params["namespace"] = ""
        m_copp = Copp()
        returned = m_copp.execute(params)
        print(returned)
        expect = create_template_dict(dbs=["CONFIG_FILE", "CONFIG_DB", "APPL_DB", "ASIC_DB", "STATE_DB"])
        expect["CONFIG_FILE"]["keys"].extend(["COPP_GROUP|queue4_group2", "COPP_TRAP|arp"])
        expect["APPL_DB"]["keys"].append("COPP_TABLE:queue4_group2")
        expect["STATE_DB"]["keys"].extend(["COPP_GROUP_TABLE|queue4_group2", "COPP_TRAP_TABLE|arp"])
        expect["ASIC_DB"]["keys"].extend(["ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF_TRAP:oid:0x220000000004dd", "ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF_TRAP_GROUP:oid:0x110000000004da", 
                                          "ASIC_STATE:SAI_OBJECT_TYPE_POLICER:oid:0x120000000004db","ASIC_STATE:SAI_OBJECT_TYPE_QUEUE:oid:0x150000000002a0"])
        ddiff = DeepDiff(returned, expect, ignore_order=True)
        assert not ddiff, ddiff
    
    def test_copp_cfg_file_trap_and_copp_cfg_file_grp_with_diff(self):
        '''
        Scenario: Both the Trap ID and Trap Group are configured through copp_cfg file. 
                  In addition, User also provided a diff for the COPP_GROUP entry
        '''
        params = {}
        params[Copp.ARG_NAME] = "sample_packet"
        params["namespace"] = ""
        m_copp = Copp()
        returned = m_copp.execute(params)
        print(returned)
        expect = create_template_dict(dbs=["CONFIG_FILE", "CONFIG_DB", "APPL_DB", "ASIC_DB", "STATE_DB"])
        expect["CONFIG_FILE"]["keys"].extend(["COPP_GROUP|queue2_group1", "COPP_TRAP|sflow"])
        expect["CONFIG_DB"]["keys"].append("COPP_GROUP|queue2_group1")
        expect["APPL_DB"]["keys"].append("COPP_TABLE:queue2_group1")
        expect["STATE_DB"]["keys"].extend(["COPP_GROUP_TABLE|queue2_group1", "COPP_TRAP_TABLE|sflow"])
        expect["ASIC_DB"]["keys"].extend(["ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF_TRAP:oid:0x220000000004de", "ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF_TRAP_GROUP:oid:0x110000000004db", 
                                          "ASIC_STATE:SAI_OBJECT_TYPE_POLICER:oid:0x120000000004dc","ASIC_STATE:SAI_OBJECT_TYPE_QUEUE:oid:0x150000000002a1"])
        ddiff = DeepDiff(returned, expect, ignore_order=True)
        assert not ddiff, ddiff
    
    def test_usr_cfg_trap_with_missing_group(self):
        '''
        Scenario: A custom COPP_TRAP table entry is defined by the user, but the relevant COPP_GROUP entry is missing
        '''
        params = {}
        params[Copp.ARG_NAME] = "vrrpv6"
        params["namespace"] = ""
        m_copp = Copp()
        returned = m_copp.execute(params)
        print(returned)
        expect = create_template_dict(dbs=["CONFIG_DB", "APPL_DB", "ASIC_DB", "STATE_DB", "CONFIG_FILE"])
        expect["CONFIG_DB"]["keys"].append("COPP_TRAP|vrrpv6")
        expect["CONFIG_DB"]["tables_not_found"].append("COPP_GROUP")
        expect["APPL_DB"]["tables_not_found"].append("COPP_TABLE")
        expect["STATE_DB"]["tables_not_found"].extend(["COPP_GROUP_TABLE", "COPP_TRAP_TABLE"])
        expect["ASIC_DB"]["tables_not_found"].extend(["ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF_TRAP", "ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF_TRAP_GROUP"])
        ddiff = DeepDiff(returned, expect, ignore_order=True)
        assert not ddiff, ddiff
    
    def test_copp_cfg_file_group_and_copp_cfg_file_trap_with_diff(self):
        '''
        Scenario: User has added a trap_id to a COPP_TRAP entry. The COPP_TRAP entry is already present in copp_cfg file (i.e diff) 
                  and the relevant trap group is in copp_cfg file
        '''
        params = {}
        params[Copp.ARG_NAME] = "ospfv6"
        params["namespace"] = ""
        m_copp = Copp()
        returned = m_copp.execute(params)
        print(returned)
        expect = create_template_dict(dbs=["CONFIG_FILE", "CONFIG_DB", "APPL_DB", "ASIC_DB", "STATE_DB"])
        expect["CONFIG_FILE"]["keys"].extend(["COPP_GROUP|queue4_group1", "COPP_TRAP|bgp"])
        expect["CONFIG_DB"]["keys"].append("COPP_TRAP|bgp")
        expect["APPL_DB"]["keys"].append("COPP_TABLE:queue4_group1")
        expect["STATE_DB"]["keys"].extend(["COPP_GROUP_TABLE|queue4_group1", "COPP_TRAP_TABLE|bgp"])
        expect["ASIC_DB"]["keys"].extend(["ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF_TRAP:oid:0x220000000004df", "ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF_TRAP_GROUP:oid:0x110000000004db", 
                                          "ASIC_STATE:SAI_OBJECT_TYPE_POLICER:oid:0x120000000004dc","ASIC_STATE:SAI_OBJECT_TYPE_QUEUE:oid:0x150000000002a1"])
        ddiff = DeepDiff(returned, expect, ignore_order=True)
        assert not ddiff, ddiff
    
    def test_invalid_trap_id(self):
        params = {}
        params[Copp.ARG_NAME] = "random"
        params["namespace"] = ""
        m_copp = Copp()
        returned = m_copp.execute(params)
        print(returned)
        expect = create_template_dict(dbs=["CONFIG_DB", "APPL_DB", "ASIC_DB", "STATE_DB", "CONFIG_FILE"])
        expect["CONFIG_FILE"]["tables_not_found"].extend(["COPP_GROUP", "COPP_TRAP"])
        expect["CONFIG_DB"]["tables_not_found"].extend(["COPP_GROUP", "COPP_TRAP"])
        expect["APPL_DB"]["tables_not_found"].append("COPP_TABLE")
        expect["STATE_DB"]["tables_not_found"].extend(["COPP_GROUP_TABLE", "COPP_TRAP_TABLE"])
        expect["ASIC_DB"]["tables_not_found"].extend(["ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF_TRAP", "ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF_TRAP_GROUP"])
        ddiff = DeepDiff(returned, expect, ignore_order=True)
        assert not ddiff, ddiff
    
    def test_missing_asic_dump(self):
        params = {}
        params[Copp.ARG_NAME] = "ospf"
        params["namespace"] = ""
        m_copp = Copp()
        returned = m_copp.execute(params)
        print(returned)
        expect = create_template_dict(dbs=["CONFIG_FILE", "CONFIG_DB", "APPL_DB", "ASIC_DB", "STATE_DB"])
        expect["CONFIG_FILE"]["keys"].extend(["COPP_GROUP|queue4_group1", "COPP_TRAP|bgp"])
        expect["CONFIG_DB"]["keys"].append("COPP_TRAP|bgp")
        expect["APPL_DB"]["keys"].append("COPP_TABLE:queue4_group1")
        expect["STATE_DB"]["keys"].extend(["COPP_GROUP_TABLE|queue4_group1", "COPP_TRAP_TABLE|bgp"])
        expect["ASIC_DB"]["tables_not_found"].extend(["ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF_TRAP", "ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF_TRAP_GROUP"])
        ddiff = DeepDiff(returned, expect, ignore_order=True)
        assert not ddiff, ddiff
    
    def test_missing_appl(self):
        params = {}
        params[Copp.ARG_NAME] = "lldp"
        params["namespace"] = ""
        m_copp = Copp()
        returned = m_copp.execute(params)
        print(returned)
        expect = create_template_dict(dbs=["CONFIG_FILE", "CONFIG_DB", "APPL_DB", "ASIC_DB", "STATE_DB"])
        expect["CONFIG_FILE"]["keys"].extend(["COPP_GROUP|queue4_group3", "COPP_TRAP|lldp"])
        expect["APPL_DB"]["tables_not_found"].append("COPP_TABLE")
        expect["STATE_DB"]["tables_not_found"].extend(["COPP_GROUP_TABLE", "COPP_TRAP_TABLE"])
        expect["ASIC_DB"]["tables_not_found"].extend(["ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF_TRAP", "ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF_TRAP_GROUP"])
        ddiff = DeepDiff(returned, expect, ignore_order=True)
        assert not ddiff, ddiff
    
    def test_missing_state(self):
        params = {}
        params[Copp.ARG_NAME] = "src_nat_miss"
        params["namespace"] = ""
        m_copp = Copp()
        returned = m_copp.execute(params)
        print(returned)
        expect = create_template_dict(dbs=["CONFIG_FILE", "APPL_DB", "ASIC_DB", "STATE_DB","CONFIG_DB"])
        expect["CONFIG_FILE"]["keys"].extend(["COPP_GROUP|queue1_group2", "COPP_TRAP|nat"])
        expect["APPL_DB"]["keys"].append("COPP_TABLE:queue1_group2")
        expect["STATE_DB"]["tables_not_found"].extend(["COPP_GROUP_TABLE", "COPP_TRAP_TABLE"])
        expect["ASIC_DB"]["keys"].extend(["ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF_TRAP:oid:0x220000000004e0", "ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF_TRAP_GROUP:oid:0x110000000004e0", 
                                          "ASIC_STATE:SAI_OBJECT_TYPE_QUEUE:oid:0x150000000002a1"])
        ddiff = DeepDiff(returned, expect, ignore_order=True)
        assert not ddiff, ddiff
        
    def test_all_args(self):
        params = {}
        m_copp = Copp()
        returned = m_copp.get_all_args("")
        expect = ["bgp", "bgpv6", "lacp", "arp_req", "arp_resp", "neigh_discovery", "lldp", "dhcp", "dhcpv6", "udld", "ip2me", "src_nat_miss", "dest_nat_miss", "sample_packet", "snmp", "bfd", "vrrpv6", "ospf", "ospfv6"]
        ddiff = DeepDiff(expect, returned, ignore_order=True)
        assert not ddiff, ddiff   
 
        