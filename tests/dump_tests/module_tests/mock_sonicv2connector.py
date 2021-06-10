import json, re, os
from utilities_common.constants import DEFAULT_NAMESPACE

class MockSonicV2Connector():
    def __init__(self, dedicated_dbs, namespace=DEFAULT_NAMESPACE):
        if namespace != DEFAULT_NAMESPACE:
            raise "This Mock doesn't support multi-asic configuration"
        self.db = None
        self.db_name_connect_to = None
        self.dedicated_dbs = dedicated_dbs
        db_config_path = os.path.join(os.path.dirname(__file__),"../../mock_tables/database_config.json")
        with open(db_config_path) as f:
            self.db_cfg = json.load(f)
    
    def connect(self, db_name, retry=False):
        if db_name not in self.dedicated_dbs:
            raise Exception("{} not found. Available db's: {}".fomrat(db_name, self.dedicated_dbs.keys()))
        try:
            with open(self.dedicated_dbs[db_name]) as f:
                self.db = json.load(f)
                self.db_name_connect_to = db_name  
        except BaseException as e:
            raise "Connection Failure" + str(e)
    
    def get_db_separator(self, db_name):
        return self.db_cfg["DATABASES"][db_name]["separator"]
    
    def keys(self, db_name, pattern):
        if not self.db:
            raise "MockDB Not Connected"
        if self.db_name_connect_to != db_name:
            raise "Failed to find {} in the MockDB".format(db_name)
        
        pattern = re.escape(pattern)
        pattern = pattern.replace("\\*", ".*")
        filtered_keys = []
        all_keys = self.db.keys()
        for key in all_keys:
            if re.match(pattern, key):
                filtered_keys.append(key)
        return filtered_keys
    
    def get_all(self, db_name, key):
        if not self.db:
            raise "MockDB Not Connected"
        if self.db_name_connect_to != db_name:
            raise "Failed to find {} in the MockDB".format(db_name)
        if key not in self.db:
            return {}
        return self.db[key]

    def get(self, db_name, key, field):
        if not self.db:
            raise "MockDB Not Connected"
        if self.db_name_connect_to != db_name:
            raise "Failed to find {} in the MockDB".format(db_name)
        if key not in self.db or field not in self.db[key]:
            return ""
        return self.db[key][field]
    
    def hexists(self, db_name, key, field):
        if not self.db:
            raise "MockDB Not Connected"
        if self.db_name_connect_to != db_name:
            raise "Failed to find {} in the MockDB".format(db_name)
        if key not in self.db or field not in self.db[key]:
            return False
        else:
            return True
