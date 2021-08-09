import json, os, sys
import jsonpatch
import unittest
import pytest
from deepdiff import DeepDiff
from mock import patch
from dump.helper import create_template_dict, sort_lists
from dump.plugins.portchannel import PortChannel

from .mock_sonicv2connector import MockSonicV2Connector

module_tests_path = os.path.dirname(__file__)
dump_tests_path = os.path.join(module_tests_path, "../")
tests_path = os.path.join(dump_tests_path, "../")
dump_test_input = os.path.join(tests_path, "dump_input")


# Location for dedicated db's used for UT
port_files_path = os.path.join(dump_test_input, "portchannel")

dedicated_dbs = {}
dedicated_dbs['CONFIG_DB'] = os.path.join(port_files_path, "config_db.json") 
dedicated_dbs['APPL_DB'] = os.path.join(port_files_path, "appl_db.json") 
dedicated_dbs['ASIC_DB'] = os.path.join(port_files_path, "asic_db.json")
dedicated_dbs['STATE_DB'] = os.path.join(port_files_path, "state_db.json")

def mock_connector(namespace, use_unix_socket_path=True):
    return MockSonicV2Connector(dedicated_dbs, namespace=namespace, use_unix_socket_path=use_unix_socket_path)

@pytest.fixture(scope="module", autouse=True)
def verbosity_setup():
    print("SETUP")
    os.environ["VERBOSE"] = "1"
    yield
    print("TEARDOWN")
    os.environ["VERBOSE"] = "0"

@patch("dump.match_infra.SonicV2Connector", mock_connector)
class TestPortChannelModule(unittest.TestCase):
    def test_get_all_args(self):
        """
        Scenario: Verify Whether the get_all_args method is working as expected
        """
        m_lag = PortChannel()
        returned = m_lag.get_all_args("")
        expect = ["PortChannel001", "PortChannel002", "PortChannel003"]
        ddiff = DeepDiff(expect, returned, ignore_order=True)
        assert not ddiff, ddiff 
    
    def test_missing_appl_state(self):
        '''
        Scenario: When the LAG is configured but the Change is not propagated
        '''
        params = {PortChannel.ARG_NAME:"PortChannel003", "namespace":""}
        m_lag = PortChannel()
        returned = m_lag.execute(params)
        expect = create_template_dict(dbs=["CONFIG_DB", "APPL_DB", "ASIC_DB", "STATE_DB"])
        expect["CONFIG_DB"]["keys"].append("PORTCHANNEL|PortChannel003")
        expect["CONFIG_DB"]["tables_not_found"].append("PORTCHANNEL_MEMBER")
        expect["APPL_DB"]["tables_not_found"].append("LAG_TABLE")
        expect["APPL_DB"]["tables_not_found"].append("LAG_MEMBER_TABLE")
        expect["STATE_DB"]["tables_not_found"].append("LAG_TABLE")
        expect["STATE_DB"]["tables_not_found"].append("LAG_MEMBER_TABLE")
        expect["ASIC_DB"]["tables_not_found"].append("ASIC_STATE:SAI_OBJECT_TYPE_LAG")
        expect["ASIC_DB"]["tables_not_found"].append("ASIC_STATE:SAI_OBJECT_TYPE_LAG_MEMBER")
        ddiff = DeepDiff(returned, expect, ignore_order=True)
        assert not ddiff, ddiff
    
    def test_lag_with_no_members(self):
        '''
        Scenario: When the PortChannel doesn't have any members, 
                  it is not possible to uniquely identify ASIC LAG Related Key
        '''
        params = {PortChannel.ARG_NAME:"PortChannel002", "namespace":""}
        m_lag = PortChannel()
        returned = m_lag.execute(params)
        expect = create_template_dict(dbs=["CONFIG_DB", "APPL_DB", "ASIC_DB", "STATE_DB"])
        expect["CONFIG_DB"]["keys"].append("PORTCHANNEL|PortChannel002")
        expect["CONFIG_DB"]["tables_not_found"].append("PORTCHANNEL_MEMBER")
        expect["APPL_DB"]["keys"].append("LAG_TABLE:PortChannel002")
        expect["APPL_DB"]["tables_not_found"].append("LAG_MEMBER_TABLE")
        expect["STATE_DB"]["keys"].append("LAG_TABLE|PortChannel002")
        expect["STATE_DB"]["tables_not_found"].append("LAG_MEMBER_TABLE")
        expect["ASIC_DB"]["tables_not_found"].append("ASIC_STATE:SAI_OBJECT_TYPE_LAG")
        expect["ASIC_DB"]["tables_not_found"].append("ASIC_STATE:SAI_OBJECT_TYPE_LAG_MEMBER")
        ddiff = DeepDiff(returned, expect, ignore_order=True)
        assert not ddiff, ddiff

    def test_lag_with_members(self):
        '''
        Scenario: It should be possible to uniquely identify ASIC LAG Related Keys,
                  when the LAG has members
        '''
        params = {PortChannel.ARG_NAME:"PortChannel001", "namespace":""}
        m_lag = PortChannel()
        returned = m_lag.execute(params)
        expect = create_template_dict(dbs=["CONFIG_DB", "APPL_DB", "ASIC_DB", "STATE_DB"])
        expect["CONFIG_DB"]["keys"].append("PORTCHANNEL|PortChannel001")
        expect["CONFIG_DB"]["keys"].append("PORTCHANNEL_MEMBER|PortChannel001|Ethernet0")
        expect["CONFIG_DB"]["keys"].append("PORTCHANNEL_MEMBER|PortChannel001|Ethernet4")
        expect["APPL_DB"]["keys"].append("LAG_TABLE:PortChannel001")
        expect["APPL_DB"]["keys"].append("LAG_MEMBER_TABLE:PortChannel001:Ethernet4")
        expect["APPL_DB"]["keys"].append("LAG_MEMBER_TABLE:PortChannel001:Ethernet0")
        expect["STATE_DB"]["keys"].append("LAG_TABLE|PortChannel001")
        expect["STATE_DB"]["keys"].append("LAG_MEMBER_TABLE|PortChannel001|Ethernet0")
        expect["STATE_DB"]["keys"].append("LAG_MEMBER_TABLE|PortChannel001|Ethernet4")
        expect["ASIC_DB"]["keys"].append("ASIC_STATE:SAI_OBJECT_TYPE_LAG:oid:0x2000000000d17")
        expect["ASIC_DB"]["keys"].append("ASIC_STATE:SAI_OBJECT_TYPE_LAG_MEMBER:oid:0x1b000000000d18")
        expect["ASIC_DB"]["keys"].append("ASIC_STATE:SAI_OBJECT_TYPE_LAG_MEMBER:oid:0x1b000000000d1a")
        ddiff = DeepDiff(returned, expect, ignore_order=True)
        assert not ddiff, ddiff
