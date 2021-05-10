import os
import json
import click 
import redis
import re
from swsscommon import swsscommon

# Generate a Template whcih can be used by the print_dump 
def display_template(dbs, tabular = False, indent = 4):
    description_map = {"CONFIG_DB" : "Config DB",
                    "APPL_DB"  : "Application DB",
                    "ASIC_DB"  : "ASIC DB"}
    template = {"error" : dict(), "vidtorid" : dict()}   
    
    for db in dbs:
        template[db] = {}
        template[db]['dump'] = []
        template[db]['description'] = ""
        if db in description_map:
            template[db]['description'] = description_map[db]
            
    return template

def verbose_print(str):
    print(str)

def print_dump(final_dict, table, db):
    click.echo(json.dumps(final_dict, indent=4))


def extract_rid(final_dict):
    
    v_r_map = dict()
    r = redis.Redis(unix_socket_path=swsscommon.SonicDBConfig.getDbSock("ASIC_DB"), db=swsscommon.ASIC_DB, encoding="utf-8", decode_responses=True)
    
    if "ASIC_DB" in final_dict and 'dump' in final_dict["ASIC_DB"]:
        for dump_single in final_dict["ASIC_DB"]['dump']:
            
            redis_key = list(dump_single.keys())[0]
            
            if "SAI_OBJECT_TYPE_ROUTE_ENTRY" in redis_key:
                # TODO
                pass
            else:
                matches = re.findall(r"oid:0x\w{14}", redis_key)
                if matches:
                   vid = matches[0]
                   v_r_map[vid] =  vid_to_rid(vid, r)
    return v_r_map
                
# Get a vid:rid for the input vid
def vid_to_rid(vid, r):
    rid = r.hget("VIDTORID", vid)
    if not rid:
        rid = "Real ID Not Found" 
    return rid  
        
    
