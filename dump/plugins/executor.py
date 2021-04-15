
from abc import ABC, abstractmethod

class Executor(ABC):
    
    N_ARGS = 1  #Number of args
    ARGS = ("id") # Args Description
    
    @abstractmethod
    def execute(self):
        pass