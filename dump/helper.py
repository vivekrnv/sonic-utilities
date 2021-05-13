import os,json,re,click
import redis
from swsscommon.swsscommon import SonicDBConfig, ASIC_DB


# Generate a Template which will be returned by Executor Classes
def display_template(dbs):
    template = {}
    for db in dbs:
        template[db] = {}
        template[db]['keys'] = []
        template[db]['tables_not_found'] = []     
    return template

def verbose_print(str):
    if "VERBOSE" in os.environ and os.environ["VERBOSE"] == "1":
        print(str)

# Get a vid:rid for the input vid
def vid_to_rid(vid, r):
    rid = r.hget("VIDTORID", vid)
    if not rid:
        rid = "Real ID Not Found" 
    return rid  

def get_v_r_map(r, single_dict):
    v_r_map = {}
    asic_obj_ptrn = "ASIC_STATE:.*:oid:0x\w{1,14}"
    
    if "ASIC_DB" in single_dict and 'keys' in single_dict["ASIC_DB"]:
        for redis_key in single_dict["ASIC_DB"]['keys']:
            if re.match(asic_obj_ptrn, redis_key):
                matches = re.findall(r"oid:0x\w{1,14}", redis_key)
                if matches:
                   vid = matches[0]
                   v_r_map[vid] =  vid_to_rid(vid, r)
    return v_r_map

def extract_rid(info):
    r = redis.Redis(unix_socket_path=SonicDBConfig.getDbSock("ASIC_DB"), db=ASIC_DB, encoding="utf-8", decode_responses=True)
    vidtorid = {}
    for arg in info.keys():
        vidtorid[arg] = get_v_r_map(r, info[arg])
    return vidtorid

# Filter dbs which are not required
def filter_out_dbs(db_list, collected_info):
    args_ = list(collected_info.keys())
    for arg in args_:
        dbs = list(collected_info[arg].keys())
        for db in dbs:
            if db not in db_list:
                del collected_info[arg][db]
    return collected_info
    
    
    





        
    
