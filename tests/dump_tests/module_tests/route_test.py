import os, sys
import unittest
import pytest
from deepdiff import DeepDiff
from mock import patch
from dump.helper import create_template_dict
from dump.plugins.route import Route 

from .mock_sonicv2connector import MockSonicV2Connector

module_tests_path = os.path.dirname(__file__)
dump_tests_path = os.path.join(module_tests_path, "../")
tests_path = os.path.join(dump_tests_path, "../")
dump_test_input = os.path.join(tests_path, "dump_input")


# Location for dedicated db's used for UT
Route_files_path = os.path.join(dump_test_input, "route")

dedicated_dbs = {}
dedicated_dbs['CONFIG_DB'] = os.path.join(Route_files_path, "config_db.json") 
dedicated_dbs['APPL_DB'] = os.path.join(Route_files_path, "appl_db.json") 
dedicated_dbs['ASIC_DB'] = os.path.join(Route_files_path, "asic_db.json")

def mock_connector(namespace, use_unix_socket_path=True):
    return MockSonicV2Connector(dedicated_dbs, namespace=namespace, use_unix_socket_path=use_unix_socket_path)

@pytest.fixture(scope="module", autouse=True)
def verbosity_setup():
    print("SETUP")
    os.environ["VERBOSE"] = "1"
    yield
    print("TEARDOWN")
    os.environ["VERBOSE"] = "0"

def get_asic_route_key(dest):
    return "ASIC_STATE:SAI_OBJECT_TYPE_ROUTE_ENTRY:{\"dest\":\"" + dest + \
            "\",\"switch_id\":\"oid:0x21000000000000\",\"vr\":\"oid:0x3000000000002\"}"

@patch("dump.match_infra.SonicV2Connector", mock_connector)
class TestRouteModule(unittest.TestCase):
    def test_static_route(self):
        """
        Scenario: Fetch the Keys related to a Static Route from CONF, APPL & ASIC DB's
                  1) CONF & APPL are straightforward
                  2) SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID = SAI_OBJECT_TYPE_NEXT_HOP here
                  For More details about SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID, check the SAI header in sairoute.h
        """
        params = {Route.ARG_NAME : "20.0.0.0/24", "namespace" : ""}
        m_route = Route()
        returned = m_route.execute(params)
        expect = create_template_dict(dbs=["CONFIG_DB", "APPL_DB", "ASIC_DB"])
        expect["CONFIG_DB"]["keys"].append("STATIC_ROUTE|20.0.0.0/24")
        expect["APPL_DB"]["keys"].append("ROUTE_TABLE:20.0.0.0/24")
        expect["ASIC_DB"]["keys"].append(get_asic_route_key("20.0.0.0/24"))
        expect["ASIC_DB"]["keys"].append("ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP:oid:0x40000000002e7")
        expect["ASIC_DB"]["keys"].append("ASIC_STATE:SAI_OBJECT_TYPE_ROUTER_INTERFACE:oid:0x60000000002cd")
        expect["ASIC_DB"]["keys"].append("ASIC_STATE:SAI_OBJECT_TYPE_VIRTUAL_ROUTER:oid:0x3000000000002")
        ddiff = DeepDiff(returned, expect, ignore_order=True)
        print(expect, returned)
        assert not ddiff, ddiff
        
    def test_ip2me_route(self):
        """
        Scenario: Fetch the keys related to a ip2me route from APPL & ASIC DB.
                  1) CONF DB doesn't have a ip2me route entry unlike a static route.
                  2) APPL is straightforward
                  3) SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID = SAI_OBJECT_TYPE_PORT (CPU Port)
                  4) Thus, no SAI_OBJECT_TYPE_ROUTER_INTERFACE entry for this route
                  For More details about SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID, check the SAI header in sairoute.h 
        """
        params = {Route.ARG_NAME : "fe80::/64", "namespace" : ""}
        m_route = Route()
        returned = m_route.execute(params)
        expect = create_template_dict(dbs=["APPL_DB", "ASIC_DB"])
        expect["APPL_DB"]["keys"].append("ROUTE_TABLE:fe80::/64")
        expect["ASIC_DB"]["keys"].append(get_asic_route_key("fe80::/64"))
        expect["ASIC_DB"]["keys"].append("ASIC_STATE:SAI_OBJECT_TYPE_PORT:oid:0x1000000000001")
        expect["ASIC_DB"]["keys"].append("ASIC_STATE:SAI_OBJECT_TYPE_VIRTUAL_ROUTER:oid:0x3000000000002")
        ddiff = DeepDiff(returned, expect, ignore_order=True)
        assert not ddiff, ddiff
    
    def test_directly_connected_route(self):
        """
        Scenario: Fetch the keys related to a directly connected route from APPL & ASIC DB.
                  1) CONF DB doesn't have this route entry
                  2) APPL is straightforward
                  3) SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID = SAI_OBJECT_TYPE_ROUTER_INTERFACE
                  For More details about SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID, check the SAI header in sairoute.h 
        """
        params = {Route.ARG_NAME : "1.1.1.0/24", "namespace" : ""}
        m_route = Route()
        returned = m_route.execute(params)
        expect = create_template_dict(dbs=["APPL_DB", "ASIC_DB"])
        expect["APPL_DB"]["keys"].append("ROUTE_TABLE:1.1.1.0/24")
        expect["ASIC_DB"]["keys"].append(get_asic_route_key("1.1.1.0/24"))
        expect["ASIC_DB"]["keys"].append("ASIC_STATE:SAI_OBJECT_TYPE_ROUTER_INTERFACE:oid:0x60000000002cd")
        expect["ASIC_DB"]["keys"].append("ASIC_STATE:SAI_OBJECT_TYPE_VIRTUAL_ROUTER:oid:0x3000000000002")
        ddiff = DeepDiff(returned, expect, ignore_order=True)
        assert not ddiff, ddiff
    
    def test_route_with_next_hop(self):
        """
        Scenario: Fetch the keys related to a route with next hop.
                  1) CONF DB doesn't have this route entry
                  2) APPL is straightforward
                  3) SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID = SAI_OBJECT_TYPE_NEXT_HOP
                  For More details about SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID, check the SAI header in sairoute.h 
        """
        params = {Route.ARG_NAME : "10.212.0.0/16", "namespace" : ""}
        m_route = Route()
        returned = m_route.execute(params)
        expect = create_template_dict(dbs=["APPL_DB", "ASIC_DB"])
        expect["APPL_DB"]["keys"].append("ROUTE_TABLE:10.212.0.0/16")
        expect["ASIC_DB"]["keys"].append(get_asic_route_key("10.212.0.0/16"))
        expect["ASIC_DB"]["keys"].append("ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP:oid:0x40000000002e7")
        expect["ASIC_DB"]["keys"].append("ASIC_STATE:SAI_OBJECT_TYPE_ROUTER_INTERFACE:oid:0x60000000002cd")
        expect["ASIC_DB"]["keys"].append("ASIC_STATE:SAI_OBJECT_TYPE_VIRTUAL_ROUTER:oid:0x3000000000002")
        ddiff = DeepDiff(returned, expect, ignore_order=True)
        assert not ddiff, ddiff
    
    def test_route_with_next_hop_group(self):
        """
        Scenario: Fetch the keys related to a route with multiple next hops.
                  1) CONF DB doesn't have this route entry
                  2) APPL is straightforward
                  3) SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID = SAI_OBJECT_TYPE_NEXT_HOP_GROUP
                  For More details about SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID, check the SAI header in sairoute.h 
        """
        params = {Route.ARG_NAME : "20c0:e6e0:0:80::/64", "namespace" : ""}
        m_route = Route()
        returned = m_route.execute(params)
        expect = create_template_dict(dbs=["APPL_DB", "ASIC_DB"])
        expect["APPL_DB"]["keys"].append("ROUTE_TABLE:20c0:e6e0:0:80::/64")
        expect["ASIC_DB"]["keys"].append(get_asic_route_key("20c0:e6e0:0:80::/64"))
        
        exp_nh_group = "ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP:oid:0x5000000000689"
        exp_nh_group_mem = ["ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP_MEMBER:oid:0x2d00000000068a",
                            "ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP_MEMBER:oid:0x2d00000000068b",
                            "ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP_MEMBER:oid:0x2d00000000068c",
                            "ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP_MEMBER:oid:0x2d00000000068d"]
        exp_nh = ["ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP:oid:0x400000000066f", 
                  "ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP:oid:0x400000000067f",
                  "ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP:oid:0x4000000000665",
                  "ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP:oid:0x4000000000667"]
        exp_rif = ["ASIC_STATE:SAI_OBJECT_TYPE_ROUTER_INTERFACE:oid:0x60000000005c6",
                   "ASIC_STATE:SAI_OBJECT_TYPE_ROUTER_INTERFACE:oid:0x60000000005c7",
                   "ASIC_STATE:SAI_OBJECT_TYPE_ROUTER_INTERFACE:oid:0x60000000005c8",
                   "ASIC_STATE:SAI_OBJECT_TYPE_ROUTER_INTERFACE:oid:0x60000000005c9"]
        expect["ASIC_DB"]["keys"].append(exp_nh_group)
        expect["ASIC_DB"]["keys"].extend(exp_nh_group_mem)
        expect["ASIC_DB"]["keys"].extend(exp_nh)
        expect["ASIC_DB"]["keys"].extend(exp_rif)
        expect["ASIC_DB"]["keys"].append("ASIC_STATE:SAI_OBJECT_TYPE_VIRTUAL_ROUTER:oid:0x3000000000002")
        ddiff = DeepDiff(returned, expect, ignore_order=True)
        assert not ddiff, ddiff
    
    def test_all_args(self):
        """
        Scenario: Verify Whether the get_all_args method is working as expected
        """
        m_route = Route()
        returned = m_route.get_all_args("")
        expect = ["1.1.1.0/24", "10.1.0.32", "10.212.0.0/16", "20.0.0.0/24", "fe80::/64", "20c0:e6e0:0:80::/64"]
        ddiff = DeepDiff(expect, returned, ignore_order=True)
        assert not ddiff, ddiff 
