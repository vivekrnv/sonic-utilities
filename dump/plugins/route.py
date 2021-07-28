from .executor import Executor
from dump.match_infra import MatchEngine, MatchRequest
from dump.helper import create_template_dict

class Route(Executor):
    """
    Debug Dump Plugin for PORT Module
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
        port_name = params[Route.ARG_NAME]
        self.ns = params["namespace"]
        return self.ret_temp