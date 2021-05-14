import os,sys,json,re
import click
from tabulate import tabulate

sys.path.append(os.path.dirname(__file__))
import plugins
from dump.helper import extract_rid, filter_out_dbs
from dump.redis_match import RedisSource, JsonSource

# Autocompletion Helper
def get_available_modules(ctx, args, incomplete):
    return [k for k in plugins.dump_modules.keys() if incomplete in k]

# Display Modules Callback
def show_modules(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    header = ["Module", "Identifier"]
    display = []
    for mod in plugins.dump_modules:
        display.append((mod, plugins.dump_modules[mod].ARG_NAME))
    click.echo(tabulate(display, header))
    ctx.exit()
              
@click.group()
def dump():
    pass

@dump.command()
@click.pass_context
@click.argument('module', required=True, type=str, autocompletion=get_available_modules)
@click.argument('identifier', required=True, type=str) 
@click.option('--show', '-s', is_flag=True, default=False, help='Display Modules Available', is_eager=True, expose_value=False, callback=show_modules)
@click.option('--db', '-d', multiple=True, help='Only dump from these Databases')
@click.option('--table', '-t', is_flag=True, default=False, help='Print in tabular format', show_default=True)
@click.option('--key-map', '-k', is_flag=True, default=False, help="Only fetch the keys matched, don't extract field-value dumps", show_default=True)
@click.option('--verbose', '-v', is_flag=True, default=False, help="Prints any intermediate output to stdout useful for dev & troubleshooting", show_default=True)
def state(ctx, module, identifier, db, table, key_map, verbose):
    """
    Dump the redis-state of the identifier for the module specified
    """

    if module not in plugins.dump_modules:
        click.echo("No Matching Plugin has been Implemented")
        ctx.exit()
    
    if verbose:
        os.environ["VERBOSE"] = "1"
    else:
        os.environ["VERBOSE"] = "0"
    
    ctx.module = module
    obj = plugins.dump_modules[module]()
    
    if identifier == "all":
        ids = obj.get_all_args()
    else:
        ids = identifier.split(",")
        
    params = {}
    collected_info = {}
    for arg in ids: 
        params[plugins.dump_modules[module].ARG_NAME] = arg 
        collected_info[arg] = obj.execute(params)
        
    if len(db) > 0:
        collected_info = filter_out_dbs(db, collected_info)
    
    vidtorid = extract_rid(collected_info)
    
    if not key_map:
        collected_info = populate_fv(collected_info, module)
    
    for id in vidtorid.keys():
        if  vidtorid[id] and vidtorid:
            collected_info[id]["ASIC_DB"]["vidtorid"] = vidtorid[id]
         
    print_dump(collected_info, table, module, identifier, key_map)
    
    return 

def populate_fv(info, module):

    all_dbs = set()
    for id in info.keys():
        for db_name in info[id].keys():
            all_dbs.add(db_name)
            
    db_dict = {}  
    for db_name in all_dbs:
        if db_name is "CONFIG_FILE":
            db_dict[db_name] = JsonSource()
            db_dict[db_name].connect(plugins.dump_modules[module].CONFIG_FILE)
        else:
            db_dict[db_name] = RedisSource()
            db_dict[db_name].connect(db_name)
            
    final_info = {}
    for id in info.keys():
        final_info[id] = {}
        for db_name in info[id].keys():
            final_info[id][db_name] = {}
            final_info[id][db_name]["keys"] = []
            final_info[id][db_name]["tables_not_found"] = info[id][db_name]["tables_not_found"]
            for key in info[id][db_name]["keys"]:
                final_info[id][db_name]["keys"].append({key : db_dict[db_name].get(db_name, key)})
                 
    return final_info

def get_dict_str(key_obj):
    table = []
    for pair in key_obj.items():
        table.append(list(pair))
    return tabulate(table, headers=["field", "value"], tablefmt="psql")

def get_keys(dump):
    keys = []
    for key_ in dump:
        if isinstance(key_, dict) and key_:
            keys.append(list(key_.keys())[0])
        else:
            keys.append(key_)
    return keys

def get_rid(redis_key, vidtorid):
    matches = re.findall(r"oid:0x\w{1,14}", redis_key)
    if matches:
       vid = matches[0]
       if vid in vidtorid:
           return vidtorid[vid]   
    return "Not Found"
 
# print dump
def print_dump(collected_info, table, module, identifier, key_map):
    if not table:
        click.echo(json.dumps(collected_info, indent=4))
        return

    top_header = [plugins.dump_modules[module].ARG_NAME, "DB_NAME", "DUMP"]
    final_collection = []
    for ids in collected_info.keys():
        for db in collected_info[ids].keys():
            total_info = ""

            if collected_info[ids][db]["tables_not_found"]:
                total_info += tabulate(collected_info[ids][db]["tables_not_found"], ["Tables Not Found"])
                total_info += ""
    
            if not key_map:
                values = []
                hdrs = ["Keys", "field-value pairs"]
                for key_obj in collected_info[ids][db]["keys"]:
                    if isinstance(key_obj, dict) and key_obj:
                        key = list(key_obj.keys())[0]
                        values.append([key, get_dict_str(key_obj[key])])
                total_info += str(tabulate(values, hdrs, tablefmt="pretty"))
            else:
                temp = []
                for key_ in collected_info[ids][db]["keys"]:
                    temp.append([key_])
                total_info += str(tabulate(temp, headers=["Keys Collected"], tablefmt="pretty"))

            total_info += "\n"
            if "vidtorid" in collected_info[ids][db]:
                table = []
                for pair in collected_info[ids][db]["vidtorid"].items():
                    table.append(list(pair))
                total_info +=str(tabulate(table, headers=["vid", "rid"], tablefmt="pretty"))
            final_collection.append([ids, db, total_info])

    click.echo(tabulate(final_collection, top_header, tablefmt="grid"))
    return

if __name__ == '__main__':
    dump()
