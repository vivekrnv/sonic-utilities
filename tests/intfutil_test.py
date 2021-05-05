import os
import sys
from click.testing import CliRunner
from unittest import TestCase
import subprocess

import show.main as show

root_path = os.path.dirname(os.path.abspath(__file__))
modules_path = os.path.dirname(root_path)
scripts_path = os.path.join(modules_path, "scripts")

show_interface_status_output="""\
      Interface            Lanes    Speed    MTU    FEC      Alias             Vlan    Oper    Admin             Type    Asym PFC
---------------  ---------------  -------  -----  -----  ---------  ---------------  ------  -------  ---------------  ----------
      Ethernet0                0      25G   9100     rs  Ethernet0           routed    down       up  QSFP28 or later         off
     Ethernet32      13,14,15,16      40G   9100     rs       etp9  PortChannel1001      up       up              N/A         off
    Ethernet112      93,94,95,96      40G   9100     rs      etp29  PortChannel0001      up       up              N/A         off
    Ethernet116      89,90,91,92      40G   9100     rs      etp30  PortChannel0002      up       up              N/A         off
    Ethernet120  101,102,103,104      40G   9100     rs      etp31  PortChannel0003      up       up              N/A         off
    Ethernet124     97,98,99,100      40G   9100     rs      etp32  PortChannel0004      up       up              N/A         off
PortChannel0001              N/A      40G   9100    N/A        N/A           routed    down       up              N/A         N/A
PortChannel0002              N/A      40G   9100    N/A        N/A           routed      up       up              N/A         N/A
PortChannel0003              N/A      40G   9100    N/A        N/A           routed      up       up              N/A         N/A
PortChannel0004              N/A      40G   9100    N/A        N/A           routed      up       up              N/A         N/A
PortChannel1001              N/A      40G   9100    N/A        N/A            trunk     N/A      N/A              N/A         N/A
"""

show_interface_status_Ethernet32_output="""\
  Interface        Lanes    Speed    MTU    FEC    Alias             Vlan    Oper    Admin    Type    Asym PFC
-----------  -----------  -------  -----  -----  -------  ---------------  ------  -------  ------  ----------
 Ethernet32  13,14,15,16      40G   9100     rs     etp9  PortChannel1001      up       up     N/A         off
"""

show_interface_description_output="""\
  Interface    Oper    Admin      Alias           Description
-----------  ------  -------  ---------  --------------------
  Ethernet0    down       up  Ethernet0  ARISTA01T2:Ethernet1
 Ethernet32      up       up       etp9         Servers7:eth0
Ethernet112      up       up      etp29  ARISTA01T1:Ethernet1
Ethernet116      up       up      etp30  ARISTA02T1:Ethernet1
Ethernet120      up       up      etp31  ARISTA03T1:Ethernet1
Ethernet124      up       up      etp32  ARISTA04T1:Ethernet1
"""

show_interface_description_Ethernet0_output="""\
  Interface    Oper    Admin      Alias           Description
-----------  ------  -------  ---------  --------------------
  Ethernet0    down       up  Ethernet0  ARISTA01T2:Ethernet1
"""

show_interface_description_Ethernet0_verbose_output="""\
Running command: intfutil -c description -i Ethernet0
  Interface    Oper    Admin      Alias           Description
-----------  ------  -------  ---------  --------------------
  Ethernet0    down       up  Ethernet0  ARISTA01T2:Ethernet1
"""

show_interface_description_eth9_output="""\
  Interface    Oper    Admin    Alias    Description
-----------  ------  -------  -------  -------------
 Ethernet32      up       up     etp9  Servers7:eth0
"""

class TestIntfutil(TestCase):
    @classmethod
    def setup_class(cls):
        print("SETUP")
        os.environ["PATH"] += os.pathsep + scripts_path
        os.environ["UTILITIES_UNIT_TESTING"] = "2"

    def setUp(self):
        self.runner = CliRunner()


    # Test 'show interfaces status' / 'intfutil status'
    def test_intf_status(self):
        # Test 'show interfaces status'
        result = self.runner.invoke(show.cli.commands["interfaces"].commands["status"], [])
        print(result.exit_code)
        print(result.output)
        assert result.exit_code == 0
        assert result.output == show_interface_status_output

        # Test 'intfutil status'
        output = subprocess.check_output('intfutil -c status', stderr=subprocess.STDOUT, shell=True, text=True)
        print(output)
        assert result.output == show_interface_status_output

    # Test 'show interfaces status --verbose'
    def test_intf_status_verbose(self):
        result = self.runner.invoke(show.cli.commands["interfaces"].commands["status"], ["--verbose"])
        assert result.exit_code == 0
        print(result.exit_code)
        print(result.output)
        expected_output = "Running command: intfutil -c status -d all"
        assert result.output.split('\n')[0] == expected_output

    def test_intf_status_Ethernet32(self):
        result = self.runner.invoke(show.cli.commands["interfaces"].commands["status"], ["Ethernet32"])
        print(result.exit_code)
        print(result.output)
        assert result.exit_code == 0
        assert result.output == show_interface_status_Ethernet32_output

    def test_intf_status_etp9(self):
        os.environ["SONIC_CLI_IFACE_MODE"] = "alias"
        result = self.runner.invoke(show.cli.commands["interfaces"].commands["status"], ["etp9"])
        os.environ["SONIC_CLI_IFACE_MODE"] = "default"
        print(result.exit_code)
        print(result.output)
        assert result.exit_code == 0
        assert result.output == show_interface_status_Ethernet32_output

    def test_show_interfaces_description(self):
        result = self.runner.invoke(show.cli.commands["interfaces"].commands["description"], [])
        print(result.exit_code)
        print(result.output)
        assert result.exit_code == 0
        assert result.output == show_interface_description_output

    def test_show_interfaces_description_Ethernet0(self):
        result = self.runner.invoke(show.cli.commands["interfaces"].commands["description"], ["Ethernet0"])
        print(result.exit_code)
        print(result.output)
        assert result.exit_code == 0
        assert result.output == show_interface_description_Ethernet0_output

    def test_show_interfaces_description_etp9_in_alias_mode(self):
        os.environ["SONIC_CLI_IFACE_MODE"] = "alias"
        result = self.runner.invoke(show.cli.commands["interfaces"].commands["description"], ["etp9"])
        os.environ["SONIC_CLI_IFACE_MODE"] = "default"
        print(result.exit_code)
        print(result.output)
        assert result.exit_code == 0
        assert result.output == show_interface_description_eth9_output

    def test_show_interfaces_description_etp33_in_alias_mode(self):
        os.environ["SONIC_CLI_IFACE_MODE"] = "alias"
        result = self.runner.invoke(show.cli.commands["interfaces"].commands["description"], ["etp33"])
        os.environ["SONIC_CLI_IFACE_MODE"] = "default"
        print(result.exit_code)
        print(result.output)
        assert result.exit_code != 0
        assert "Error: cannot find interface name for alias etp33" in result.output

    def test_show_interfaces_description_Ethernet0_verbose(self):
        result = self.runner.invoke(show.cli.commands["interfaces"].commands["description"], ["Ethernet0", "--verbose"])
        print(result.exit_code)
        print(result.output)
        assert result.exit_code == 0
        assert result.output == show_interface_description_Ethernet0_verbose_output

    # Test 'show subinterfaces status' / 'intfutil status subport'
    def test_subintf_status(self):
        # Test 'show subinterfaces status'
        result = self.runner.invoke(show.cli.commands["subinterfaces"].commands["status"], [])
        print(result.output, file=sys.stderr)
        expected_output = (
            "Sub port interface    Speed    MTU    Vlan    Admin                  Type\n"
          "--------------------  -------  -----  ------  -------  --------------------\n"
          "        Ethernet0.10      25G   9100      10       up  802.1q-encapsulation"
        )
        self.assertEqual(result.output.strip(), expected_output)

        # Test 'intfutil status subport'
        output = subprocess.check_output('intfutil -c status -i subport', stderr=subprocess.STDOUT, shell=True, text=True)
        print(output, file=sys.stderr)
        self.assertEqual(output.strip(), expected_output)

    # Test 'show subinterfaces status --verbose'
    def test_subintf_status_verbose(self):
        result = self.runner.invoke(show.cli.commands["subinterfaces"].commands["status"], ["--verbose"])
        print(result.output, file=sys.stderr)
        expected_output = "Command: intfutil -c status -i subport"
        self.assertEqual(result.output.split('\n')[0], expected_output)


    # Test single sub interface status
    def test_single_subintf_status(self):
        # Test 'show subinterfaces status Ethernet0.10'
        result = self.runner.invoke(show.cli.commands["subinterfaces"].commands["status"], ["Ethernet0.10"])
        print(result.output, file=sys.stderr)
        expected_output = (
            "Sub port interface    Speed    MTU    Vlan    Admin                  Type\n"
          "--------------------  -------  -----  ------  -------  --------------------\n"
          "        Ethernet0.10      25G   9100      10       up  802.1q-encapsulation"
        )
        self.assertEqual(result.output.strip(), expected_output)

        # Test 'intfutil status Ethernet0.10'
        output = subprocess.check_output('intfutil -c status -i Ethernet0.10', stderr=subprocess.STDOUT, shell=True, text=True)
        print(output, file=sys.stderr)
        self.assertEqual(output.strip(), expected_output)

    # Test '--verbose' status of single sub interface
    def test_single_subintf_status_verbose(self):
        result = self.runner.invoke(show.cli.commands["subinterfaces"].commands["status"], ["Ethernet0.10", "--verbose"])
        print(result.output, file=sys.stderr)
        expected_output = "Command: intfutil -c status -i Ethernet0.10"
        self.assertEqual(result.output.split('\n')[0], expected_output)


    # Test status of single sub interface in alias naming mode
    def test_single_subintf_status_alias_mode(self):
        os.environ["SONIC_CLI_IFACE_MODE"] = "alias"

        result = self.runner.invoke(show.cli.commands["subinterfaces"].commands["status"], ["etp1.10"])
        print(result.output, file=sys.stderr)
        expected_output = (
            "Sub port interface    Speed    MTU    Vlan    Admin                  Type\n"
          "--------------------  -------  -----  ------  -------  --------------------\n"
          "        Ethernet0.10      25G   9100      10       up  802.1q-encapsulation"
        )
        self.assertEqual(result.output.strip(), expected_output)

        os.environ["SONIC_CLI_IFACE_MODE"] = "default"

    # Test '--verbose' status of single sub interface in alias naming mode
    def test_single_subintf_status_alias_mode_verbose(self):
        os.environ["SONIC_CLI_IFACE_MODE"] = "alias"

        result = self.runner.invoke(show.cli.commands["subinterfaces"].commands["status"], ["etp1.10", "--verbose"])
        print(result.output, file=sys.stderr)
        expected_output = "Command: intfutil -c status -i Ethernet0.10"
        self.assertEqual(result.output.split('\n')[0], expected_output)

        os.environ["SONIC_CLI_IFACE_MODE"] = "default"

    @classmethod
    def teardown_class(cls):
        print("TEARDOWN")
        os.environ["PATH"] = os.pathsep.join(os.environ["PATH"].split(os.pathsep)[:-1])
        os.environ["UTILITIES_UNIT_TESTING"] = "0"
