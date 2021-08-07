import os
import sys
import pytest
import pyfakefs
from unittest import mock 
from pyfakefs.fake_filesystem_unittest import Patcher
from utilities_common.general import load_module_from_source

from .mock_tables import dbconnector

test_path = os.path.dirname(os.path.abspath(__file__))
modules_path = os.path.dirname(test_path)
scripts_path = os.path.join(modules_path, 'scripts')
sys.path.insert(0, modules_path)

# Load the file under test
script_path = os.path.join(scripts_path, 'coredump_gen_handler')
cdump_handle = load_module_from_source('coredump_gen_handler', script_path)