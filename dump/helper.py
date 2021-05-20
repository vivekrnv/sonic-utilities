import os

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
