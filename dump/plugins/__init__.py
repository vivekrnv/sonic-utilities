import os
import sys
import pkgutil

from .executor import Executor

child_classes = {}
pkg_dir = os.path.dirname(__file__)
    
# import child classes automatically                      
for (module_loader, name, ispkg) in pkgutil.iter_modules([pkg_dir]):
    importlib.import_module('.' + name, __package__)

# Classes inheriting Executor
child_classes = {cls.__name__: cls for cls in Executor.__subclasses__()}



