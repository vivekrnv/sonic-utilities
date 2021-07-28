from .executor import Executor
from dump.match_infra import MatchEngine, MatchRequest
from dump.helper import create_template_dict

class Route(Executor):
    """
    Debug Dump Plugin for Route Module
    """
    ARG_NAME = "destination_network"
    
    def __init__(self):
        self.match_engine = MatchEngine()
        self.ret_temp = {}
        self.ns = ''
          
    def get_all_args(self, ns=""):
        return ""
            
    def execute(self, params):
        self.ret_temp = create_template_dict(dbs=["CONFIG_DB", "APPL_DB", "ASIC_DB"])
        self.dest_net = params[Route.ARG_NAME]
        self.ns = params["namespace"]
        self.init_route_config_info()
        self.init_route_appl_info()
        return self.ret_temp
    
    def add_to_ret_template(self, table, db, keys, err, add_to_tables_not_found=True):
        if not err and keys:
            self.ret_temp[db]["keys"].extend(keys)
        elif add_to_tables_not_found:
            self.ret_temp[db]["tables_not_found"].extend([table])
    
    def init_route_config_info(self):
        req = MatchRequest(db="CONFIG_DB", table="STATIC_ROUTE", key_pattern=self.dest_net, ns=self.ns)
        ret = self.match_engine.fetch(req)
        self.add_to_ret_template(req.table, req.db, ret["keys"], ret["error"])
    
    def init_route_appl_info(self):
        req = MatchRequest(db="APPL_DB", table="ROUTE_TABLE", key_pattern=self.dest_net, ns=self.ns)
        ret = self.match_engine.fetch(req)
        self.add_to_ret_template(req.table, req.db, ret["keys"], ret["error"], True)
    
    def init_asic_route_entry_info(self):
        req = MatchRequest(db="APPL_DB", table="ROUTE_TABLE", key_pattern=self.dest_net, ns=self.ns)
        pass