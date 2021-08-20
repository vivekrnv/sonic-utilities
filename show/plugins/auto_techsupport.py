"""
Auto-generated show CLI plugin.
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
def AUTO_TECHSUPPORT_global(db):
    """  """
    header = [
        "AUTO INVOKE TS",
        "COREDUMP CLEANUP",
        "TECHSUPPORT CLEANUP",
        "COOLOFF",
        "MAX TECHSUPPORT SIZE",
        "CORE USAGE",
        "SINCE",
    ]

    body = []
    table = db.cfgdb.get_table("AUTO_TECHSUPPORT")
    entry = table.get("global", {})
    row = [
        format_attr_value(
            entry,
            {'name': 'auto_invoke_ts', 'description': '', 'is-leaf-list': False, 'is-mandatory': False, 'group': ''}
        ),
        format_attr_value(
            entry,
            {'name': 'coredump_cleanup', 'description': '', 'is-leaf-list': False, 'is-mandatory': False, 'group': ''}
        ),
        format_attr_value(
            entry,
            {'name': 'techsupport_cleanup', 'description': '', 'is-leaf-list': False, 'is-mandatory': False, 'group': ''}
        ),
        format_attr_value(
            entry,
            {'name': 'cooloff', 'description': '', 'is-leaf-list': False, 'is-mandatory': False, 'group': ''}
        ),
        format_attr_value(
            entry,
            {'name': 'max_techsupport_size', 'description': '', 'is-leaf-list': False, 'is-mandatory': False, 'group': ''}
        ),
        format_attr_value(
            entry,
            {'name': 'core_usage', 'description': '', 'is-leaf-list': False, 'is-mandatory': False, 'group': ''}
        ),
        format_attr_value(
            entry,
            {'name': 'since', 'description': '', 'is-leaf-list': False, 'is-mandatory': False, 'group': ''}
        ),
    ]
    body.append(row)
    click.echo(tabulate.tabulate(body, header))


@AUTO_TECHSUPPORT.command(name="history")
@clicommon.pass_db
def AUTO_TECHSUPPORT_history(db):
    fv = db.db.get_all("STATE_DB", "AUTO_TECHSUPPORT|TS_CORE_MAP")
    header = ["Techsupport Dump", "Triggered By", "Critical Process"]
    body = []
    for field, value in fv.items():
        core_dump, _, supervisor_crit_proc = value.split(";")
        body.append([field, core_dump, supervisor_crit_proc])
    click.echo(tabulate.tabulate(body, header))


def register(cli):
    cli_node = AUTO_TECHSUPPORT
    if cli_node.name in cli.commands:
        raise Exception(f"{cli_node.name} already exists in CLI")
    cli.add_command(AUTO_TECHSUPPORT)
