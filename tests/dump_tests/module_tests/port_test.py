import json, os, sys
import jsonpatch
import unittest
import pytest
from deepdiff import DeepDiff
from mock import patch
from dump.helper import display_template
from dump.plugins.port import Port

module_tests_path = os.path.dirname(__file__)
dump_tests_path = os.path.join(module_tests_path, "../")
port_files_path = os.path.join(dump_tests_path,"files","port")
sys.path.append(dump_tests_path)
sys.path.append(module_tests_path)

from module_tests.mock_sonicv2connector import MockSonicV2Connector

dedicated_dbs = {}
dedicated_dbs['CONFIG_DB'] = os.path.join(port_files_path, "config_db.json") 
dedicated_dbs['APPL_DB'] = os.path.join(port_files_path, "appl_db.json") 
dedicated_dbs['ASIC_DB'] = os.path.join(port_files_path, "asic_db.json")
dedicated_dbs['STATE_DB'] = os.path.join(port_files_path, "state_db.json")

def mock_connector(host):
    return MockSonicV2Connector(dedicated_dbs)

@pytest.fixture(scope="module", autouse=True)
def verbosity_setup():
    print("SETUP")
    os.environ["VERBOSE"] = "1"
    yield
    print("TEARDOWN")
    os.environ["VERBOSE"] = "0"

def sort_lists(ret):
    for db in ret.keys():
        for key in ret[db].keys():
            if isinstance(ret[db][key], list):
                ret[db][key].sort()
    return ret


@patch("dump.redis_match.SonicV2Connector", mock_connector)
class TestPortModule(unittest.TestCase):
    
    def test_proper_config_state(self):
        params = {}
        params[Port.ARG_NAME] = "Ethernet176"
        m_port = Port()
        returned = m_port.execute(params)
        print(returned)
        expect = display_template(dbs=["CONFIG_DB", "APPL_DB", "ASIC_DB", "STATE_DB"])
        expect["CONFIG_DB"]["keys"].append("PORT|Ethernet176")
        expect["APPL_DB"]["keys"].append("PORT_TABLE:Ethernet176")
        expect["STATE_DB"]["keys"].append("PORT_TABLE|Ethernet176")
        expect["ASIC_DB"]["keys"].append("ASIC_STATE:SAI_OBJECT_TYPE_PORT:oid:0x100000000036a")
        expect["ASIC_DB"]["keys"].append("ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF:oid:0xd000000000a4d")
        ddiff = DeepDiff(sort_lists(expect), sort_lists(returned))
        assert not ddiff, ddiff
        
    def test_missing_asic(self):
        params = {}
        params[Port.ARG_NAME] = "Ethernet176"
        m_port = Port()
        returned = m_port.execute(params)
        print(returned)
        expect = display_template(dbs=["CONFIG_DB", "APPL_DB", "ASIC_DB", "STATE_DB"])
        expect["CONFIG_DB"]["keys"].append("PORT|Ethernet176")
        expect["APPL_DB"]["keys"].append("PORT_TABLE:Ethernet176")
        expect["STATE_DB"]["keys"].append("PORT_TABLE|Ethernet176")
        expect["ASIC_DB"]["keys"].append("ASIC_STATE:SAI_OBJECT_TYPE_PORT:oid:0x100000000036a")
        expect["ASIC_DB"]["keys"].append("ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF:oid:0xd000000000a4d")
        ddiff = DeepDiff(sort_lists(expect), sort_lists(returned))
        assert not ddiff, ddiff
        
        