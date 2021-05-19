import os
import sys, json
import pytest
from unittest import mock, TestCase
from click.testing import CliRunner
from dump.main import state
from deepdiff import DeepDiff

def compare_json_output(exp, rec):
    try:
        rec_json = json.loads(rec)
    except Exception as e:
        assert 0 , "CLI Output is not in JSON Format"    
    exp_json = json.loads(exp)
    return DeepDiff(exp_json, rec_json)

table_display_output = '''\
+-------------+-----------+--------------------------------------------------------------------+
| port_name   | DB_NAME   | DUMP                                                               |
+=============+===========+====================================================================+
| Ethernet0   | APPL_DB   | +----------------------+-----------------------------------------+ |
|             |           | | Keys                 | field-value pairs                       | |
|             |           | +======================+=========================================+ |
|             |           | | PORT_TABLE:Ethernet0 | +--------------+----------------------+ | |
|             |           | |                      | | field        | value                | | |
|             |           | |                      | |--------------+----------------------| | |
|             |           | |                      | | index        | 0                    | | |
|             |           | |                      | | lanes        | 0                    | | |
|             |           | |                      | | alias        | Ethernet0            | | |
|             |           | |                      | | description  | ARISTA01T2:Ethernet1 | | |
|             |           | |                      | | speed        | 25000                | | |
|             |           | |                      | | oper_status  | down                 | | |
|             |           | |                      | | pfc_asym     | off                  | | |
|             |           | |                      | | mtu          | 9100                 | | |
|             |           | |                      | | fec          | rs                   | | |
|             |           | |                      | | admin_status | up                   | | |
|             |           | |                      | +--------------+----------------------+ | |
|             |           | +----------------------+-----------------------------------------+ |
+-------------+-----------+--------------------------------------------------------------------+
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
        
    def test_identifier_single(self):
        runner = CliRunner()
        result = runner.invoke(state, ["port", "Ethernet0"])
        expected = ('''{"Ethernet0":{"CONFIG_DB":{"keys":[{"PORT|Ethernet0":{"alias":"etp1","description":"etp1","index":"0","lanes":"25,26,27,28","mtu":"9100","pfc_asym":"off","speed":"40000"}}],''' + 
        '''"tables_not_found":[]},"APPL_DB":{"keys":[{"PORT_TABLE:Ethernet0":{"index":"0","lanes":"0","alias":"Ethernet0","description":"ARISTA01T2:Ethernet1","speed":"25000","oper_status":"down","pfc_asym":"off","mtu":"9100","fec":"rs","admin_status":"up"}}],''' +
        '''"tables_not_found":[]},"ASIC_DB":{"keys":[{"ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF:oid:0xd00000000056d":{"SAI_HOSTIF_ATTR_NAME":"Ethernet0","SAI_HOSTIF_ATTR_OBJ_ID":"oid:0x10000000004a4","SAI_HOSTIF_ATTR_OPER_STATUS":"true",'''+
        '''"SAI_HOSTIF_ATTR_TYPE":"SAI_HOSTIF_TYPE_NETDEV","SAI_HOSTIF_ATTR_VLAN_TAG":"SAI_HOSTIF_VLAN_TAG_STRIP"}},''' +
        '''{"ASIC_STATE:SAI_OBJECT_TYPE_PORT:oid:0x10000000004a4":{"NULL":"NULL","SAI_PORT_ATTR_ADMIN_STATE":"true","SAI_PORT_ATTR_MTU":"9122","SAI_PORT_ATTR_SPEED":"100000"}}],"tables_not_found":[],"vidtorid":{"oid:0xd00000000056d":"oid:0xd","oid:0x10000000004a4":"oid:0x1690000000001"}},''' +
        '''"STATE_DB":{"keys":[{"PORT_TABLE|Ethernet0":{"state":"ok"}}],"tables_not_found":[]}}}''')
        assert result.exit_code == 0, "exit code: {}, Exception: {}".format(result.exit_code, result.exception)
        ddiff = compare_json_output(expected, result.output)
        assert not ddiff, ddiff
        
    def test_identifier_multiple(self):
        runner = CliRunner()
        result = runner.invoke(state, ["port", "Ethernet0,Ethernet4"])
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
        assert result.exit_code == 0, "exit code: {}, Exception: {}".format(result.exit_code, result.exception)
        ddiff = compare_json_output(expected, result.output)
        assert not ddiff, ddiff
    
    def test_option_key_map(self):
        runner = CliRunner()
        result = runner.invoke(state, ["port", "Ethernet0", "--key-map"])
        expected = ('''{"Ethernet0":{"CONFIG_DB":{"keys":["PORT|Ethernet0"],"tables_not_found":[]},"APPL_DB":{"keys":["PORT_TABLE:Ethernet0"],"tables_not_found":[]},'''+
        '''"ASIC_DB":{"keys":["ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF:oid:0xd00000000056d","ASIC_STATE:SAI_OBJECT_TYPE_PORT:oid:0x10000000004a4"],'''+
        '''"tables_not_found":[],"vidtorid":{"oid:0xd00000000056d":"oid:0xd","oid:0x10000000004a4":"oid:0x1690000000001"}},'''+
        '''"STATE_DB":{"keys":["PORT_TABLE|Ethernet0"],"tables_not_found":[]}}}''')
        assert result.exit_code == 0, "exit code: {}, Exception: {}".format(result.exit_code, result.exception)
        ddiff = compare_json_output(expected, result.output)
        assert not ddiff, ddiff
        
    def test_option_db_filtering(self):
        runner = CliRunner()
        result = runner.invoke(state, ["port", "Ethernet0", "--db", "CONFIG_DB", "--db", "APPL_DB"])
        expected = ('''{"Ethernet0":{"CONFIG_DB":{"keys":[{"PORT|Ethernet0":{"alias":"etp1","description":"etp1","index":"0","lanes":"25,26,27,28","mtu":"9100",''' +
        '''"pfc_asym":"off","speed":"40000"}}],"tables_not_found":[]},"APPL_DB":{"keys":[{"PORT_TABLE:Ethernet0":{"index":"0","lanes":"0","alias":"Ethernet0","description":"ARISTA01T2:Ethernet1",''' +
        '''"speed":"25000","oper_status":"down","pfc_asym":"off","mtu":"9100","fec":"rs","admin_status":"up"}}],"tables_not_found":[]}}}''')
        assert result.exit_code == 0, "exit code: {}, Exception: {}".format(result.exit_code, result.exception)
        ddiff = compare_json_output(expected, result.output)
        assert not ddiff, ddiff
    
    def test_option_tabular_display(self):
        runner = CliRunner()
        result = runner.invoke(state, ["port", "Ethernet0", "--db", "APPL_DB", "--table"])
        assert result.exit_code == 0, "exit code: {}, Exception: {}".format(result.exit_code, result.exception)
        print(result.output)
        assert table_display_output == result.output
    
    def test_option_tabular_display_no_db_filter(self):
        runner = CliRunner()
        result = runner.invoke(state, ["port", "Ethernet0", "--table", "--key-map"])
        assert result.exit_code == 0, "exit code: {}, Exception: {}".format(result.exit_code, result.exception)
        assert table_display_output_no_filtering == result.output
    
    def test_identifier_all_with_filtering(self):
        runner = CliRunner()
        expected_entries = []
        for i in range(0, 125, 4):
            expected_entries.append("Ethernet" + str(i))
        result = runner.invoke(state, ["port", "all", "--db", "CONFIG_DB", "--key-map"])
        try:
            rec_json = json.loads(result.output)
        except Exception as e:
            assert 0 , "CLI Output is not in JSON Format" 
        ddiff = DeepDiff(set(expected_entries), set(rec_json.keys()))
        assert not ddiff, "Expected Entries were not recieved when passing all keyword"