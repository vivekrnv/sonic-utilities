import os
import json
import click 

def display_template(dbs, tabular = False, indent = 4):
    description_map = {"CONFIG_DB" : "Config DB",
                    "APPL_DB"  : "Application DB",
                    "ASIC_DB"  : "ASIC DB"}
    template = {"error" : dict()}   
    
    for db in dbs:
        template[db] = {}
        template[db]['dump'] = []
        template[db]['description'] = ""
        if db in description_map:
            template[db]['description'] = description_map[db]
            
    return template

def print_dump(final_dict):
    click.echo(json.dumps(final_dict, indent=4))
