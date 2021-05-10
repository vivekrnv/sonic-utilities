import re, json, os
from swsscommon.swsscommon import SonicV2Connector, SonicDBConfig
from .helper import verbose_print

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
    "BAD_FORMAT_RE_FIELDS": "Return Fields should be of list type"
}

class SourceAdapter:
    def __init__(self, req):
        self.req = req
    
    def connect(self):
        return False
    
    def getKeys(self):
        return []
    
    def get(self, key):
        return {}
    
    def hget(self, key, field):
        return ""
        
class RedisSource(SourceAdapter):
    def __init__(self, req):
        super().__init__(req)
        self.sep = "None"
        
    def connect(self):
        self.db = SonicV2Connector(host="127.0.0.1")
        try:
            self.db.connect(self.req.db, False)
            self.sep = self.db.get_db_separator(self.req.db)
        except Exception as e:
            verbose_print("RedisSource: Connection Failed\n" + str(e))
            return False
        return True
        
    def getKeys(self):       
        try:
            keys = self.db.keys(self.req.db, self.req.table + self.sep + self.req.key_pattern)
        except Exception as e:
            verbose_print("RedisSource: {}|{}|{} Keys fetch Request Failed for DB {}\n".format(self.req.table, self.sep, self.req.key_pattern, self.req.db) + str(e))
            return []
        print(self.req.table + self.sep + self.req.key_pattern)
        return keys
    
    def get(self, key):
        try:
            fv_pairs = self.db.get_all(self.req.db, key)
        except Exception as e:
            verbose_print("RedisSource: hgetall {} request failed for DB {}\n".format(key, self.db) + str(e))
            return {}
        return fv_pairs
     
    def hget(self, key, field):
        try:
            value = self.db.get(self.req.db, key, field)
        except Exception as e:
            verbose_print("RedisSource: hget {} {} request failed for DB {}\n".format(key, field) + str(e))
            return ""
        return value

class JsonSource(SourceAdapter):
    def __init__(self, req):
        super().__init__(req)
    
    def connect(self):
        try:
            with open(self.req.file) as f:
                self.db = json.load(f)
        except Exception as e:
            verbose_print("JsonSource: Loading the JSON file failed" + str(e))
            return False
        return True
    
    def getKeys(self):
        if self.req.table not in self.db:
            return []
        
        all_keys = self.db[self.req.table].keys()
        key_ptrn = self.req.key_pattern
        key_ptrn = key_ptrn.replace("*", ".*")
        filtered_keys = []
        for key in all_keys:
            if re.match(key_ptrn, key):
                filtered_keys.append(key)
        return filtered_keys
    
    def get(self, key):
        if self.req.table in self.db and key in self.db[self.req.table]:
            return self.db[self.req.table][key]
        return {}
            
    def hget(self, key, field):
        if self.req.table in self.db and key in self.db[self.req.table] and field in self.db[self.req.table][key]:
            return self.db[self.req.table][key][field]
        return ""
                         
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
    
    def __str__(self):
        str = "MatchRequest: \n"
        if self.db:
            str += "db : {},".format(self.db)
        if self.file:
            str += "file : {},".format(self.file) 
        if self.table:
            str += "table : {},".format(self.table)
        if self.key_pattern:
            str += "key_regx : {},".format(self.key_pattern)
        if self.field:
            str += "field : {},".format(self.field)
        if self.value:
            str += "value : {},".format(self.value)
        if self.just_keys:
            str += "just_keys: True "
        else:
            str += "just_keys: False "
        if len(self.return_fields) > 0:
            str += "Return Fields: " + ",".join(self.return_fields)
        return str
     
class MatchEngine:
    
    def fetch(self, req):
        verbose_print(str(req))
        template = self.__ret_template()
        template['error']  = self.__validate_request(req)
        if template['error']:
            return self.__return_error(template)
        
        src = None
        if req.db:
            src = RedisSource(req)
        else:
            src = JsonSource(req)
        
        if not src.connect():
            template['error']  = error_dict["CONN_ERR"]
            return self.__return_error(template)
        
        all_matched_keys = src.getKeys()
        verbose_print(all_matched_keys)
        if not all_matched_keys or len(all_matched_keys) == 0:
            template['error'] = error_dict["INV_PTTRN"]
            return self.__return_error(template)
        
        filtered_keys = self.__filter_out_keys(src, req, all_matched_keys)
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
            f_values = src.hget(key, req.field)
            if "," in f_values: # Fields Conatining Multile Values
                f_value = f_values.split(",")
            else:
                f_value = [f_values]
            verbose_print(str(f_value))
            if req.value in f_value :
                filtered_keys.append(key)
        return filtered_keys
        
    def __fill(self, src, req, filtered_keys):
        
        template = self.__ret_template()
        for key in filtered_keys:
            temp = {}
            if not req.just_keys:
                temp[key] = src.get(key)
                template["keys"].append(temp)
            elif len(req.return_fields) > 0:
                template["keys"].append(key)
                template["return_values"][key] = {}
                for field in req.return_fields: 
                    template["return_values"][key][field] = src.hget(key, field)
            else:
                template["keys"].append(key)
        return template
            
            


