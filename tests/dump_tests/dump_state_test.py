import os
import sys, json
import pytest
from unittest import mock, TestCase
from click.testing import CliRunner
import dump.main as dump
from deepdiff import DeepDiff
from importlib import reload
from utilities_common.db import Db
import traceback
from .module_tests import mock_sonicv2connector
from utilities_common.constants import DEFAULT_NAMESPACE

def compare_json_output(exp, rec, exclude_paths=None):
    try:
        rec_json = json.loads(rec)
    except Exception as e:
        assert 0 , "CLI Output is not in JSON Format"    
    exp_json = json.loads(exp)
    return DeepDiff(exp_json, rec_json, exclude_paths=exclude_paths)

table_display_output = '''\
+-------------+-----------+--------------------------------------------------+
| port_name   | DB_NAME   | DUMP                                             |
+=============+===========+==================================================+
| Ethernet0   | STATE_DB  | +----------------------+-----------------------+ |
|             |           | | Keys                 | field-value pairs     | |
|             |           | +======================+=======================+ |
|             |           | | PORT_TABLE|Ethernet0 | +---------+---------+ | |
|             |           | |                      | | field   | value   | | |
|             |           | |                      | |---------+---------| | |
|             |           | |                      | | state   | ok      | | |
|             |           | |                      | +---------+---------+ | |
|             |           | +----------------------+-----------------------+ |
+-------------+-----------+--------------------------------------------------+
'''

table_display_output_no_filtering= '''\
+-------------+-----------+-----------------------------------------------------------+
| port_name   | DB_NAME   | DUMP                                                      |
+=============+===========+===========================================================+
| Ethernet0   | CONFIG_DB | +------------------+                                      |
|             |           | | Keys Collected   |                                      |
|             |           | +==================+                                      |
|             |           | | PORT|Ethernet0   |                                      |
|             |           | +------------------+                                      |
+-------------+-----------+-----------------------------------------------------------+
| Ethernet0   | APPL_DB   | +----------------------+                                  |
|             |           | | Keys Collected       |                                  |
|             |           | +======================+                                  |
|             |           | | PORT_TABLE:Ethernet0 |                                  |
|             |           | +----------------------+                                  |
+-------------+-----------+-----------------------------------------------------------+
| Ethernet0   | ASIC_DB   | +-------------------------------------------------------+ |
|             |           | | Keys Collected                                        | |
|             |           | +=======================================================+ |
|             |           | | ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF:oid:0xd00000000056d | |
|             |           | +-------------------------------------------------------+ |
|             |           | | ASIC_STATE:SAI_OBJECT_TYPE_PORT:oid:0x10000000004a4   | |
|             |           | +-------------------------------------------------------+ |
|             |           | +---------------------+---------------------+             |
|             |           | | vid                 | rid                 |             |
|             |           | +=====================+=====================+             |
|             |           | | oid:0xd00000000056d | oid:0xd             |             |
|             |           | +---------------------+---------------------+             |
|             |           | | oid:0x10000000004a4 | oid:0x1690000000001 |             |
|             |           | +---------------------+---------------------+             |
+-------------+-----------+-----------------------------------------------------------+
| Ethernet0   | STATE_DB  | +----------------------+                                  |
|             |           | | Keys Collected       |                                  |
|             |           | +======================+                                  |
|             |           | | PORT_TABLE|Ethernet0 |                                  |
|             |           | +----------------------+                                  |
+-------------+-----------+-----------------------------------------------------------+
'''

class TestDumpState(object):
    
    @classmethod
    def setup_class(cls):
        print("SETUP")
        os.environ["UTILITIES_UNIT_TESTING"] = "1"
        mock_db_path = os.path.join(os.path.dirname(__file__), "../mock_tables/")

    
    def test_identifier_single(self):
        runner = CliRunner()
        result = runner.invoke(dump.state, ["port", "Ethernet0"])
        expected = ('''{"Ethernet0":{"CONFIG_DB":{"keys":[{"PORT|Ethernet0":{"alias":"etp1","description":"etp1","index":"0","lanes":"25,26,27,28","mtu":"9100","pfc_asym":"off","speed":"40000"}}],''' + 
        '''"tables_not_found":[]},"APPL_DB":{"keys":[{"PORT_TABLE:Ethernet0":{"index":"0","lanes":"0","alias":"Ethernet0","description":"ARISTA01T2:Ethernet1","speed":"25000","oper_status":"down","pfc_asym":"off","mtu":"9100","fec":"rs","admin_status":"up"}}],''' +
        '''"tables_not_found":[]},"ASIC_DB":{"keys":[{"ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF:oid:0xd00000000056d":{"SAI_HOSTIF_ATTR_NAME":"Ethernet0","SAI_HOSTIF_ATTR_OBJ_ID":"oid:0x10000000004a4","SAI_HOSTIF_ATTR_OPER_STATUS":"true",'''+
        '''"SAI_HOSTIF_ATTR_TYPE":"SAI_HOSTIF_TYPE_NETDEV","SAI_HOSTIF_ATTR_VLAN_TAG":"SAI_HOSTIF_VLAN_TAG_STRIP"}},''' +
        '''{"ASIC_STATE:SAI_OBJECT_TYPE_PORT:oid:0x10000000004a4":{"NULL":"NULL","SAI_PORT_ATTR_ADMIN_STATE":"true","SAI_PORT_ATTR_MTU":"9122","SAI_PORT_ATTR_SPEED":"100000"}}],"tables_not_found":[],"vidtorid":{"oid:0xd00000000056d":"oid:0xd","oid:0x10000000004a4":"oid:0x1690000000001"}},''' +
        '''"STATE_DB":{"keys":[{"PORT_TABLE|Ethernet0":{"state":"ok"}}],"tables_not_found":[]}}}''')
        assert result.exit_code == 0, "exit code: {}, Exception: {}, Traceback: {}".format(result.exit_code, result.exception, result.exc_info)
        # Cause other tests depend and change these paths in the mock_db, this test would fail everytime when a field or a value in changed in this path, creating noise
        # and therefore Hense ignoring these paths. field-value dump capability of the utility is nevertheless verified using f-v dumps of ASIC_DB & STATE_DB
        pths = ["root['Ethernet0']['CONFIG_DB']['keys'][0]['PORT|Ethernet0']", "root['Ethernet0']['APPL_DB']['keys'][0]['PORT_TABLE:Ethernet0']"]
        ddiff = compare_json_output(expected, result.output, exclude_paths = pths)
        assert not ddiff, ddiff
        
    def test_identifier_multiple(self):
        runner = CliRunner()
        result = runner.invoke(dump.state, ["port", "Ethernet0,Ethernet4"])
        print(result.output)
        expected = ('''{"Ethernet0":{"CONFIG_DB":{"keys":[{"PORT|Ethernet0":{"alias":"etp1","description":"etp1","index":"0","lanes":"25,26,27,28",''' +
        '''"mtu":"9100","pfc_asym":"off","speed":"40000"}}],"tables_not_found":[]},"APPL_DB":{"keys":[{"PORT_TABLE:Ethernet0":{"index":"0",''' +
        '''"lanes":"0","alias":"Ethernet0","description":"ARISTA01T2:Ethernet1","speed":"25000","oper_status":"down","pfc_asym":"off","mtu":"9100",''' +
        '''"fec":"rs","admin_status":"up"}}],"tables_not_found":[]},"ASIC_DB":{"keys":[{"ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF:oid:0xd00000000056d":''' +
        '''{"SAI_HOSTIF_ATTR_NAME":"Ethernet0","SAI_HOSTIF_ATTR_OBJ_ID":"oid:0x10000000004a4","SAI_HOSTIF_ATTR_OPER_STATUS":"true","SAI_HOSTIF_ATTR_TYPE":''' +
        '''"SAI_HOSTIF_TYPE_NETDEV","SAI_HOSTIF_ATTR_VLAN_TAG":"SAI_HOSTIF_VLAN_TAG_STRIP"}},{"ASIC_STATE:SAI_OBJECT_TYPE_PORT:oid:0x10000000004a4":{"NULL":''' +
        '''"NULL","SAI_PORT_ATTR_ADMIN_STATE":"true","SAI_PORT_ATTR_MTU":"9122","SAI_PORT_ATTR_SPEED":"100000"}}],"tables_not_found":[],"vidtorid":''' +
        '''{"oid:0xd00000000056d":"oid:0xd","oid:0x10000000004a4":"oid:0x1690000000001"}},"STATE_DB":{"keys":[{"PORT_TABLE|Ethernet0":{"state":"ok"}}],"tables_not_found":[]}},''' +
        '''"Ethernet4":{"CONFIG_DB":{"keys":[{"PORT|Ethernet4":{"admin_status":"up","alias":"etp2","description":"Servers0:eth0","index":"1","lanes":"29,30,31,32","mtu":"9100","pfc_asym":"off","speed":"40000"}}],''' +
        '''"tables_not_found":[]},"APPL_DB":{"keys":[],"tables_not_found":["PORT_TABLE"]},"ASIC_DB":{"keys":[],"tables_not_found"''' +
        ''':["ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF","ASIC_STATE:SAI_OBJECT_TYPE_PORT"]},"STATE_DB":{"keys":[],"tables_not_found":["PORT_TABLE"]}}}''')
        assert result.exit_code == 0, "exit code: {}, Exception: {}, Traceback: {}".format(result.exit_code, result.exception, result.exc_info)
        pths = ["root['Ethernet0']['CONFIG_DB']['keys'][0]['PORT|Ethernet0']", "root['Ethernet0']['APPL_DB']['keys'][0]['PORT_TABLE:Ethernet0']"]
        pths += ["root['Ethernet4']['CONFIG_DB']['keys'][0]['PORT|Ethernet4]", "root['Ethernet4']['APPL_DB']['keys'][0]['PORT_TABLE:Ethernet4']"]
        ddiff = compare_json_output(expected, result.output, pths)
        assert not ddiff, ddiff
    
    def test_option_key_map(self):
        runner = CliRunner()
        result = runner.invoke(dump.state, ["port", "Ethernet0", "--key-map"])
        expected = ('''{"Ethernet0":{"CONFIG_DB":{"keys":["PORT|Ethernet0"],"tables_not_found":[]},"APPL_DB":{"keys":["PORT_TABLE:Ethernet0"],"tables_not_found":[]},'''+
        '''"ASIC_DB":{"keys":["ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF:oid:0xd00000000056d","ASIC_STATE:SAI_OBJECT_TYPE_PORT:oid:0x10000000004a4"],'''+
        '''"tables_not_found":[],"vidtorid":{"oid:0xd00000000056d":"oid:0xd","oid:0x10000000004a4":"oid:0x1690000000001"}},'''+
        '''"STATE_DB":{"keys":["PORT_TABLE|Ethernet0"],"tables_not_found":[]}}}''')
        assert result.exit_code == 0, "exit code: {}, Exception: {}, Traceback: {}".format(result.exit_code, result.exception, result.exc_info)
        ddiff = compare_json_output(expected, result.output)
        assert not ddiff, ddiff
        
    def test_option_db_filtering(self):
        runner = CliRunner()
        result = runner.invoke(dump.state, ["port", "Ethernet0", "--db", "ASIC_DB", "--db", "STATE_DB"])
        expected = ('''{"Ethernet0":{"ASIC_DB":{"keys":[{"ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF:oid:0xd00000000056d":{"SAI_HOSTIF_ATTR_NAME":"Ethernet0","SAI_HOSTIF_ATTR_OBJ_ID":"oid:0x10000000004a4",'''+
        '''"SAI_HOSTIF_ATTR_OPER_STATUS":"true","SAI_HOSTIF_ATTR_TYPE":"SAI_HOSTIF_TYPE_NETDEV","SAI_HOSTIF_ATTR_VLAN_TAG":"SAI_HOSTIF_VLAN_TAG_STRIP"}},'''+
        '''{"ASIC_STATE:SAI_OBJECT_TYPE_PORT:oid:0x10000000004a4":{"NULL":"NULL","SAI_PORT_ATTR_ADMIN_STATE":"true","SAI_PORT_ATTR_MTU":"9122","SAI_PORT_ATTR_SPEED":"100000"}}],"tables_not_found":[],'''+
        '''"vidtorid":{"oid:0xd00000000056d":"oid:0xd","oid:0x10000000004a4":"oid:0x1690000000001"}},"STATE_DB":{"keys":[{"PORT_TABLE|Ethernet0":{"state":"ok"}}],"tables_not_found":[]}}}''')
        assert result.exit_code == 0, "exit code: {}, Exception: {}, Traceback: {}".format(result.exit_code, result.exception, result.exc_info)
        ddiff = compare_json_output(expected, result.output)
        assert not ddiff, ddiff
    
    def test_option_tabular_display(self):
        runner = CliRunner()
        result = runner.invoke(dump.state, ["port", "Ethernet0", "--db", "STATE_DB", "--table"])
        print(result.output)
        assert result.exit_code == 0, "exit code: {}, Exception: {}, Traceback: {}".format(result.exit_code, result.exception, result.exc_info)
        print(result.output)
        assert table_display_output == result.output
    
    def test_option_tabular_display_no_db_filter(self):
        runner = CliRunner()
        result = runner.invoke(dump.state, ["port", "Ethernet0", "--table", "--key-map"])
        assert result.exit_code == 0, "exit code: {}, Exception: {}, Traceback: {}".format(result.exit_code, result.exception, result.exc_info)
        assert table_display_output_no_filtering == result.output
    
    def test_identifier_all_with_filtering(self):
        runner = CliRunner()
        expected_entries = []
        for i in range(0, 125, 4):
            expected_entries.append("Ethernet" + str(i))
        result = runner.invoke(dump.state, ["port", "all", "--db", "CONFIG_DB", "--key-map"])
        try:
            rec_json = json.loads(result.output)
        except Exception as e:
            assert 0 , "CLI Output is not in JSON Format" 
        ddiff = DeepDiff(set(expected_entries), set(rec_json.keys()))
        assert not ddiff, "Expected Entries were not recieved when passing all keyword"
    
    def test_namespace_single_asic(self):
        runner = CliRunner()
        result = runner.invoke(dump.state, ["port", "Ethernet0", "--table", "--key-map", "--namespace", "asic0"])
        assert result.output == "Namespace option is not valid for a single-ASIC device\n"
    
    @classmethod
    def teardown(cls):
        print("TEARDOWN")
        os.environ["UTILITIES_UNIT_TESTING"] = "0"
    
class TestDumpStateMultiAsic(object):
    
    @classmethod
    def setup_class(cls):
        print("SETUP")
        os.environ["UTILITIES_UNIT_TESTING"] = "2"
        os.environ["UTILITIES_UNIT_TESTING_TOPOLOGY"] = "multi_asic"
        from ..mock_tables import mock_multi_asic
        reload(mock_multi_asic)
        from ..mock_tables import dbconnector
        dbconnector.load_namespace_config()
        
    def test_default_namespace(self):
        runner = CliRunner()
        db = Db()
        result = runner.invoke(dump.state, ["port", "Ethernet0", "--key-map"], obj=db)
        expected = ('''{"Ethernet0":{"CONFIG_DB":{"keys":["PORT|Ethernet0"],"tables_not_found":[]},"APPL_DB":{"keys":["PORT_TABLE:Ethernet0"],"tables_not_found":[]},'''+
        '''"ASIC_DB":{"keys":["ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF:oid:0xd00000000056d","ASIC_STATE:SAI_OBJECT_TYPE_PORT:oid:0x10000000004a4"],'''+
        '''"tables_not_found":[],"vidtorid":{"oid:0xd00000000056d":"oid:0xd","oid:0x10000000004a4":"oid:0x1690000000001"}},'''+
        '''"STATE_DB":{"keys":["PORT_TABLE|Ethernet0"],"tables_not_found":[]}}}''')
        assert result.exit_code == 0, "exit code: {}, Exception: {}, Output: {}".format(result.exit_code, result.exception, result.output)
        ddiff = compare_json_output(expected, result.output)
        assert not ddiff, ddiff
    
    def test_namespace_asic0(self):
        runner = CliRunner()
        db = Db()
        result = runner.invoke(dump.state, ["port", "Ethernet0", "--namespace", "asic0"], obj=db)
        expected = ('''{"Ethernet0":{"CONFIG_DB":{"keys":[{"PORT|Ethernet0":{"admin_status":"up","alias":"Ethernet1/1","asic_port_name":'''+
        '''"Eth0-ASIC0","description":"ARISTA01T2:Ethernet3/1/1","lanes":"33,34,35,36","mtu":"9100","pfc_asym":"off","role":"Ext","speed":"40000"}}],'''+
        '''"tables_not_found":[]},"APPL_DB":{"keys":[{"PORT_TABLE:Ethernet0":{"lanes":"33,34,35,36","description":"ARISTA01T2:Ethernet3/1/1","pfc_asym":"off",'''+
        '''"mtu":"9100","alias":"Ethernet1/1","oper_status":"up","admin_status":"up","role":"Ext","speed":"40000","asic_port_name":"Eth0-ASIC0"}}],"tables_not_found":[]},"ASIC_DB":'''+
        '''{"keys":[],"tables_not_found":["ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF","ASIC_STATE:SAI_OBJECT_TYPE_PORT"]},"STATE_DB":{"keys":[],"tables_not_found":["PORT_TABLE"]}}}''')
        assert result.exit_code == 0, "exit code: {}, Exception: {}, Output: {}".format(result.exit_code, result.exception, result.output)
        ddiff = compare_json_output(expected, result.output)
        assert not ddiff, ddiff

    
    def test_namespace_asic1(self):
        runner = CliRunner()
        db = Db()
        result = runner.invoke(dump.state, ["port", "Ethernet-BP256", "--namespace", "asic1"], obj=db)
        expected = ('''{"Ethernet-BP256":{"CONFIG_DB":{"keys":[{"PORT|Ethernet-BP256":{"admin_status":"up","alias":"Ethernet-BP256","asic_port_name":"Eth0-ASIC1","description":"ASIC0:Eth16-ASIC0",'''+
        '''"lanes":"61,62,63,64","mtu":"9100","pfc_asym":"off","role":"Int","speed":"40000"}}],"tables_not_found":[]},"APPL_DB":{"keys":[{"PORT_TABLE:Ethernet-BP256":{"oper_status":"up",'''+
        '''"lanes":"61,62,63,64","description":"ASIC0:Eth16-ASIC0","pfc_asym":"off","mtu":"9100","alias":"Ethernet-BP256","admin_status":"up","speed":"40000","asic_port_name":"Eth0-ASIC1"}}],'''+
        '''"tables_not_found":[]},"ASIC_DB":{"keys":[],"tables_not_found":["ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF","ASIC_STATE:SAI_OBJECT_TYPE_PORT"]},"STATE_DB":{"keys":[],"tables_not_found":["PORT_TABLE"]}}}''')
        assert result.exit_code == 0, "exit code: {}, Exception: {}, Output: {}".format(result.exit_code, result.exception, result.output)
        ddiff = compare_json_output(expected, result.output)
        assert not ddiff, ddiff
    
    def test_invalid_namespace(self):
        runner = CliRunner()
        db = Db()
        result = runner.invoke(dump.state, ["port", "Ethernet0", "--namespace", "asic3"], obj=db)
        assert result.output == "Namespace option is not valid. Choose one of ['asic0', 'asic1']\n"
    

    def teardown_class(cls):
        print("TEARDOWN")
        os.environ["UTILITIES_UNIT_TESTING"] = "0"
        os.environ["UTILITIES_UNIT_TESTING_TOPOLOGY"] = "" 
