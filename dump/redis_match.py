import re
from swsscommon.swsscommon import SonicDBConfig, DBConnector, Table

class RedisMatchRequest:
    
    def __init__(self):
        self.table = None
        self.redis_key = None
        self.key = None
        self.value = None
        self.is_list = False
        self.return_keys = []
        self.db = None
        self.dump = True


class RedisMatchEngine:
    # Given a request obj, find the match in the redis
    
    def fetch(self, request_json):
        err = self.__arg_check(request_json)
        if not(err):
            return err
        
        dump = dict()
        err = self.__launch(request_json, dump)
        if not(err):
            return err
        return self.__fill(request_json, dump)
        
    
    def __launch(self, request_json, dump):
        
        err_temp = self.__return_template(True, None)
        
        db = DBConnector(request_json.db, 0)
        tbl = Table(db, request_json.table)
        redis_keys = tbl.getKeys()
        
        if len(redis_keys) == 0:
            err_temp['error'] = "{}: No Keys Found for table {} in DB {}".format(self.__class__.__name__, request_json.table, request_json.db)
            return err_temp
        
        if request_json.key is None:
            err = self.__search_redis_key(request_json, redis_keys, tbl, dump)
            if not(err):
                err_temp['error'] = err
                return err_temp
        else:
            err = self.__search_redis_hash_key(request_json, redis_keys, tbl, dump)
            if not(err):
                err_temp['error'] = err
                return err_temp
            
        return None 

    def __search_redis_hash_key(self, request_json, redis_keys, tbl, dump):
        
        for redis_key in redis_keys:
            redis_response = tbl.get(request_json.value)
            if redis_response[0]:
                temp = dict(redis_response[1])
                if key in temp and re.match(request_json.value, temp[key]):
                    dump[request_json.table+SonicDBConfig.getSeparator(db)+redis_key] = dict(redis_response[1])
                    return None
                else:
                    continue
        
        return "{}: Nothing Matched".format(self.__class__.__name__)
       
              
    def __search_redis_key(self, request_json, redis_keys, tbl, dump):
        
        if request_json.value in redis_keys:
            redis_response = tbl.get(request_json.value)
            if redis_response[0]:
                dump[request_json.table+SonicDBConfig.getSeparator(db)+request_json.value] = dict(redis_response[1])
                return None
            else:
                err_str = "{}: Key {} not found for table {} in DB {}".format(self.__class__.__name__, request_json.value, request_json.table, request_json.db)
                return err_str
        
        for redis_key in redis_keys:
            if re.match(request_json.value, redis_key):
                redis_response = tbl.get(request_json.value)
                if redis_response[0]:
                    dump[request_json.table+SonicDBConfig.getSeparator(db)+request_json.value] = dict(redis_response[1])
                    return None
        
        return "{}: Nothing Matched".format(self.__class__.__name__)
        

    
    def __fill(self, request_json, dump):
        ret_match = self.__return_template(False, request_json)
        if 'dump' in ret_match:
            ret_match['dump'] = dump
        
        for params in request_json.return_keys:
            for redis_key in dump.keys():
                if params in dump[redis_key]:
                    ret_match['return_match'][params] = dump[redis_key][params]
                         
        return ret_match
    
    def __arg_check(self, request_json):
        
        err_temp = self.__return_template(True, None)
        if not isinstance(request_json, RedisMatchRequest):
            err_temp['error'] = "{}: Argument should be of type RedisMatchRequest".format(self.__class__.__name__)
            return err_temp
        
        if not(self.table):
            err_temp['error'] = "{}: Should give a Table Name to match".format(self.__class__.__name__)
            return err_temp
        
        self.dbList = SonicDBConfig.getDbList()
        if not(request_json.db) or request_json.db not in self.dbList:
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
            
            


