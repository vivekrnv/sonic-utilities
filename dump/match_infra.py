import re, json, os, sys
from dump.helper import verbose_print
from swsscommon.swsscommon import SonicV2Connector, SonicDBConfig

error_dict  = {
    "INV_REQ": "Argument should be of type MatchRequest",
    "INV_DB": "DB provided is not valid",
    "INV_JSON": "Not a properly formatted JSON file",
    "INV_PTTRN": "No Entries found for Table|key_pattern provided",
    "NO_FILE": "JSON File not found",
    "NO_SRC": "Either one of db or file in the request should be non-empty",
    "NO_KEY": "'key_pattern' cannot be empty",
    "NO_TABLE": "No 'table' name provided",
    "NO_VALUE" : "Field is provided, but no value is provided to compare with", 
    "SRC_VAGUE": "Only one of db or file should be provided",
    "CONN_ERR" : "Connection Error",
    "JUST_KEYS_COMPAT": "When Just_keys is set to False, return_fields should be empty",
    "BAD_FORMAT_RE_FIELDS": "Return Fields should be of list type",
    "NO_ENTRIES": "No Keys found after applying the filtering criteria"
}

class MatchRequest:
    def __init__(self):
        self.table = None
        self.key_pattern = "*"
        self.field = None
        self.value = None
        self.return_fields = []
        self.db = ""
        self.file = ""
        self.just_keys = True
        self.ns = ''
        self.match_entire_list = False
    
    def __str__(self):
        str = "----------------------- \n MatchRequest: \n"
        if self.db:
            str += "db:{} , ".format(self.db)
        if self.file:
            str += "file:{} , ".format(self.file) 
        if self.table:
            str += "table:{} , ".format(self.table)
        if self.key_pattern:
            str += "key_regx:{} , ".format(self.key_pattern)
        if self.field:
            str += "field:{} , ".format(self.field)
        if self.value:
            str += "value:{} , ".format(self.value)
        if self.just_keys:
            str += "just_keys:True "
        else:
            str += "just_keys:False "
        if len(self.return_fields) > 0:
            str += "Return Fields: " + ",".join(self.return_fields) + " "
        if self.ns:
            str += "Namespace: " + self.ns 
        if self.match_entire_list:
            str += "Match Entire List: True "
        else:
            str += "Match Entire List: False "
        return str
    
class SourceAdapter:
    def __init__(self):
        pass
    
    def connect(self, db, ns):
        return False
    
    def getKeys(self, db, table, key_pattern):
        return []
    
    def get(self, db, key):
        return {}
    
    def hget(self, db, key, field):
        return ""
    
    def sep(self, db):
        return ""
        
class RedisSource(SourceAdapter):
    def __init__(self):
        self.db_driver = None 
        
    def connect(self, db, ns):
        try:
            self.db_driver = SonicV2Connector(namespace=ns, host="127.0.0.1")
            self.db_driver.connect(db)
        except Exception as e:
            verbose_print("RedisSource: Connection Failed\n" + str(e))
            return False
        return True
    
    def sep(self, db):
        return self.db_driver.get_db_separator(db)
       
    def getKeys(self, db, table, key_pattern):       
        try:
            keys = self.db_driver.keys(db, table + self.sep(db) + key_pattern)
        except Exception as e:
            verbose_print("RedisSource: {}|{}|{} Keys fetch Request Failed for DB {}\n".format(table, self.sep(db), key_pattern, db) + str(e))
            return []
        return keys
    
    def get(self, db, key):
        try:
            fv_pairs = self.db_driver.get_all(db, key)
        except Exception as e:
            verbose_print("RedisSource: hgetall {} request failed for DB {}\n".format(key, db) + str(e))
            return {}
        return fv_pairs
     
    def hget(self, db, key, field):
        try:
            value = self.db_driver.get(db, key, field)
        except Exception as e:
            verbose_print("RedisSource: hget {} {} request failed for DB {}\n".format(key, field) + str(e))
            return ""
        return value

class JsonSource(SourceAdapter):
    
    def __init__(self):
        self.db_driver = None
    
    def connect(self, db, ns):
        try:
            with open(db) as f:
                self.db_driver = json.load(f)
        except Exception as e:
            verbose_print("JsonSource: Loading the JSON file failed" + str(e))
            return False
        return True
    
    def sep(self, db):
        return SonicDBConfig.getSeparator("CONFIG_DB")
    
    def getKeys(self, db, table, key_pattern):
        if table not in self.db_driver:
            return []
        
        all_keys = self.db_driver[table].keys()
        key_ptrn = key_pattern
        key_ptrn = re.escape(key_ptrn)
        key_ptrn = key_ptrn.replace("\\*", ".*")
        filtered_keys = []
        for key in all_keys:
            if re.match(key_ptrn, key):
                filtered_keys.append(table+self.sep(db)+key)
        return filtered_keys
    
    def get(self, db, key):
        sp = self.sep(db)
        tokens = key.split(sp)
        key_ptrn = tokens[-1]
        tokens.pop()
        table = sp.join(tokens)
        if table in self.db_driver and key_ptrn in self.db_driver[table]:
            return self.db_driver[table][key_ptrn]
        return {}
            
    def hget(self, db, key, field):
        sp = self.sep(db)
        tokens = key.split(sp)
        key_ptrn = tokens[-1]
        tokens.pop()
        table = sp.join(tokens)
        if table in self.db_driver and key_ptrn in self.db_driver[table] and field in self.db_driver[table][key_ptrn]:
            return self.db_driver[table][key_ptrn][field]
        return ""
                        
class MatchEngine:
    
    # Given a request obj, find its match in the redis
    def fetch(self, req):
        verbose_print(str(req))
        template = self.__ret_template()
        template['error']  = self.__validate_request(req)
        if template['error']:
            return self.__return_error(template)
        
        src = None
        d_src = ""
        if req.db:
            d_src = req.db
            src = RedisSource()
        else:
            d_src = req.file
            src = JsonSource()
        
        if not src.connect(d_src, req.ns):
            template['error']  = error_dict["CONN_ERR"]
            return self.__return_error(template)
        verbose_print("MatchRequest Checks Passed")
        all_matched_keys = src.getKeys(req.db, req.table, req.key_pattern)
        if not all_matched_keys or len(all_matched_keys) == 0:
            template['error'] = error_dict["INV_PTTRN"]
            return self.__return_error(template)
        
        filtered_keys = self.__filter_out_keys(src, req, all_matched_keys)
        verbose_print("Filtered Keys:" + str(filtered_keys))
        if not filtered_keys:
            template['error'] = error_dict["NO_ENTRIES"]
            return self.__return_error(template)
        return self.__fill(src, req, filtered_keys)
    
    def __ret_template(self):
        return {"error" : "", "keys" : [], "return_values" : {}}
    
    
    def __return_error(self, template):
        verbose_print("MatchEngine: \n" + template['error'])
        return template
    
    def __validate_request(self, req):
        
        if not isinstance(req, MatchRequest):
            return error_dict["INV_REQ"]
            
        if not(req.db) and not(req.file):
            return error_dict["NO_SRC"]
        
        if req.db and req.file:
            return error_dict["SRC_VAGUE"]
        
        if not req.db and os.path.exists(req.file):
            try:
                with open(req.file) as f:
                    json.load(f)
            except ValueError as e:
                return error_dict["INV_JSON"] 
        elif not req.db:
            return error_dict["NO_FILE"]
        
        if not(req.file) and req.db not in SonicDBConfig.getDbList():
            return error_dict["INV_DB"]
        
        if not req.table:
            return error_dict["NO_TABLE"]
        
        if not req.key_pattern:
            return error_dict["NO_KEY"]
        
        if not isinstance(req.return_fields, list):
            return error_dict["BAD_FORMAT_RE_FIELDS"]
        
        if not req.just_keys and len(req.return_fields) > 0:
            return error_dict["JUST_KEYS_COMPAT"]
        
        if req.field and not req.value:
            return error_dict["NO_VALUE"]
        
        return ""
    
    def __filter_out_keys(self, src, req, all_matched_keys):
        if not (req.field):
            return all_matched_keys
        
        filtered_keys = []
        for key in all_matched_keys:
            f_values = src.hget(req.db, key, req.field)
            if "," in f_values and not req.match_entire_list: # Fields Containing Multiple Values
                f_value = f_values.split(",")
            else:
                f_value = [f_values]
            if req.value in f_value:
                filtered_keys.append(key)
        return filtered_keys
        
    def __fill(self, src, req, filtered_keys):
        
        template = self.__ret_template()
        for key in filtered_keys:
            temp = {}
            if not req.just_keys:
                temp[key] = src.get(req.db, key)
                template["keys"].append(temp)
            elif len(req.return_fields) > 0:
                template["keys"].append(key)
                template["return_values"][key] = {}
                for field in req.return_fields: 
                    template["return_values"][key][field] = src.hget(req.db, key, field)
            else:
                template["keys"].append(key)
        verbose_print("Return Values:" + str(template["return_values"]))
        return template
