import re, json, os
from swsscommon.swsscommon import SonicDBConfig, DBConnector, Table, SonicV2Connector

error_dict  = {
    "INV_REQ": "Argument should be of type MatchRequest",
    "INV_DB": "DB provided is not valid",
    "INV_JSON": "Not a properly formatted JSON file",
    "INV_TABLE": "Table is not present in the Source (db or file) provided",
    "NO_FILE": "JSON File not found",
    "NO_SRC": "Either one of db or file in the request should be non-empty",
    "NO_KEY": "'key_regex' cannot be empty",
    "NO_TABLE": "No 'table' name provided",
    "NO_VALUE" : "Field is provided, but no value is provided to compare with", 
    "SRC_VAGUE": "Only one of db or file should be provided"
}
        

class MatchRequest:
    def __init__(self):
        self.table = None
        self.key_regex = ".*"
        self.field = None
        self.value = None
        self.return_fields = []
        self.db = ""
        self.file = ""
        self.just_keys = True
    
    
class MatchEngine:
    
    def __ret_template(self):
        return {"error" : "", "keys" : [], "return_fields" : []}
    
     # Static Checks
    def validate_request(self, req):
        
        if not isinstance(req, MatchRequest):
            return error_dict["INV_REQ"]
            
        if not(req.db) and not(req.file):
            return error_dict["NO_SRC"]
        
        if req.db and req.file:
            return error_dict["SRC_VAGUE"]
        
        if not req.db and os.path.exists(req.file):
            try:
                with open(req.file) as f:
                    json.loads(req.file)
            except ValueError as e:
                return error_dict["INV_JSON"]
        elif not req.db:
            return error_dict["NO_FILE"]
        
        if req.db not in SonicV2Connector().get_db_list():
            return error_dict["INV_DB"]
        
        if not req.table:
            return error_dict["NO_TABLE"]
        
        if not req.key_regex:
            return error_dict["NO_KEY"]
        
        if req.field and not req.value:
            return error_dict["NO_VALUE"]
        
        return ""
    
    # Given a request obj, find its match in the redis
    def fetch(self, request_json):
        template = self.__ret_template()
        template['error']  = self.validate_request(request_json)
        if template['error']:
            return template
        
        err, dump = self.__launch(request_json)
        if err:
            return err
        
        return self.__fill(request_json, dump)
        
    
    def __launch(self, request_json):
        
        err_temp = self.__return_template(True, None)
        
        db = DBConnector(request_json.db, 0)
        tbl = Table(db, request_json.table)
        redis_keys = tbl.getKeys()
        
        if len(redis_keys) == 0:
            err_temp['error'] = "{}: No Keys Found for table {} in DB {}".format(self.__class__.__name__, request_json.table, request_json.db)
            return err_temp, None
        
        if request_json.hash_key is None:
            err, dump = self.__search_redis_keys(request_json, redis_keys, tbl)
            if err:
                err_temp['error'] = err
                return err_temp, None
            return None, dump
        else:
            err, dump = self.__search_redis_hash(request_json, redis_keys, tbl)
            if err:
                err_temp['error'] = err
                return err_temp, None
            return None, dump

    def __search_redis_hash(self, request_json, redis_keys, tbl):
        
        dump = dict()
        for redis_key in redis_keys:
            redis_response = tbl.get(redis_key)
            if redis_response[0]:
                temp = dict(redis_response[1])
                if request_json.hash_key in temp and re.match(request_json.value, temp[request_json.hash_key]):
                    dump[request_json.table+SonicDBConfig.getSeparator(request_json.db)+redis_key] = dict(redis_response[1])
                    return None, dump
        
        return "{}: Nothing Matched".format(self.__class__.__name__), None
       
              
    def __search_redis_keys(self, request_json, redis_keys, tbl):
        
        dump = dict()
        
        if request_json.value in redis_keys:
            redis_response = tbl.get(request_json.value)
            if redis_response[0]:
                dump[request_json.table+SonicDBConfig.getSeparator(request_json.db)+request_json.value] = dict(redis_response[1])
                return None, dump
            else:
                err_str = "{}: Key {} not found for table {} in DB {}".format(self.__class__.__name__, request_json.value, request_json.table, request_json.db)
                return err_str, None
            
        # Case which handles Regex Match in redis_keys. Only the first match is returned
        for redis_key in redis_keys:
            if re.match(request_json.value, redis_key):
                redis_response = tbl.get(request_json.value)
                if redis_response[0]:
                    dump[request_json.table+SonicDBConfig.getSeparator(request_json.db)+request_json.value] = dict(redis_response[1])
                    return None, dump
        
        return "{}: Nothing Matched".format(self.__class__.__name__), None
        
    
    def __fill(self, request_json, dump):
        ret_match = self.__return_template(False, request_json)
        if 'dump' in ret_match:
            ret_match['dump'] = dump
        
        for params in request_json.return_keys:
            for redis_key in dump.keys():
                if params in dump[redis_key]:
                    ret_match['return_keys'][params] = dump[redis_key][params]
                         
        return ret_match
            
    
    def __return_template():
        
        return template
            
            


