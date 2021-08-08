import os
import sys
import pyfakefs 
import unittest
from pyfakefs.fake_filesystem_unittest import Patcher
from swsscommon import swsscommon
from .shared_state_mock import RedisSingleton, MockConn
from utilities_common.general import load_module_from_source

# Mock the SonicV2Connector
swsscommon.SonicV2Connector = MockConn

curr_test_path = os.path.abspath(os.path.join(os.path.abspath(__file__), "../"))
test_dir_path = os.path.dirname(curr_test_path)
modules_path = os.path.dirname(test_dir_path)
scripts_path = os.path.join(modules_path, 'scripts')
sys.path.insert(0, modules_path)

# Load the file under test
script_path = os.path.join(scripts_path, 'coredump_gen_handler')
cdump_handle = load_module_from_source('coredump_gen_handler', script_path)

# Mock Handle to the data inside the Redis
RedisHandle = RedisSingleton.getInstance()