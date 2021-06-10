import json, fnmatch
from abc import ABC, abstractmethod
from dump.helper import verbose_print
from swsscommon.swsscommon import SonicV2Connector, SonicDBConfig

EXCEP_DICT = {
    "INV_REQ": "Argument should be of type MatchRequest",
    "INV_DB": "DB provided is not valid",
    "NO_MATCHES": "No Entries found for Table|key_pattern provided",
    "NO_SRC": "Either one of db or file in the request should be non-empty",
    "NO_TABLE": "No 'table' name provided",
    "NO_KEY": "'key_pattern' cannot be empty",
    "NO_VALUE" : "Field is provided, but no value is provided to compare with", 
    "SRC_VAGUE": "Only one of db or file should be provided",
    "CONN_ERR" : "Connection Error",
    "JUST_KEYS_COMPAT": "When Just_keys is set to False, return_fields should be empty",
    "BAD_FORMAT_RE_FIELDS": "Return Fields should be of list type",
    "NO_ENTRIES": "No Keys found after applying the filtering criteria",
    "FILE_R_EXEP": "Exception Caught While Reading the json cfg file provided" 
}

class MatchRequest:
    """ 
    Request Object which should be passed to the MatchEngine  
    
    Attributes:
    "table"             : A Valid Table Name
    "key_pattern"       : Pattern of the redis-key to match. Defaults to "*". Eg: "*" will match all the keys.
                          Supports these glob style patterns. https://redis.io/commands/KEYS               
    "field"             : Field to check for a match,Defaults to None
    "value"             : Value to match, Defaults to None
    "return_fields"     : An iterable type, where each element woudld imply a field to return from all the filtered keys
    "db"                : A Valid DB name, Defaults to "".
    "file"              : A Valid Config JSON file, Eg: copp_cfg.json, Defaults to "".
                          Only one of the db/file fields should have a non-empty string.
    "just_keys"         : If true, Only Returns the keys matched. Does not return field-value pairs. Defaults to True
    "ns"                : namespace argument, if nothing is provided, default namespace is used
    "match_entire_list" : When this arg is set to true, entire list is matched incluing the ",". 
                          When False, the values are split based on "," and individual items are matched with
    """
    def __init__(self, **kwargs):
        self.table = kwargs["table"] if "table" in kwargs else None
        self.key_pattern = kwargs["key_pattern"] if "key_pattern" in kwargs else "*"
        self.field = kwargs["field"] if "field" in kwargs else None
        self.value = kwargs["value"] if "value" in kwargs else None
        self.return_fields = kwargs["return_fields"] if "return_fields" in kwargs else []
        self.db = kwargs["db"] if "db" in kwargs else ""
        self.file = kwargs["file"] if "file" in kwargs else ""
        self.just_keys = kwargs["just_keys"] if "just_keys" in kwargs else True
        self.ns = kwargs["ns"] if "ns" in kwargs else ""
        self.match_entire_list = kwargs["match_entire_list"] if "match_entire_list" in kwargs else False
        err = self.__static_checks()
        verbose_print(str(err))
        if err:
            raise Exception("Static Checks for the MatchRequest Failed, Reason: \n" + err)
        
        
    def __static_checks(self):
        
        if not self.db and not self.file:
            return EXCEP_DICT["NO_SRC"]
        
        if self.db and self.file:
            return EXCEP_DICT["SRC_VAGUE"]
        
        if not self.db:
            try:
                with open(self.file) as f:
                    json.load(f)
            except Exception as e:
                return EXCEP_DICT["FILE_R_EXEP"] + str(e)

        if not self.file and self.db not in SonicDBConfig.getDbList():
            return EXCEP_DICT["INV_DB"]
        
        if not self.table:
            return EXCEP_DICT["NO_TABLE"]
        
        if not isinstance(self.return_fields, list):
            return EXCEP_DICT["BAD_FORMAT_RE_FIELDS"]
        
        if not self.just_keys and self.return_fields:
            return EXCEP_DICT["JUST_KEYS_COMPAT"]
        
        if self.field and not self.value:
            return EXCEP_DICT["NO_VALUE"]
        
        verbose_print("MatchRequest Checks Passed")
        
        return ""
    
    def __str__(self):
        str = "----------------------- \n MatchRequest: \n"
        if self.db:
            str += "db:{} , ".format(self.db)
        if self.file:
            str += "file:{} , ".format(self.file) 
        if self.table:
            str += "table:{} , ".format(self.table)
        if self.key_pattern:
            str += "key_pattern:{} , ".format(self.key_pattern)
        if self.field:
            str += "field:{} , ".format(self.field)
        if self.value:
            str += "value:{} , ".format(self.value)
        if self.just_keys:
            str += "just_keys:True ,"
        else:
            str += "just_keys:False ,"
        if len(self.return_fields) > 0:
            str += "return_fields: " + ",".join(self.return_fields) + " "
        if self.ns:
            str += "namespace: ," + self.ns 
        if self.match_entire_list:
            str += "match_list: True ,"
        else:
            str += "match_list: False ,"
        return str
    
class SourceAdapter(ABC):
    """ Source Adaptor offers unified interface to Data Sources """
    
    def __init__(self):
        pass
    
    @abstractmethod
    def connect(self, db, ns):
        """ Return True for Success, False for failure """
        return False
    
    @abstractmethod
    def getKeys(self, db, table, key_pattern):
        return []
    
    @abstractmethod
    def get(self, db, key):
        return {}
    
    @abstractmethod
    def hget(self, db, key, field):
        return ""
    
    @abstractmethod
    def sep(self, db):
        return ""
        
class RedisSource(SourceAdapter):
    """ Concrete Adaptor Class for connecting to Redis Data Sources """
    
    def __init__(self):
        self.conn = None 
        
    def connect(self, db, ns):
        try:
            self.conn = SonicV2Connector(namespace=ns, host="127.0.0.1")
            self.conn.connect(db)
        except Exception as e:
            verbose_print("RedisSource: Connection Failed\n" + str(e))
            return False
        return True
    
    def sep(self, db):
        return self.conn.get_db_separator(db)
       
    def getKeys(self, db, table, key_pattern):       
        return self.conn.keys(db, table + self.sep(db) + key_pattern)
    
    def get(self, db, key):
        return self.conn.get_all(db, key)
     
    def hget(self, db, key, field):
        return self.conn.get(db, key, field)

class JsonSource(SourceAdapter):
    """ Concrete Adaptor Class for connecting to JSON Data Sources """
    
    def __init__(self):
        self.json_data = None
    
    def connect(self, db, ns):
        try:
            with open(db) as f:
                self.json_data = json.load(f)
        except Exception as e:
            verbose_print("JsonSource: Loading the JSON file failed" + str(e))
            return False
        return True
    
    def sep(self, db):
        return SonicDBConfig.getSeparator("CONFIG_DB")
    
    def getKeys(self, db, table, key_pattern):
        if table not in self.json_data:
            return []
        # https://docs.python.org/3.7/library/fnmatch.html
        kp = key_pattern.replace("[^", "[!")
        kys = fnmatch.filter(self.json_data[table].keys(), kp)
        return [table+self.sep(db)+ky for ky in kys]
    
    def get(self, db, key):
        sep = self.sep(db)
        table, key = key.split(sep, 1)
        return self.json_data.get(table, {}).get(key, {})
            
    def hget(self, db, key, field):
        sep = self.sep(db)
        table, key = key.split(sep, 1)
        return self.json_data.get(table, "").get(key, "").get(field, "")
                        
class MatchEngine:
    """ Pass in a MatchRequest, to fetch the Matched dump from the Data sources """
    
    def __get_source_adapter(self, req):
        src = None
        d_src = ""
        if req.db:
            d_src = req.db
            src = RedisSource()
        else:
            d_src = req.file
            src = JsonSource()
        return d_src, src
    
    def __create_template(self):
        return {"error" : "", "keys" : [], "return_values" : {}}
    
    def __display_error(self, err):
        template = self.__create_template()
        template['error'] = err
        verbose_print("MatchEngine: \n" + template['error'])
        return template
    
    def __filter_out_keys(self, src, req, all_matched_keys):
        # TODO: Custom Callbacks for Complex Matching Criteria
        if not req.field:
            return all_matched_keys
        
        filtered_keys = []
        for key in all_matched_keys:
            f_values = src.hget(req.db, key, req.field)
            if "," in f_values and not req.match_entire_list:
                f_value = f_values.split(",")
            else:
                f_value = [f_values]
            if req.value in f_value:
                filtered_keys.append(key)
        return filtered_keys
        
    def __fill_template(self, src, req, filtered_keys, template):
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
        
    def fetch(self, req):
        """ Given a request obj, find its match in the data source provided """
        if not isinstance(req, MatchRequest):
            return self.__display_error(EXCEP_DICT["INV_REQ"])
        
        verbose_print(str(req))
        
        if not req.key_pattern:
            return self.__display_error(EXCEP_DICT["NO_KEY"])
        
        d_src, src = self.__get_source_adapter(req)
        if not src.connect(d_src, req.ns):
            return self.__display_error(EXCEP_DICT["CONN_ERR"])
        
        template = self.__create_template()
        all_matched_keys = src.getKeys(req.db, req.table, req.key_pattern)
        if not all_matched_keys:
            return self.__display_error(EXCEP_DICT["NO_MATCHES"])
        
        filtered_keys = self.__filter_out_keys(src, req, all_matched_keys)
        verbose_print("Filtered Keys:" + str(filtered_keys))
        if not filtered_keys:
            return self.__display_error(EXCEP_DICT["NO_ENTRIES"])
        return self.__fill_template(src, req, filtered_keys, template)

