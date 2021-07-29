import json, re
from .executor import Executor
from dump.match_infra import MatchEngine, MatchRequest
from dump.helper import create_template_dict

NH = "ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP"
NH_GRP = "ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP"
RIF = "ASIC_STATE:SAI_OBJECT_TYPE_ROUTER_INTERFACE"
CPU_PORT = "ASIC_STATE:SAI_OBJECT_TYPE_PORT"

def get_route_pattern(dest):
    return "*\"dest\":\"" + dest + "\"*"

def get_vr_oid(asic_route_entry):
    matches = re.findall("\{.*\}", asic_route_entry)
    key_dict = {}
    if matches:
        try:
            key_dict = json.loads(matches[0])
        except Exception as e:
            pass
    return key_dict.get("vr", "")

class Route(Executor):
    """
    Debug Dump Plugin for Route Module
    """
    ARG_NAME = "destination_network"
    
    def __init__(self):
        self.match_engine = MatchEngine()
        self.ret_temp = {}
        self.ns = ''
        self.dest_net = ''
        self.nh_id = ''
        self.nh_type = ''
          
    def get_all_args(self, ns=""):
        req = MatchRequest(db="APPL_DB", table="ROUTE_TABLE", key_pattern="*", ns=self.ns)
        ret = self.match_engine.fetch(req)
        all_routes = ret.get("keys", [])
        return [key[len("ROUTE_TABLE:"):] for key in all_routes]
            
    def execute(self, params):
        self.ret_temp = create_template_dict(dbs=["CONFIG_DB", "APPL_DB", "ASIC_DB"])
        self.dest_net = params[Route.ARG_NAME]
        self.ns = params["namespace"]
        # CONFIG DB
        if not self.init_route_config_info():
            del self.ret_temp["CONFIG_DB"]
        # APPL DB
        self.init_route_appl_info()
        # ASIC DB - ROUTE ENTRY
        self.nh_id, vr = self.init_asic_route_entry_info()
        # ASIC DB - VIRTUAL ROUTER
        self.init_asic_vr_info(vr)
        # ASIC DB - KEYS dependent on NEXT HOP ID
        self.init_asic_nh()
        return self.ret_temp
    
    def add_to_ret_template(self, table, db, keys, err, add_to_tables_not_found=True):
        if not err and keys:
            self.ret_temp[db]["keys"].extend(keys)
            return keys
        elif add_to_tables_not_found:
            self.ret_temp[db]["tables_not_found"].extend([table])
        return []
    
    def init_route_config_info(self):
        req = MatchRequest(db="CONFIG_DB", table="STATIC_ROUTE", key_pattern=self.dest_net, ns=self.ns)
        ret = self.match_engine.fetch(req)
        return self.add_to_ret_template(req.table, req.db, ret["keys"], ret["error"])
    
    def init_route_appl_info(self):
        req = MatchRequest(db="APPL_DB", table="ROUTE_TABLE", key_pattern=self.dest_net, ns=self.ns)
        ret = self.match_engine.fetch(req)
        self.add_to_ret_template(req.table, req.db, ret["keys"], ret["error"], True)
        
    def init_asic_route_entry_info(self):
        nh_id_field = "SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID"
        req = MatchRequest(db="ASIC_DB", table="ASIC_STATE:SAI_OBJECT_TYPE_ROUTE_ENTRY", key_pattern=get_route_pattern(self.dest_net), 
                           ns=self.ns, return_fields=[nh_id_field])
        ret = self.match_engine.fetch(req)
        keys = self.add_to_ret_template(req.table, req.db, ret["keys"], ret["error"], True)
        asic_route_entry = keys[0] if keys else ""
        vr = get_vr_oid(asic_route_entry)
        nh_id = ret["return_values"].get(asic_route_entry, {}).get(nh_id_field, "")
        return nh_id, vr

    def init_asic_vr_info(self, vr):
        ret = {}
        if vr:
            req = MatchRequest(db="ASIC_DB", table="ASIC_STATE:SAI_OBJECT_TYPE_VIRTUAL_ROUTER", key_pattern=vr, ns=self.ns)
            ret = self.match_engine.fetch(req)
        self.add_to_ret_template("ASIC_STATE:SAI_OBJECT_TYPE_VIRTUAL_ROUTER", "ASIC_DB", ret.get("keys", []), ret.get("error", ""))
    
    def init_asic_nh(self):
        self.nh_type = self.get_nh_type()
        nh_ex = NHExtractor.initialize(self)
        nh_ex.collect()
        
    def get_nh_type(self):
        if not self.nh_id: 
            return "DROP"
        ret = self.match_engine.fetch(MatchRequest(db="ASIC_DB", table=NH, key_pattern=self.nh_id, ns=self.ns))
        if ret["keys"]: 
            return NH
        ret = self.match_engine.fetch(MatchRequest(db="ASIC_DB", table=NH_GRP, key_pattern=self.nh_id, ns=self.ns))
        if ret["keys"]: 
            return NH_GRP
        ret = self.match_engine.fetch(MatchRequest(db="ASIC_DB", table=RIF, key_pattern=self.nh_id, ns=self.ns))
        if ret["keys"]: 
            return RIF
        ret = self.match_engine.fetch(MatchRequest(db="ASIC_DB", table=CPU_PORT, key_pattern=self.nh_id, ns=self.ns))
        if ret["keys"]: 
            return CPU_PORT            
    
class NHExtractor:
    """
    Base Class for NH_ID Type
    """
    @staticmethod
    def initialize(route_obj):
        if route_obj.nh_type == NH:
            return SingleNextHop(route_obj)
        elif route_obj.nh_type == NH_GRP:
            return MultipleNextHop(route_obj)
        elif route_obj.nh_type == RIF:
            return DirecAttachedRt(route_obj)
        elif route_obj.nh_type == CPU_PORT:
            return CPUPort(route_obj)
        else:          
            return NHExtractor(route_obj)
        
    def __init__(self, route_obj):
        self.rt = route_obj

    def collect(self):
        pass
    
    def init_asic_rif_info(self, oid, add_to_tables_not_found=True):
        ret = {}
        if oid: 
            req = MatchRequest(db="ASIC_DB", table=RIF, key_pattern=oid, ns=self.rt.ns)
            ret = self.rt.match_engine.fetch(req)
        return self.rt.add_to_ret_template(RIF, "ASIC_DB", ret.get("keys", []), ret.get("error", ""), add_to_tables_not_found)
    
    def init_asic_next_hop_info(self, oid, add_to_tables_not_found=True):
        ret = {}
        if oid:
            req = MatchRequest(db="ASIC_DB", table=NH, key_pattern=oid, ns=self.rt.ns,
                               return_fields=["SAI_NEXT_HOP_ATTR_ROUTER_INTERFACE_ID"])
            ret = self.rt.match_engine.fetch(req)
        keys = self.rt.add_to_ret_template(NH, "ASIC_DB", ret.get("keys", []), ret.get("error", ""), add_to_tables_not_found)
        nh_key = keys[0] if keys else ""
        return ret.get("return_values", {}).get(nh_key, {}).get("SAI_NEXT_HOP_ATTR_ROUTER_INTERFACE_ID", "")    
        
class CPUPort(NHExtractor):
    def __init__(self, route_obj):
        super().__init__(route_obj)
    
    def collect(self):
        req = MatchRequest(db="ASIC_DB", table=CPU_PORT, key_pattern=self.rt.nh_id, ns=self.rt.ns)
        ret = self.rt.match_engine.fetch(req)
        self.rt.add_to_ret_template(req.table, req.db, ret["keys"], ret["error"], True)

class DirecAttachedRt(NHExtractor):
    def __init__(self, route_obj):
        super().__init__(route_obj)
    
    def collect(self):
        self.init_asic_rif_info(self.rt.nh_id) 
        
class SingleNextHop(NHExtractor):
    def __init__(self, route_obj):
        super().__init__(route_obj)
    
    def collect(self):
        rif_oid  = self.init_asic_next_hop_info(self.rt.nh_id)
        self.init_asic_rif_info(rif_oid)      
    
class MultipleNextHop(NHExtractor):
    def __init__(self, route_obj):
        super().__init__(route_obj) 
    
    def init_asic_nh_group_info(self, oid):
        ret = {}
        if oid:
            req = MatchRequest(db="ASIC_DB", table=NH_GRP, value=oid, ns=self.rt.ns)
            ret = self.rt.match_engine.fetch(req)
        self.rt.add_to_ret_template(NH_GRP, "ASIC_DB", ret.get("keys", []), ret.get("error", ""))
        
    def init_asic_nh_group_members_info(self, oid):
        ret = {}
        if oid:
            req = MatchRequest(db="ASIC_DB", table="ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP_MEMBER", 
                               field="SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_GROUP_ID",  value=oid, ns=self.rt.ns, 
                               return_fields=["SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_ID"])
            ret = self.rt.match_engine.fetch(req)    
        keys = self.rt.add_to_ret_template("ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP_MEMBER", "ASIC_DB", 
                                           ret.get("keys", []), ret.get("error", ""), False)
        if not keys:
            self.rt.ret_temp["ASIC_DB"]["tables_not_found"].append("ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP_MEMBER")
        return [ret.get("return_values", {}).get(key, {}).get("SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_ID", "") for key in keys]
    
    def init_asic_next_hops_info(self, nh_oids):
        rif_oids = []
        for oid in nh_oids:
            rif_oid = self.init_asic_next_hop_info(oid, False)
            if rif_oid:
                rif_oids.append(rif_oid)
        if not rif_oids:
            self.rt.ret_temp["ASIC_DB"]["tables_not_found"].append("ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP")
        return rif_oids
    
    def init_asic_rifs_info(self, rif_oids):
        nothing_found = True
        for oid in rif_oids:
            if self.init_asic_rif_info(oid, False):
                nothing_found = False
        if nothing_found:
            self.rt.ret_temp["ASIC_DB"]["tables_not_found"].append("ASIC_STATE:SAI_OBJECT_TYPE_ROUTER_INTERFACE")
        
    def collect(self):
        self.init_asic_nh_group_info(self.rt.nh_id)
        nh_oids = self.init_asic_nh_group_members_info(self.rt.nh_id)
        rif_oids = self.init_asic_next_hops_info(nh_oids)
        self.init_asic_rifs_info(rif_oids)

  
        
        
        
        
        
        
        
