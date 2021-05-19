import os
import sys
import pytest
from unittest import mock, TestCase

from click.testing import CliRunner
from dump.main import state
from utilities_common.db import Db
# from importlib import reload

from ..mock_tables import dbconnector

# >>> a = SonicV2Connector(host="127.0.0.1")
# >>>
# >>>
# >>> a.connect("ASIC_DB")
# >>>
# >>>
# >>> a.hexists("ASIC_DB", "VIDTORID", "0xcc")
# False
# >>> a.hexists("ASIC_DB", "VIDTORID", "oid:0x1a0000000005a0")
# True
# >>> help(a0
# ... help(a0
# KeyboardInterrupt
# >>> help(a)
# 
# >>>
# >>> a.get("ASIC_DB", "VIDTORID", "oid:0x1a0000000005a0")
# 'oid:0x270000001a'
# >>>
# >>>


class TestDumpState(object):
        
    def test_key_map_filtering(self):
        os.environ['UTILITIES_UNIT_TESTING'] = "1"
        
        runner = CliRunner()
        db = Db()
        result = runner.invoke(state, ["port", "Ethernet0"], obj=db)
        print(result.output, result.exit_code, result.exception)
        assert 1 == 0