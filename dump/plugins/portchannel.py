from dump.match_infra import MatchRequest
from dump.helper import create_template_dict, verbose_print
from dump.match_helper import fetch_lag_oid, get_lag_members_from_cfg
from .executor import Executor


class Portchannel(Executor):
    """
    Debug Dump Plugin for PortChannel/LAG Module
    """
    ARG_NAME = "portchannel_name"

    def __init__(self, match_engine=None):
        super().__init__(match_engine)
        self.ns = ''
        self.lag_members = set()

    def get_all_args(self, ns=""):
        req = MatchRequest(db="CONFIG_DB", table="PORTCHANNEL", key_pattern="*", ns=ns)
        ret = self.match_engine.fetch(req)
        all_lags = ret["keys"]
        return [key.split("|")[-1] for key in all_lags]

    def execute(self, params_dict):
        self.ret_temp = create_template_dict(dbs=["CONFIG_DB", "APPL_DB", "ASIC_DB", "STATE_DB"])
        self.lag_name = params_dict[Portchannel.ARG_NAME]
        self.ns = params_dict["namespace"]
        # CONFIG_DB
        self.init_lag_config_info()
        # APPL_DB
        self.init_lag_appl_info()
        # STATE_DB
        self.init_lag_state_info()
        # ASIC_DB
        self.init_lag_asic_info()
        return self.ret_temp

    def init_lag_config_info(self):
        req = MatchRequest(db="CONFIG_DB", table="PORTCHANNEL", key_pattern=self.lag_name, ns=self.ns)
        ret = self.match_engine.fetch(req)
        return self.add_to_ret_template(req.table, req.db, ret["keys"], ret["error"])

    def init_lag_appl_info(self):
        req = MatchRequest(db="APPL_DB", table="LAG_TABLE", key_pattern=self.lag_name, ns=self.ns)
        ret = self.match_engine.fetch(req)
        return self.add_to_ret_template(req.table, req.db, ret["keys"], ret["error"])

    def init_lag_state_info(self):
        req = MatchRequest(db="STATE_DB", table="LAG_TABLE", key_pattern=self.lag_name, ns=self.ns)
        ret = self.match_engine.fetch(req)
        return self.add_to_ret_template(req.table, req.db, ret["keys"], ret["error"])

    def init_lag_asic_info(self):
        # Fetch Lag Members from CFG DB
        _, lag_members, _ = get_lag_members_from_cfg(self.match_engine, self.lag_name, self.ns)
        # Fetch Lag Type Asic Obj from Members info
        _, lag_type_objs_asic, _ = fetch_lag_oid(self.match_engine, lag_members, self.ns)
        if len(lag_type_objs_asic) == 0:
            self.ret_temp["ASIC_DB"]["tables_not_found"].extend(["ASIC_STATE:SAI_OBJECT_TYPE_LAG"])
            return
        for lag_asic_obj in lag_type_objs_asic:
            req = MatchRequest(db="ASIC_DB", table="ASIC_STATE:SAI_OBJECT_TYPE_LAG", key_pattern=lag_asic_obj, ns=self.ns)
            ret = self.match_engine.fetch(req)
            self.add_to_ret_template(req.table, req.db, ret["keys"], ret["error"])