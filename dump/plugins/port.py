import os, sys
from .executor import Executor
from dump.match_infra import MatchEngine, MatchRequest
from dump.helper import create_template_dict

class Port(Executor):
    
    ARG_NAME = "port_name"
    
    def __init__(self):
        self.match_engine = MatchEngine()
        self.ret_temp = {}
        self.ns = ''
          
    def get_all_args(self, ns=""):
        req = MatchRequest(db="CONFIG_DB", table="PORT", key_pattern="*", ns=ns)
        ret = self.match_engine.fetch(req)
        all_ports = ret["keys"]
        return [key.split("|")[-1] for key in all_ports]
            
    def execute(self, params_dict):
        self.ret_temp = create_template_dict(dbs=["CONFIG_DB", "APPL_DB", "ASIC_DB", "STATE_DB"])
        port_name = params_dict[Port.ARG_NAME]
        self.ns = params_dict["namespace"]
        self.init_port_config_info(port_name)
        self.init_port_appl_info(port_name)
        port_asic_obj = self.init_asic_hostif_info(port_name)
        self.init_asic_port_info(port_asic_obj)
        self.init_state_port_info(port_name)
        return self.ret_temp
    
    def init_port_config_info(self, port_name):
        req = MatchRequest(db="CONFIG_DB", table="PORT", key_pattern=port_name, ns=self.ns)
        ret = self.match_engine.fetch(req)
        if not ret["error"] and len(ret["keys"]) != 0:
            self.ret_temp[req.db]["keys"] = ret["keys"]
        else:
            self.ret_temp[req.db]["tables_not_found"] = [req.table]
    
    def init_port_appl_info(self, port_name):
        req = MatchRequest(db="APPL_DB", table="PORT_TABLE", key_pattern=port_name, ns=self.ns)
        ret = self.match_engine.fetch(req)
        if not ret["error"] and len(ret["keys"]) != 0:
            self.ret_temp[req.db]["keys"] = ret["keys"]
        else:
            self.ret_temp[req.db]["tables_not_found"] = [req.table]
        
    
    def init_state_port_info(self, port_name):
        req = MatchRequest(db="STATE_DB", table="PORT_TABLE", key_pattern=port_name, ns=self.ns)
        ret = self.match_engine.fetch(req)
        if not ret["error"] and len(ret["keys"]) != 0:
            self.ret_temp[req.db]["keys"] = ret["keys"]
        else:
            self.ret_temp[req.db]["tables_not_found"] = [req.table]
    
    def init_asic_hostif_info(self, port_name):
        req = MatchRequest(db="ASIC_DB", table="ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF", key_pattern="*", field="SAI_HOSTIF_ATTR_NAME", 
                           value=port_name, return_fields=["SAI_HOSTIF_ATTR_OBJ_ID"], ns=self.ns)
        ret = self.match_engine.fetch(req)
        asic_port_obj_id = ""
        
        if not ret["error"] and len(ret["keys"]) != 0:
            self.ret_temp[req.db]["keys"] = ret["keys"]
            sai_hostif_obj_key = ret["keys"][-1]
            if sai_hostif_obj_key in ret["return_values"] and "SAI_HOSTIF_ATTR_OBJ_ID" in ret["return_values"][sai_hostif_obj_key]:
                asic_port_obj_id = ret["return_values"][sai_hostif_obj_key]["SAI_HOSTIF_ATTR_OBJ_ID"]
        else:
            self.ret_temp[req.db]["tables_not_found"] = [req.table]
        return asic_port_obj_id
           
    def init_asic_port_info(self, asic_port_obj_id):
        if not asic_port_obj_id: 
            self.ret_temp["ASIC_DB"]["tables_not_found"].append("ASIC_STATE:SAI_OBJECT_TYPE_PORT")
            return 
        req = MatchRequest(db="ASIC_DB", table="ASIC_STATE:SAI_OBJECT_TYPE_PORT", key_pattern=asic_port_obj_id, ns=self.ns)
        ret = self.match_engine.fetch(req)
        if not ret["error"] and len(ret["keys"]) != 0:
            sai_port_obj_key = ret["keys"][-1]
            self.ret_temp[req.db]["keys"].append(sai_port_obj_key)
        else:
            self.ret_temp[req.db]["tables_not_found"].append("ASIC_STATE:SAI_OBJECT_TYPE_PORT") 
