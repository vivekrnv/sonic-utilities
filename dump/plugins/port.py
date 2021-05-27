import os, sys
from .executor import Executor
from dump.match_infra import MatchEngine, MatchRequest
from dump.helper import display_template

class Port(Executor):
    
    ARG_NAME = "port_name"
    
    def __init__(self):
        self.match_engine = MatchEngine()
          
    def get_all_args(self, ns):
        req = MatchRequest()
        req.db = "CONFIG_DB"
        req.table = "PORT"
        req.key_pattern = "*"
        req.ns = ns
        ret = self.match_engine.fetch(req)
        all_ports = []
        for key in ret["keys"]:
            all_ports.append(key.split("|")[-1])
        return all_ports
            
    
    def execute(self, params_dict):
        ret_temp = display_template(dbs=["CONFIG_DB", "APPL_DB", "ASIC_DB", "STATE_DB"])
        port_name = params_dict[Port.ARG_NAME]
        ns = params_dict["namespace"]
        ret_temp = self.get_config_info(port_name, ret_temp, ns)
        ret_temp = self.get_appl_info(port_name, ret_temp, ns)
        ret_temp, port_asic_obj = self.get_asic_info_hostif(port_name, ret_temp, ns)
        ret_temp = self.get_asic_info_port(port_asic_obj, ret_temp, ns)
        ret_temp = self.get_state_info(port_name, ret_temp, ns)
        return ret_temp
    
    def get_config_info(self, port_name, ret_temp, ns):
        req = MatchRequest()
        req.db = "CONFIG_DB"
        req.table = "PORT"
        req.key_pattern = port_name
        req.ns = ns
        ret = self.match_engine.fetch(req)
        if not ret["error"] and len(ret["keys"]) != 0:
            ret_temp[req.db]["keys"] = ret["keys"]
        else:
            ret_temp[req.db]["tables_not_found"] = [req.table]
        return ret_temp
    
    def get_appl_info(self, port_name, ret_temp, ns):
        req = MatchRequest()
        req.db = "APPL_DB"
        req.table = "PORT_TABLE"
        req.key_pattern = port_name
        req.ns = ns
        ret = self.match_engine.fetch(req)
        if not ret["error"] and len(ret["keys"]) != 0:
            ret_temp[req.db]["keys"] = ret["keys"]
        else:
            ret_temp[req.db]["tables_not_found"] = [req.table]
        return ret_temp
        
    
    def get_state_info(self, port_name, ret_temp, ns):
        req = MatchRequest()
        req.db = "STATE_DB"
        req.table = "PORT_TABLE"
        req.key_pattern = port_name
        req.ns = ns
        ret = self.match_engine.fetch(req)
        if not ret["error"] and len(ret["keys"]) != 0:
            ret_temp[req.db]["keys"] = ret["keys"]
        else:
            ret_temp[req.db]["tables_not_found"] = [req.table]
        return ret_temp
    
    def get_asic_info_hostif(self, port_name, ret_temp, ns):
        req = MatchRequest()
        req.db = "ASIC_DB"
        req.table = "ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF"
        req.key_pattern = "*"
        req.field = "SAI_HOSTIF_ATTR_NAME"
        req.value = port_name
        req.return_fields = ["SAI_HOSTIF_ATTR_OBJ_ID"]
        req.ns = ns
        ret = self.match_engine.fetch(req)
        
        asic_port_obj_id = ""
        
        if not ret["error"] and len(ret["keys"]) != 0:
            ret_temp[req.db]["keys"] = ret["keys"]
            if ret["keys"][-1] in ret["return_values"] and "SAI_HOSTIF_ATTR_OBJ_ID" in ret["return_values"][ret["keys"][-1]]:
                asic_port_obj_id = ret["return_values"][ret["keys"][-1]]["SAI_HOSTIF_ATTR_OBJ_ID"]
        else:
            ret_temp[req.db]["tables_not_found"] = [req.table]
        return ret_temp, asic_port_obj_id
        
        
    def get_asic_info_port(self, asic_port_obj_id, ret_temp, ns):
        if not asic_port_obj_id: 
            ret_temp["ASIC_DB"]["tables_not_found"].append("ASIC_STATE:SAI_OBJECT_TYPE_PORT")
            return ret_temp
        
        req = MatchRequest()
        req.db = "ASIC_DB"
        req.table = "ASIC_STATE:SAI_OBJECT_TYPE_PORT"
        req.key_pattern = asic_port_obj_id
        req.ns = ns
        ret = self.match_engine.fetch(req)
        if not ret["error"] and len(ret["keys"]) != 0:
            ret_temp[req.db]["keys"].append(ret["keys"][-1])
        else:
            ret_temp[req.db]["tables_not_found"].append("ASIC_STATE:SAI_OBJECT_TYPE_PORT")
        return ret_temp
        
        
        