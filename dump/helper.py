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

# Handles general error conditions, if any experienced by the module,
# Set excep = True, to raise a exception 
def handle_error(err_str, excep=False):
    if excep:
        raise Exception("ERROR : {}".format(err_str))
    else:
        print("ERROR : {}".format(err_str))
    

def handle_multiple_keys_matched_error(err_str, key_to_go_with="", excep=False):
    if excep:
        handle_error(err_str, True)
    else:
        print("ERROR (AMBIGUITY): {} \n Proceeding with the key {}".format(err_str, key_to_go_with))


def sort_lists(ret):
    for db in ret.keys():
        for key in ret[db].keys():
            if isinstance(ret[db][key], list):
                ret[db][key].sort()
    return ret