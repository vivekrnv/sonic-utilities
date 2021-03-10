import click

from .helper import run_command

#
# 'bgp' group for FRR ###
#
@click.group()
def bgp():
    """debug bgp group """
    pass

@bgp.command('allow-martians')
def allow_martians():
    """BGP allow martian next hops"""
    command = 'sudo vtysh -c "debug bgp allow-martians"'
    run_command(command)

@bgp.command()
@click.argument('additional', type=click.Choice(['segment']), required=False)
def as4(additional):
    """BGP AS4 actions"""
    command = 'sudo vtysh -c "debug bgp as4'
    if additional is not None:
        command += " segment"
    command += '"'
    run_command(command)

@bgp.command()
@click.argument('prefix', required=True)
def bestpath(prefix):
    """BGP bestpath"""
    command = 'sudo vtysh -c "debug bgp bestpath %s"' % prefix
    run_command(command)

@bgp.command()
@click.argument('prefix_or_iface', required=False)
def keepalives(prefix_or_iface):
    """BGP Neighbor Keepalives"""
    command = 'sudo vtysh -c "debug bgp keepalives'
    if prefix_or_iface is not None:
        command += " " + prefix_or_iface
    command += '"'
    run_command(command)

@bgp.command('neighbor-events')
@click.argument('prefix_or_iface', required=False)
def neighbor_events(prefix_or_iface):
    """BGP Neighbor Events"""
    command = 'sudo vtysh -c "debug bgp neighbor-events'
    if prefix_or_iface is not None:
        command += " " + prefix_or_iface
    command += '"'
    run_command(command)

@bgp.command()
def nht():
    """BGP nexthop tracking events"""
    command = 'sudo vtysh -c "debug bgp nht"'
    run_command(command)

@bgp.command()
@click.argument('additional', type=click.Choice(['error']), required=False)
def pbr(additional):
    """BGP policy based routing"""
    command = 'sudo vtysh -c "debug bgp pbr'
    if additional is not None:
        command += " error"
    command += '"'
    run_command(command)

@bgp.command('update-groups')
def update_groups():
    """BGP update-groups"""
    command = 'sudo vtysh -c "debug bgp update-groups"'
    run_command(command)

@bgp.command()
@click.argument('direction', type=click.Choice(['in', 'out', 'prefix']), required=False)
@click.argument('prefix', required=False)
def updates(direction, prefix):
    """BGP updates"""
    command = 'sudo vtysh -c "debug bgp updates'
    if direction is not None:
        command += " " + direction
    if prefix is not None:
        command += " " + prefix
    command += '"'
    run_command(command)

@bgp.command()
@click.argument('prefix', required=False)
def zebra(prefix):
    """BGP Zebra messages"""
    command = 'sudo vtysh -c "debug bgp zebra'
    if prefix is not None:
        command += " prefix " + prefix
    command += '"'
    run_command(command)






