import os, sys
from .executor import Executor

sys.path.append(os.path.join(os.path.dirname(__file__), "../")) # Add dump to the path
# from redis_match import RedisMatchRequest, RedisMatchEngine
# from helper import display_template

CFG_COPP_TRAP_TABLE_NAME       =              "COPP_TRAP"
CFG_COPP_GROUP_TABLE_NAME      =              "COPP_GROUP"
APP_COPP_TABLE_NAME            =              "COPP_TABLE"

ASIC_DB_PREFIX                 =              "ASIC_STATE"

ASIC_TRAP_OBJ                  =              ASIC_DB_PREFIX + ":" + "SAI_OBJECT_TYPE_HOSTIF_TRAP"
ASIC_TRAP_GROUP_OBJ            =              ASIC_DB_PREFIX + ":" + "SAI_OBJECT_TYPE_HOSTIF_TRAP_GROUP"
ASIC_POLICER_OBJ               =              ASIC_DB_PREFIX + ":" + "SAI_OBJECT_TYPE_POLICER"
ASIC_QUEUE_OBJ                 =              ASIC_DB_PREFIX + ":" + "SAI_OBJECT_TYPE_QUEUE"

trap_id_map = { 
    "stp" : "SAI_HOSTIF_TRAP_TYPE_STP" ,
    "lacp" : "SAI_HOSTIF_TRAP_TYPE_LACP" ,
    "eapol" : "SAI_HOSTIF_TRAP_TYPE_EAPOL" ,
    "lldp" : "SAI_HOSTIF_TRAP_TYPE_LLDP" ,
    "pvrst" : "SAI_HOSTIF_TRAP_TYPE_PVRST" ,
    "igmp_query" : "SAI_HOSTIF_TRAP_TYPE_IGMP_TYPE_QUERY" ,
    "igmp_leave" : "SAI_HOSTIF_TRAP_TYPE_IGMP_TYPE_LEAVE" ,
    "igmp_v1_report" : "SAI_HOSTIF_TRAP_TYPE_IGMP_TYPE_V1_REPORT" ,
    "igmp_v2_report" : "SAI_HOSTIF_TRAP_TYPE_IGMP_TYPE_V2_REPORT" ,
    "igmp_v3_report" : "SAI_HOSTIF_TRAP_TYPE_IGMP_TYPE_V3_REPORT" ,
    "sample_packet" : "SAI_HOSTIF_TRAP_TYPE_SAMPLEPACKET" ,
    "switch_cust_range" : "SAI_HOSTIF_TRAP_TYPE_SWITCH_CUSTOM_RANGE_BASE" ,
    "arp_req" : "SAI_HOSTIF_TRAP_TYPE_ARP_REQUEST" ,
    "arp_resp" : "SAI_HOSTIF_TRAP_TYPE_ARP_RESPONSE" ,
    "dhcp" : "SAI_HOSTIF_TRAP_TYPE_DHCP" ,
    "ospf" : "SAI_HOSTIF_TRAP_TYPE_OSPF" ,
    "pim" : "SAI_HOSTIF_TRAP_TYPE_PIM" ,
    "vrrp" : "SAI_HOSTIF_TRAP_TYPE_VRRP" ,
    "bgp" : "SAI_HOSTIF_TRAP_TYPE_BGP" ,
    "dhcpv6" : "SAI_HOSTIF_TRAP_TYPE_DHCPV6" ,
    "ospfv6" : "SAI_HOSTIF_TRAP_TYPE_OSPFV6" ,
    "vrrpv6" : "SAI_HOSTIF_TRAP_TYPE_VRRPV6" ,
    "bgpv6" : "SAI_HOSTIF_TRAP_TYPE_BGPV6" ,
    "neigh_discovery" : "SAI_HOSTIF_TRAP_TYPE_IPV6_NEIGHBOR_DISCOVERY" ,
    "mld_v1_v2" : "SAI_HOSTIF_TRAP_TYPE_IPV6_MLD_V1_V2" ,
    "mld_v1_report" : "SAI_HOSTIF_TRAP_TYPE_IPV6_MLD_V1_REPORT" ,
    "mld_v1_done" : "SAI_HOSTIF_TRAP_TYPE_IPV6_MLD_V1_DONE" ,
    "mld_v2_report" : "SAI_HOSTIF_TRAP_TYPE_MLD_V2_REPORT" ,
    "ip2me" : "SAI_HOSTIF_TRAP_TYPE_IP2ME" ,
    "ssh" : "SAI_HOSTIF_TRAP_TYPE_SSH" ,
    "snmp" : "SAI_HOSTIF_TRAP_TYPE_SNMP" ,
    "router_custom_range" : "SAI_HOSTIF_TRAP_TYPE_ROUTER_CUSTOM_RANGE_BASE" ,
    "l3_mtu_error" : "SAI_HOSTIF_TRAP_TYPE_L3_MTU_ERROR" ,
    "ttl_error" : "SAI_HOSTIF_TRAP_TYPE_TTL_ERROR" ,
    "udld" : "SAI_HOSTIF_TRAP_TYPE_UDLD" ,
    "bfd" : "SAI_HOSTIF_TRAP_TYPE_BFD" ,
    "bfdv6" : "SAI_HOSTIF_TRAP_TYPE_BFDV6" ,
    "src_nat_miss" : "SAI_HOSTIF_TRAP_TYPE_SNAT_MISS" ,
    "dest_nat_miss" : "SAI_HOSTIF_TRAP_TYPE_DNAT_MISS" 
}



# class Copp(Executor):
#     
#     def __init__(self):
#         self.RMEngine = RedisMatchEngine()
#         
#         self.cf_trap_id = ""
#         self.cf_trap_group = ""
#         self.asic_trap_obj = ""
#         self.asic_group_obj = ""
#         self.asic_policer_obj = ""
#         self.asic_queue_obj = ""
#     
#     def execute(self, vargs):
#         
#         self.template = display_template(dbs=["CONFIG_DB", "APPL_DB", "ASIC_DB"])
#         
#         if not vargs:
#             self.template['errror'] = "No Trap_id provided!!"
#             return self.template
#         
#         self.cf_trap_id = vargs[0]
#         
#         if not self.__gen_conf_trap():
#             return self.template
#         
#         self.__gen_conf_group()
# 
#         if not self.__gen_appl_trap():
#             return self.template
#         
#         if not self.__gen_asic_trap():
#             return self.template
#         
#         if not self.__gen_asic_group():
#             return self.template
#         
#         self.__gen_asic_policer()
#         self.__gen_asic_queue()
#         
#         return self.template
#        
#     def __gen_conf_trap(self):
#         
#         if not(self.cf_trap_id) or self.cf_trap_id not in trap_id_map:
#             self.template['error'][CFG_COPP_TRAP_TABLE_NAME] = "Trap id provided is not valid"
#             return False
#         
#         req = RedisMatchRequest()
#         req.table = CFG_COPP_TRAP_TABLE_NAME
#         req.hash_key = "trap_ids"
#         req.value = self.cf_trap_id
#         req.return_keys = ["trap_group"]
#         req.db = "CONFIG_DB"
#         ans = self.RMEngine.fetch(req)
#         
#         if ans['status'] != 0 or ans['error'] != "":
#             self.template['error'][CFG_COPP_TRAP_TABLE_NAME] = ans['error']
#             return False
#         
#         self.cf_trap_group = ans['return_keys']['trap_group']
#         self.template[req.db]['dump'].append(ans['dump'])
#         return True
#         
#     def __gen_conf_group(self):
#         
#         if not(self.cf_trap_group):
#             self.template['error'][CFG_COPP_GROUP_TABLE_NAME]  = "Invalid Trap group !!!"
#             return False
#         
#         req = RedisMatchRequest()
#         req.table = CFG_COPP_GROUP_TABLE_NAME
#         req.value = self.cf_trap_group
#         req.db = "CONFIG_DB"
#         ans = self.RMEngine.fetch(req)
#         
#         if ans['status'] != 0 or ans['error'] != "":
#             self.template['error'][CFG_COPP_GROUP_TABLE_NAME] = ans['error']
#             return True
#         
#         self.template[req.db]['dump'].append(ans['dump'])
#         return True
#            
#     
#     def __gen_appl_trap(self):
#         
#         if not(self.cf_trap_group):
#             self.template['error'][APP_COPP_TABLE_NAME] = "Invalid Trap group !!!"
#             return False
#         
#         req = RedisMatchRequest()
#         req.table = APP_COPP_TABLE_NAME
#         req.value = self.cf_trap_group
#         req.db = "APPL_DB"
#         ans = self.RMEngine.fetch(req)
#         
#         if ans['status'] != 0 or ans['error'] != "":
#             self.template['error'][APP_COPP_TABLE_NAME] = ans['error']
#             return False
#         
#         self.template[req.db]['dump'].append(ans['dump'])
#         return True
# 
#     
#     def __gen_asic_trap(self):
#         
#         self.asic_trap_obj = trap_id_map[self.cf_trap_id]
#         
#         req = RedisMatchRequest()
#         req.table = ASIC_TRAP_OBJ
#         req.hash_key = "SAI_HOSTIF_TRAP_ATTR_TRAP_TYPE"
#         req.value = self.asic_trap_obj
#         req.db = "ASIC_DB"
#         req.return_keys = ["SAI_HOSTIF_TRAP_ATTR_TRAP_GROUP"]
#         ans = self.RMEngine.fetch(req)
#         
#         if ans['status'] != 0 or ans['error'] != "":
#             self.template['error'][ASIC_TRAP_OBJ] = ans['error']
#             return False
#         
#         self.asic_group_obj = ans['return_keys']["SAI_HOSTIF_TRAP_ATTR_TRAP_GROUP"]
#         self.template[req.db]['dump'].append(ans['dump'])
#         return True
#     
#     def __gen_asic_group(self):
#         
#         if not(self.asic_group_obj):
#             self.template['error'][ASIC_TRAP_GROUP_OBJ]  = " ASIC Group Obj Can't be empty !!!"
#             return False
#         
#         req = RedisMatchRequest()
#         req.table =  ASIC_TRAP_GROUP_OBJ
#         req.value = self.asic_group_obj
#         req.db = "ASIC_DB"
#         req.return_keys = ["SAI_HOSTIF_TRAP_GROUP_ATTR_QUEUE", "SAI_HOSTIF_TRAP_GROUP_ATTR_POLICER"]
#         ans = self.RMEngine.fetch(req)
#         
#         if ans['status'] != 0 or ans['error'] != "":
#             self.template['error'][ASIC_TRAP_GROUP_OBJ] = ans['error']
#             return False
#         
#         self.asic_policer_obj = ans['return_keys']["SAI_HOSTIF_TRAP_GROUP_ATTR_POLICER"]
#         self.asic_queue_obj = ans['return_keys']["SAI_HOSTIF_TRAP_GROUP_ATTR_QUEUE"]
#         
#         self.template[req.db]['dump'].append(ans['dump'])
#         return True
#     
#     def __gen_asic_policer(self):
#         
#         if not(self.asic_policer_obj):
#             self.template['error'][ASIC_POLICER_OBJ]  = "Invalid SAI Policer Object!!!"
#             return False
#         
#         req = RedisMatchRequest()
#         req.table = ASIC_POLICER_OBJ
#         req.value = self.asic_policer_obj
#         req.db = "ASIC_DB"
#         ans = self.RMEngine.fetch(req)
#         
#         if ans['status'] != 0 or ans['error'] != "":
#             self.template['error'][ASIC_POLICER_OBJ]  = ans['error']
#             return True
#         
#         self.template[req.db]['dump'].append(ans['dump'])
#         return True
#     
#     def __gen_asic_queue(self):
#         
#         if not(self.asic_queue_obj):
#             self.template['error'][ASIC_QUEUE_OBJ]  = "Invalid SAI Queue Object!!!"
#             return False
#         
#         req = RedisMatchRequest()
#         req.table = ASIC_QUEUE_OBJ
#         req.hash_key = "SAI_QUEUE_ATTR_INDEX"
#         req.value = self.asic_queue_obj
#         req.db = "ASIC_DB"
#         ans = self.RMEngine.fetch(req)
#         
#         if ans['status'] != 0 or ans['error'] != "":
#             self.template['error'][ASIC_QUEUE_OBJ]  = ans['error']
#             return True
#         
#         self.template[req.db]['dump'].append(ans['dump'])
#     
#         return True
        
        


    
    