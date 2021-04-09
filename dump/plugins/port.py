
from .executor import Executor

class Port(Executor):
    
    def __init__(self):
        self.RMEngine = RedisMatchEngine()
       
    def execute(self, params_dict):
        return None