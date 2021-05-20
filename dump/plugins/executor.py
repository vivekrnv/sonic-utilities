
from abc import ABC, abstractmethod

class Executor(ABC):
    
    ARG_NAME = "id" # Arg Identifier
    CONFIG_FILE = "" # Path to config file, if any
    
    @abstractmethod
    def execute(self, params):
        pass
    
    @abstractmethod
    def get_all_args(self, ns):
        pass
    
