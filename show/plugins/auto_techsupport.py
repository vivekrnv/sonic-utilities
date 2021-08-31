"""
Auto-generated show CLI plugin.

Auto generated for AUTO_TECHSUPPORT|GLOBAL table
Manually updated to add the correspondig cli
1) show auto-techsupport rate_limit_interval
2) show auto-techsupport history
"""

import click
import tabulate
import natsort
import utilities_common.cli as clicommon


def format_attr_value(entry, attr):
    """ Helper that formats attribute to be presented in the table output.

    Args:
        entry (Dict[str, str]): CONFIG DB entry configuration.
        attr (Dict): Attribute metadata.

    Returns:
        str: fomatted attribute value.
    """

    if attr["is-leaf-list"]:
        return "\n".join(entry.get(attr["name"], []))
    return entry.get(attr["name"], "N/A")


def format_group_value(entry, attrs):
    """ Helper that formats grouped attribute to be presented in the table output.

    Args:
        entry (Dict[str, str]): CONFIG DB entry configuration.
        attrs (List[Dict]): Attributes metadata that belongs to the same group.

    Returns:
        str: fomatted group attributes.
    """

    data = []
    for attr in attrs:
        if entry.get(attr["name"]):
            data.append((attr["name"] + ":", format_attr_value(entry, attr)))
    return tabulate.tabulate(data, tablefmt="plain")


@click.group(name="auto-techsupport",
             cls=clicommon.AliasedGroup)
def AUTO_TECHSUPPORT():
    """ AUTO_TECHSUPPORT part of config_db.json """

    pass


@AUTO_TECHSUPPORT.command(name="global")
@clicommon.pass_db
def AUTO_TECHSUPPORT_GLOBAL(db):
    """  """

    header = [

        "AUTO INVOKE TS",
        "COREDUMP CLEANUP",
        "TECHSUPPORT CLEANUP",
        "RATE LIMIT INTERVAL",
        "MAX TECHSUPPORT SIZE",
        "MAX CORE SIZE",
        "SINCE",

    ]

    body = []

    table = db.cfgdb.get_table("AUTO_TECHSUPPORT")
    entry = table.get("GLOBAL", {})
    row = [
        format_attr_value(
            entry,
            {'name': 'auto_invoke_ts', 'description': 'Knob to make techsupport invocation event-driven based on core-dump generation', 'is-leaf-list': False, 'is-mandatory': False, 'group': ''}
        ),
        format_attr_value(
            entry,
            {'name': 'coredump_cleanup', 'description': 'Knob to enable coredump cleanup', 'is-leaf-list': False, 'is-mandatory': False, 'group': ''}
        ),
        format_attr_value(
            entry,
            {'name': 'techsupport_cleanup', 'description': 'Knob to enable techsupport dump cleanup', 'is-leaf-list': False, 'is-mandatory': False, 'group': ''}
        ),
        format_attr_value(
            entry,
            {'name': 'rate_limit_interval', 'description': 'Minimum time in seconds between two successive techsupport invocations. Configure 0 to explicitly disable', 'is-leaf-list': False, 'is-mandatory': False, 'group': ''}
        ),
        format_attr_value(
            entry,
            {'name': 'max_techsupport_size', 'description': 'Maximum Size to which the techsupport dumps in /var/dump directory can be grown until', 'is-leaf-list': False, 'is-mandatory': False, 'group': ''}
        ),
        format_attr_value(
            entry,
            {'name': 'max_core_size', 'description': 'Maximum Size to which the core dumps in /var/core directory can be grown until', 'is-leaf-list': False, 'is-mandatory': False, 'group': ''}
        ),
        format_attr_value(
            entry,
            {'name': 'since', 'description': 'Limits the auto-invoked techsupport to only collect the logs & core-dumps generated since the time provided', 'is-leaf-list': False, 'is-mandatory': False, 'group': ''}
        ),
    ]

    body.append(row)
    click.echo(tabulate.tabulate(body, header))

@AUTO_TECHSUPPORT.command(name="history")
@clicommon.pass_db
def AUTO_TECHSUPPORT_history(db):
    fv = db.db.get_all("STATE_DB", "AUTO_TECHSUPPORT|TS_CORE_MAP")
    header = ["TECHSUPPORT DUMP", "TRIGGERED BY", "CORE DUMP"]
    body = []
    for field, value in fv.items():
        core_dump, _, supervisor_crit_proc = value.split(";")
        body.append([field, supervisor_crit_proc, core_dump])
    click.echo(tabulate.tabulate(body, header))

@AUTO_TECHSUPPORT.command(name="rate_limit_interval")
@clicommon.pass_db
def AUTO_TECHSUPPORT_RATE_LIMIT_INTERVAL(db):
    fv = db.db.get_all("CONFIG_DB", "AUTO_TECHSUPPORT|RATE_LIMIT_INTERVAL")
    header = ["FEATURE", "RATE LIMIT INTERVAL"]
    body = []
    for field, value in fv.items():
        body.append([field, value])
    click.echo(tabulate.tabulate(body, header))


def register(cli):
    cli_node = AUTO_TECHSUPPORT
    if cli_node.name in cli.commands:
        raise Exception(f"{cli_node.name} already exists in CLI")
    cli.add_command(AUTO_TECHSUPPORT)
