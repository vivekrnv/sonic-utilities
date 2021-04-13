import re
from swsscommon.swsscommon import SonicDBConfig, DBConnector, Table

class RedisMatchRequest:
    
    def __init__(self):
        self.table = None
        self.redis_key = "*"
        self.hash_key = None
        self.value = None
        self.is_list = False
        self.return_keys = []
        self.db = None
        self.dump = True
    
    # Static Checks
    def validate(self):

        if not self.table:
            return "Should give a Table Name to match", False
        
        if not self.dump and len(return_keys) == 0:
            return "Either the dump or the return_keys has to be set", False
        
        if self.hash_key and self.redis_key != "*":
            return "When Hash Key is set, Redis Key can only be wildcard", False
        
        if not(self.value):
            return "Should be given something in order to match against", False
        
        if not(self.db):
            return "DB can't be None", False
        
        if self.hash_key is None:
            self.redis_key = "*"
        
        return None, True
    
class RedisMatchEngine:
    
    # Given a request obj, find its match in the redis
    def fetch(self, request_json):
    
        err = self.__arg_check(request_json)
        if err:
            return err
        
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
    
    def __arg_check(self, request_json):
        
        err_temp = self.__return_template(True, None)        
        if not isinstance(request_json, RedisMatchRequest):
            err_temp['error'] = "{}: Argument should be of type RedisMatchRequest".format(self.__class__.__name__)
            return err_temp
        
        err_str, valid = request_json.validate()
        if not(valid):
            err_temp['error'] = "{}: ".format(self.__class__.__name__) + err_str
            return err_temp
                 
        if request_json.db not in SonicDBConfig.getDbList():
            err_temp['error'] = "{}: Should give a Valid Redis DB to match".format(self.__class__.__name__)
            return err_temp
        
        #TODO: Add remaining Checks
        return None
    
    def __return_template(self, err=False, params=None):

        template = dict()
        template['status'] = 0
        template['error'] = ""
        if err:
            template['error'] = -1
            return template
        if params.dump:
            template['dump'] = dict()
        template['return_keys'] = dict()
        for val in params.return_keys:
            template['return_keys'][val] = ""
        
        return template
            
            


