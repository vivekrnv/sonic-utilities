
from abc import ABC, abstractmethod

class Executor(ABC):
    
    ARG_NAME = "id" # Args Description
    
    @abstractmethod
    def execute(self):
        pass
    
    @abstractmethod
    def get_all_args(self):
        pass