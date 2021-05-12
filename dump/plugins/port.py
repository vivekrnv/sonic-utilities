
from .executor import Executor
from dump.redis_match import MatchEngine, MatchRequest
from dump.helper import display_template

class Port(Executor):
    
    def __init__(self):
        self.match_engine = MatchEngine()
        self.ret_temp = display_template(dbs=["CONFIG_DB", "APPL_DB", "ASIC_DB", "STATE_DB"])
        
    def get_all_args(self):
        pass
    
    def execute(self, params_dict):
        port_name = params_dict[Port.ARG_NAME]
        self.get_config_info(port_name)
        self.get_appl_info(port_name)
        self.get_asic_info(port_name)
        self.get_state_info(port_name)
        return self.ret_temp
    
    def get_config_info(self, port_name):
        req = MatchRequest()
        req.db = "CONFIG_DB"
        req.table = "PORT"
        req.key_pattern = port_name
        ret = self.match_engine.fetch(req)
        if not ret["error"]:
            self.ret_temp[req.db]["keys"] = ret["keys"]
        else:
            self.ret_temp[req.db]["tables_not_found"] = req.table
    
    def get_appl_info(self, port_name):
        req = MatchRequest()
        req.db = "APPL_DB"
        req.table = "PORT_TABLE"
        req.key_pattern = port_name
        ret = self.match_engine.fetch(req)
        if not ret["error"]:
            self.ret_temp[req.db]["keys"] = ret["keys"]
        else:
            self.ret_temp[req.db]["tables_not_found"] = req.table
        
    
    def get_state_info(self, port_name):
        req = MatchRequest()
        req.db = "STATE_DB"
        req.table = "PORT_TABLE"
        req.key_pattern = port_name
        ret = self.match_engine.fetch(req)
        if not ret["error"]:
            self.ret_temp[req.db]["keys"] = ret["keys"]
        else:
            self.ret_temp[req.db]["tables_not_found"] = req.table
        
    def get_asic_info(self, port_name):
        req = MatchRequest()
        req.db = "ASIC_DB"
        req.table = "ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF"
        req.key_pattern = "*"
        req.field = "SAI_HOSTIF_ATTR_NAME"
        req.value = port_name
        req.return_fields = ["SAI_HOSTIF_ATTR_OBJ_ID"]
        ret = self.match_engine.fetch(req)
        
        asic_port_obj_id = ""
        
        if not ret["error"]:
            self.ret_temp[req.db]["keys"].append(ret["keys"][-1])
            asic_port_obj_id = ret["return_values"][ret["keys"][-1]]["SAI_HOSTIF_ATTR_OBJ_ID"]
        else:
            self.ret_temp[req.db]["tables_not_found"] = [req.table, "ASIC_STATE:SAI_OBJECT_TYPE_PORT"]
            return 
        
        req = MatchRequest()
        req.db = "ASIC_DB"
        req.table = "ASIC_STATE:SAI_OBJECT_TYPE_PORT"
        req.key_pattern = asic_port_obj_id
        ret = self.match_engine.fetch(req)
        if not ret["error"]:
            self.ret_temp[req.db]["keys"].append(ret["keys"][-1])
        else:
            self.ret_temp[req.db]["tables_not_found"] = req.table
        
        
        
        
        