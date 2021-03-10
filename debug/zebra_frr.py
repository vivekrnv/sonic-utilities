import click

from .helper import run_command

#
# 'zebra' group for FRR ###
#
@click.group()
def zebra():
    """debug zebra group"""
    pass

@zebra.command()
@click.argument('detailed', type=click.Choice(['detailed']), required=False)
def dplane(detailed):
    """Debug zebra dataplane events"""
    command = 'sudo vtysh -c "debug zebra dplane'
    if detailed is not None:
        command += " detailed"
    command += '"'
    run_command(command)

@zebra.command()
def events():
    """Debug option set for zebra events"""
    command = 'sudo vtysh -c "debug zebra events"'
    run_command(command)

@zebra.command()
def fpm():
    """Debug zebra FPM events"""
    command = 'sudo vtysh -c "debug zebra fpm"'
    run_command(command)

@zebra.command()
def kernel():
    """Debug option set for zebra between kernel interface"""
    command = 'sudo vtysh -c "debug zebra kernel"'
    run_command(command)

@zebra.command()
def nht():
    """Debug option set for zebra next hop tracking"""
    command = 'sudo vtysh -c "debug zebra nht"'
    run_command(command)

@zebra.command()
def packet():
    """Debug option set for zebra packet"""
    command = 'sudo vtysh -c "debug zebra packet"'
    run_command(command)

@zebra.command()
@click.argument('detailed', type=click.Choice(['detailed']), required=False)
def rib(detailed):
    """Debug RIB events"""
    command = 'sudo vtysh -c "debug zebra rib'
    if detailed is not None:
        command += " detailed"
    command += '"'
    run_command(command)

@zebra.command()
def vxlan():
    """Debug option set for zebra VxLAN (EVPN)"""
    command = 'sudo vtysh -c "debug zebra vxlan"'
    run_command(command)