import re

class RedisSingleton:
    """
    Introduced to modify/check Redis DB's data outside of the scripts
    Usage: Clear and Set the state of the mock before every test case
    """
    __instance = None
        
    @staticmethod 
    def getInstance():
       """ Static access method. """
       if RedisSingleton.__instance == None:
          RedisSingleton()
       return RedisSingleton.__instance
    
    @staticmethod
    def clearState():
        """ Clear the Redis State """
        if RedisSingleton.__instance != None:
            RedisSingleton.__instance.data.clear()
            
    def __init__(self):
        if RedisSingleton.__instance != None:
            raise Exception("This class is a singleton!")
        else:
            self.data = dict()
            RedisSingleton.__instance = self
              
class MockConn(object):
    """ 
    SonicV2Connector Mock for the usecases to verify/modify the Redis State outside 
        of the scope of the connector class 
    """
    def __init__(self, host):
        self.redis = RedisSingleton.getInstance()

    def connect(self, db_name):
        if db_name not in self.redis.data:
            self.redis.data[db_name] = {}

    def get(self, db_name, key, field):
        return self.redis.data.get(db_name, {}).get(key, {}).get(field, "")

    def keys(self, db_name, pattern):
        pattern = re.escape(pattern)
        pattern = pattern.replace("\\*", ".*")
        filtered_keys = []
        all_keys = self.redis.data[db_name].keys()
        for key in all_keys:
            if re.match(pattern, key):
                filtered_keys.append(key)
        return filtered_keys        
                
    def get_all(self, db_name, key):
        return self.redis.data.get(db_name, {}).get(key, {})
    
    def set(self, db_name, key, field, value, blocking=True):
        if key not in self.redis.data[db_name]:
            self.redis.data[db_name][key] = {}
        self.redis.data[db_name][key][field] = value
    
    def hmset(self, db_name, key, hash):
        self.redis.data[db_name][key] = hash
    
    def hexists(self, db_name, key, field): 
        if key in self.redis.data[db_name]:
            return True
        else:
            return False
        
    def exists(self, db_name, key):
        if key in self.redis.data[db_name]:
            return True
        else:
            return False
    
    def get_redis_client(self, db_name):
        return MockClient(db_name)
    
class MockClient(object):
    def __init__(self, db_name):
        self.redis = RedisSingleton.getInstance()
        self.db_name = db_name
    
    def hdel(self, key, field):
        try:
            del self.redis.data[self.db_name][key][field]
        except:
            pass
    
    def hset(self, key, field, value):
        try:
           self.redis.data[self.db_name][key][field] = value
        except:
            pass