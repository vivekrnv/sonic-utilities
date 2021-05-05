import importlib

from click.testing import CliRunner

from utilities_common.db import Db

show_feature_status_output="""\
Feature     State           AutoRestart     SetOwner
----------  --------------  --------------  ----------
bgp         enabled         enabled         local
database    always_enabled  always_enabled  local
dhcp_relay  enabled         enabled         kube
lldp        enabled         enabled         kube
nat         enabled         enabled         local
pmon        enabled         enabled         kube
radv        enabled         enabled         kube
restapi     disabled        enabled         local
sflow       disabled        enabled         local
snmp        enabled         enabled         kube
swss        enabled         enabled         local
syncd       enabled         enabled         local
teamd       enabled         enabled         local
telemetry   enabled         enabled         kube
"""

show_feature_status_output_with_remote_mgmt="""\
Feature     State           AutoRestart     SystemState    UpdateTime           ContainerId    Version       SetOwner    CurrentOwner    RemoteState
----------  --------------  --------------  -------------  -------------------  -------------  ------------  ----------  --------------  -------------
bgp         enabled         enabled                                                                          local
database    always_enabled  always_enabled                                                                   local
dhcp_relay  enabled         enabled                                                                          kube
lldp        enabled         enabled                                                                          kube
nat         enabled         enabled                                                                          local
pmon        enabled         enabled                                                                          kube
radv        enabled         enabled                                                                          kube
restapi     disabled        enabled                                                                          local
sflow       disabled        enabled                                                                          local
snmp        enabled         enabled         up             2020-11-12 23:32:56  aaaabbbbcccc   20201230.100  kube        kube            kube
swss        enabled         enabled                                                                          local
syncd       enabled         enabled                                                                          local
teamd       enabled         enabled                                                                          local
telemetry   enabled         enabled                                                                          kube
"""

show_feature_config_output="""\
Feature     State     AutoRestart
----------  --------  -------------
bgp         enabled   enabled
database    enabled   disabled
dhcp_relay  enabled   enabled
lldp        enabled   enabled
nat         enabled   enabled
pmon        enabled   enabled
radv        enabled   enabled
restapi     disabled  enabled
sflow       disabled  enabled
snmp        enabled   enabled
swss        enabled   enabled
syncd       enabled   enabled
teamd       enabled   enabled
telemetry   enabled   enabled
"""

show_feature_config_output_with_remote_mgmt="""\
Feature     State           AutoRestart     Owner
----------  --------------  --------------  -------
bgp         enabled         enabled         local
database    always_enabled  always_enabled  local
dhcp_relay  enabled         enabled         kube
lldp        enabled         enabled         kube
nat         enabled         enabled         local
pmon        enabled         enabled         kube
radv        enabled         enabled         kube
restapi     disabled        enabled         local
sflow       disabled        enabled         local
snmp        enabled         enabled         kube
swss        enabled         enabled         local
syncd       enabled         enabled         local
teamd       enabled         enabled         local
telemetry   enabled         enabled         kube
"""

show_feature_bgp_status_output="""\
Feature    State    AutoRestart    SetOwner
---------  -------  -------------  ----------
bgp        enabled  enabled        local
"""

show_feature_bgp_disabled_status_output="""\
Feature    State     AutoRestart    SetOwner
---------  --------  -------------  ----------
bgp        disabled  enabled        local
"""
show_feature_snmp_config_owner_output="""\
Feature    State    AutoRestart    Owner    fallback
---------  -------  -------------  -------  ----------
snmp       enabled  enabled        local    true
"""

show_feature_snmp_config_fallback_output="""\
Feature    State    AutoRestart    Owner    fallback
---------  -------  -------------  -------  ----------
snmp       enabled  enabled        kube     false
"""

show_feature_autorestart_output="""\
Feature     AutoRestart
----------  --------------
bgp         enabled
database    always_enabled
dhcp_relay  enabled
lldp        enabled
nat         enabled
pmon        enabled
radv        enabled
restapi     enabled
sflow       enabled
snmp        enabled
swss        enabled
syncd       enabled
teamd       enabled
telemetry   enabled
"""

show_feature_bgp_autorestart_output="""\
Feature    AutoRestart
---------  -------------
bgp        enabled
"""


show_feature_bgp_disabled_autorestart_output="""\
Feature    AutoRestart
---------  -------------
bgp        disabled
"""

show_feature_database_always_enabled_state_output="""\
Feature    State           AutoRestart     SetOwner
---------  --------------  --------------  ----------
database   always_enabled  always_enabled  local
"""

show_feature_database_always_enabled_autorestart_output="""\
Feature    AutoRestart
---------  --------------
database   always_enabled
"""
config_feature_bgp_inconsistent_state_output="""\
Feature 'bgp' state is not consistent across namespaces
"""
config_feature_bgp_inconsistent_autorestart_output="""\
Feature 'bgp' auto-restart is not consistent across namespaces
"""

class TestFeature(object):
    @classmethod
    def setup_class(cls):
        print("SETUP")

    def test_show_feature_status_no_kube_status(self, get_cmd_module):
        (config, show) = get_cmd_module
        runner = CliRunner()
        result = runner.invoke(show.cli.commands["feature"].commands["status"], [])
        print(result.exit_code)
        print(result.output)
        assert result.exit_code == 0
        assert result.output == show_feature_status_output

    def test_show_feature_status(self, get_cmd_module):
        (config, show) = get_cmd_module
        db = Db()
        dbconn = db.db
        for (key, val) in [("system_state", "up"), ("current_owner", "kube"),
                ("container_id", "aaaabbbbcccc"), ("update_time", "2020-11-12 23:32:56"),
                ("container_version", "20201230.100"), ("remote_state", "kube")]:
            dbconn.set(dbconn.STATE_DB, "FEATURE|snmp", key, val)
        runner = CliRunner()
        result = runner.invoke(show.cli.commands["feature"].commands["status"], ["snmp"], obj=db)
        print(result.exit_code)
        assert result.exit_code == 0

        result = runner.invoke(show.cli.commands["feature"].commands["status"], [], obj=db)
        print(result.exit_code)
        print(result.output)
        assert result.exit_code == 0
        assert result.output == show_feature_status_output_with_remote_mgmt

    def test_show_feature_config(self, get_cmd_module):
        (config, show) = get_cmd_module
        runner = CliRunner()
        result = runner.invoke(show.cli.commands["feature"].commands["config"], [])
        print(result.exit_code)
        print(result.output)
        assert result.exit_code == 0
        if "Owner" in result.output:
            assert result.output == show_feature_config_output_with_remote_mgmt
        else:
            assert result.output == show_feature_config_output

    def test_show_feature_status_abbrev_cmd(self, get_cmd_module):
        (config, show) = get_cmd_module
        runner = CliRunner()
        result = runner.invoke(show.cli.commands["feature"], ["st"])
        print(result.exit_code)
        print(result.output)
        assert result.exit_code == 0
        assert result.output == show_feature_status_output

    def test_show_bgp_feature_status(self, get_cmd_module):
        (config, show) = get_cmd_module
        runner = CliRunner()
        result = runner.invoke(show.cli.commands["feature"].commands["status"], ["bgp"])
        print(result.exit_code)
        print(result.output)
        assert result.exit_code == 0
        assert result.output == show_feature_bgp_status_output

    def test_show_unknown_feature_status(self, get_cmd_module):
        (config, show) = get_cmd_module
        runner = CliRunner()
        result = runner.invoke(show.cli.commands["feature"].commands["status"], ["foo"])
        print(result.exit_code)
        print(result.output)
        assert result.exit_code == 1

    def test_show_feature_autorestart(self, get_cmd_module):
        (config, show) = get_cmd_module
        runner = CliRunner()
        result = runner.invoke(show.cli.commands["feature"].commands["autorestart"], [])
        print(result.exit_code)
        print(result.output)
        assert result.exit_code == 0
        assert result.output == show_feature_autorestart_output

    def test_fail_autorestart(self, get_cmd_module):
        (config, show) = get_cmd_module
        runner = CliRunner()
        db = Db()

        # Try setting auto restart for non-existing feature
        result = runner.invoke(config.config.commands["feature"].commands["autorestart"], ["foo", "disabled"])
        print(result.exit_code)
        assert result.exit_code == 1

        # Delete Feature table
        db.cfgdb.delete_table("FEATURE")

        # Try setting auto restart when no FEATURE table
        result = runner.invoke(config.config.commands["feature"].commands["autorestart"], ["bgp", "disabled"], obj=db)
        print(result.exit_code)
        assert result.exit_code == 1


    def test_show_bgp_autorestart_status(self, get_cmd_module):
        (config, show) = get_cmd_module
        runner = CliRunner()
        result = runner.invoke(show.cli.commands["feature"].commands["autorestart"], ["bgp"])
        print(result.exit_code)
        print(result.output)
        assert result.exit_code == 0
        assert result.output == show_feature_bgp_autorestart_output

    def test_show_unknown_autorestart_status(self, get_cmd_module):
        (config, show) = get_cmd_module
        runner = CliRunner()
        result = runner.invoke(show.cli.commands["feature"].commands["autorestart"], ["foo"])
        print(result.exit_code)
        print(result.output)
        assert result.exit_code == 1

    def test_config_bgp_feature_state(self, get_cmd_module):
        (config, show) = get_cmd_module
        db = Db()
        runner = CliRunner()
        result = runner.invoke(config.config.commands["feature"].commands["state"], ["bgp", "disabled"], obj=db)
        print(result.exit_code)
        print(result.output)
        assert result.exit_code == 0
        result = runner.invoke(show.cli.commands["feature"].commands["status"], ["bgp"], obj=db)
        print(result.output)
        assert result.exit_code == 0
        assert result.output == show_feature_bgp_disabled_status_output

    def test_config_snmp_feature_owner(self, get_cmd_module):
        (config, show) = get_cmd_module
        db = Db()
        runner = CliRunner()
        result = runner.invoke(config.config.commands["feature"].commands["owner"], ["snmp", "local"], obj=db)
        print(result.exit_code)
        print(result.output)
        result = runner.invoke(config.config.commands["feature"].commands["fallback"], ["snmp", "on"], obj=db)
        print(result.exit_code)
        print(result.output)
        assert result.exit_code == 0

        result = runner.invoke(show.cli.commands["feature"].commands["config"], ["foo"], obj=db)
        print(result.exit_code)
        assert result.exit_code == 1

        result = runner.invoke(show.cli.commands["feature"].commands["config"], ["snmp"], obj=db)
        print(result.output)
        assert result.exit_code == 0
        assert result.output == show_feature_snmp_config_owner_output

    def test_config_unknown_feature_owner(self, get_cmd_module):
        (config, show) = get_cmd_module
        runner = CliRunner()
        result = runner.invoke(config.config.commands["feature"].commands["owner"], ["foo", "local"])
        print(result.exit_code)
        print(result.output)
        assert result.exit_code == 1

    def test_config_snmp_feature_fallback(self, get_cmd_module):
        (config, show) = get_cmd_module
        db = Db()
        runner = CliRunner()
        result = runner.invoke(config.config.commands["feature"].commands["fallback"], ["snmp", "off"], obj=db)
        print(result.exit_code)
        print(result.output)
        assert result.exit_code == 0
        result = runner.invoke(show.cli.commands["feature"].commands["config"], ["snmp"], obj=db)
        print(result.output)
        assert result.exit_code == 0
        assert result.output == show_feature_snmp_config_fallback_output

    def test_config_bgp_autorestart(self, get_cmd_module):
        (config, show) = get_cmd_module
        db = Db()
        runner = CliRunner()
        result = runner.invoke(config.config.commands["feature"].commands["autorestart"], ["bgp", "disabled"], obj=db)
        print(result.exit_code)
        print(result.output)
        assert result.exit_code == 0
        result = runner.invoke(show.cli.commands["feature"].commands["autorestart"], ["bgp"], obj=db)
        print(result.output)
        assert result.exit_code == 0
        assert result.output == show_feature_bgp_disabled_autorestart_output

    def test_config_database_feature_state(self, get_cmd_module):
        (config, show) = get_cmd_module
        db = Db()
        runner = CliRunner()
        result = runner.invoke(config.config.commands["feature"].commands["state"], ["database", "disabled"], obj=db)
        print(result.exit_code)
        print(result.output)
        result = runner.invoke(show.cli.commands["feature"].commands["status"], ["database"], obj=db)
        print(result.output)
        assert result.exit_code == 0
        assert result.output == show_feature_database_always_enabled_state_output
        result = runner.invoke(config.config.commands["feature"].commands["state"], ["database", "enabled"], obj=db)
        print(result.exit_code)
        print(result.output)
        result = runner.invoke(show.cli.commands["feature"].commands["status"], ["database"], obj=db)
        print(result.output)
        assert result.exit_code == 0
        assert result.output == show_feature_database_always_enabled_state_output

    def test_config_database_feature_autorestart(self, get_cmd_module):
        (config, show) = get_cmd_module
        db = Db()
        runner = CliRunner()
        result = runner.invoke(config.config.commands["feature"].commands["autorestart"], ["database", "disabled"], obj=db)
        print(result.exit_code)
        print(result.output)
        result = runner.invoke(show.cli.commands["feature"].commands["autorestart"], ["database"], obj=db)
        print(result.output)
        assert result.exit_code == 0
        assert result.output == show_feature_database_always_enabled_autorestart_output
        result = runner.invoke(config.config.commands["feature"].commands["autorestart"], ["database", "enabled"], obj=db)
        print(result.exit_code)
        print(result.output)
        result = runner.invoke(show.cli.commands["feature"].commands["autorestart"], ["database"], obj=db)
        print(result.output)
        assert result.exit_code == 0
        assert result.output == show_feature_database_always_enabled_autorestart_output

    def test_config_unknown_feature(self, get_cmd_module):
        (config, show) = get_cmd_module
        runner = CliRunner()
        result = runner.invoke(config.config.commands["feature"].commands['state'], ["foo", "enabled"])
        print(result.output)
        print(result.exit_code)
        assert result.exit_code == 1

    @classmethod
    def teardown_class(cls):
        print("TEARDOWN")

class TestFeatureMultiAsic(object):
    @classmethod
    def setup_class(cls):
        print("SETUP")

    def test_config_bgp_feature_inconsistent_state(self, get_cmd_module):
        from .mock_tables import dbconnector
        from .mock_tables import mock_multi_asic_3_asics
        importlib.reload(mock_multi_asic_3_asics)
        dbconnector.load_namespace_config()
        (config, show) = get_cmd_module
        db = Db()
        runner = CliRunner()
        result = runner.invoke(config.config.commands["feature"].commands["state"], ["bgp", "disabled"], obj=db)
        print(result.exit_code)
        print(result.output)
        assert result.exit_code == 1
        assert result.output == config_feature_bgp_inconsistent_state_output
        result = runner.invoke(config.config.commands["feature"].commands["state"], ["bgp", "enabled"], obj=db)
        print(result.exit_code)
        print(result.output)
        assert result.exit_code == 1
        assert result.output == config_feature_bgp_inconsistent_state_output

    def test_config_bgp_feature_inconsistent_autorestart(self, get_cmd_module):
        from .mock_tables import dbconnector
        from .mock_tables import mock_multi_asic_3_asics
        importlib.reload(mock_multi_asic_3_asics)
        dbconnector.load_namespace_config()
        (config, show) = get_cmd_module
        db = Db()
        runner = CliRunner()
        result = runner.invoke(config.config.commands["feature"].commands["autorestart"], ["bgp", "disabled"], obj=db)
        print(result.exit_code)
        print(result.output)
        assert result.exit_code == 1
        assert result.output == config_feature_bgp_inconsistent_autorestart_output
        result = runner.invoke(config.config.commands["feature"].commands["autorestart"], ["bgp", "enabled"], obj=db)
        print(result.exit_code)
        print(result.output)
        assert result.exit_code == 1
        assert result.output == config_feature_bgp_inconsistent_autorestart_output

    def test_config_bgp_feature_consistent_state(self, get_cmd_module):
        from .mock_tables import dbconnector
        from .mock_tables import mock_multi_asic
        importlib.reload(mock_multi_asic)
        dbconnector.load_namespace_config()
        (config, show) = get_cmd_module
        db = Db()
        runner = CliRunner()
        result = runner.invoke(config.config.commands["feature"].commands["state"], ["bgp", "disabled"], obj=db)
        print(result.exit_code)
        assert result.exit_code == 0
        result = runner.invoke(show.cli.commands["feature"].commands["status"], ["bgp"], obj=db)
        print(result.output)
        assert result.exit_code == 0
        assert result.output == show_feature_bgp_disabled_status_output
        result = runner.invoke(config.config.commands["feature"].commands["state"], ["bgp", "enabled"], obj=db)
        print(result.exit_code)
        print(result.output)
        assert result.exit_code == 0
        result = runner.invoke(show.cli.commands["feature"].commands["status"], ["bgp"], obj=db)
        print(result.output)
        assert result.exit_code == 0
        assert result.output == show_feature_bgp_status_output

    def test_config_bgp_feature_consistent_autorestart(self, get_cmd_module):
        from .mock_tables import dbconnector
        from .mock_tables import mock_multi_asic
        importlib.reload(mock_multi_asic)
        dbconnector.load_namespace_config()
        (config, show) = get_cmd_module
        db = Db()
        runner = CliRunner()
        result = runner.invoke(config.config.commands["feature"].commands["autorestart"], ["bgp", "disabled"], obj=db)
        print(result.exit_code)
        assert result.exit_code == 0
        result = runner.invoke(show.cli.commands["feature"].commands["autorestart"], ["bgp"], obj=db)
        print(result.output)
        print(result.exit_code)
        assert result.exit_code == 0
        assert result.output == show_feature_bgp_disabled_autorestart_output
        result = runner.invoke(config.config.commands["feature"].commands["autorestart"], ["bgp", "enabled"], obj=db)
        print(result.exit_code)
        assert result.exit_code == 0
        result = runner.invoke(show.cli.commands["feature"].commands["autorestart"], ["bgp"], obj=db)
        print(result.output)
        print(result.exit_code)
        assert result.exit_code == 0
        assert result.output == show_feature_bgp_autorestart_output
 
 
    @classmethod
    def teardown_class(cls):
        print("TEARDOWN")
        from .mock_tables import mock_single_asic
        importlib.reload(mock_single_asic)
