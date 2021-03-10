import click

from .helper import run_command

#
# 'zebra' group for quagga ###
#
@click.group()
def zebra():
    """debug zebra group"""
    pass

@zebra.command()
def events():
    """debug option set for zebra events"""
    command = 'sudo vtysh -c "debug zebra events"'
    run_command(command)

@zebra.command()
def fpm():
    """debug zebra FPM events"""
    command = 'sudo vtysh -c "debug zebra fpm"'
    run_command(command)

@zebra.command()
def kernel():
    """debug option set for zebra between kernel interface"""
    command = 'sudo vtysh -c "debug zebra kernel"'
    run_command(command)

@zebra.command()
def packet():
    """debug option set for zebra packet"""
    command = 'sudo vtysh -c "debug zebra packet"'
    run_command(command)

@zebra.command()
def rib():
    """debug RIB events"""
    command = 'sudo vtysh -c "debug zebra rib"'
    run_command(command)