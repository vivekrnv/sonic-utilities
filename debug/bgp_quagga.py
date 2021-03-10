import click

from .helper import run_command

#
# 'bgp' group for quagga ###
#
@click.group(invoke_without_command=True)
@click.pass_context
def bgp(ctx):
    """debug bgp on"""
    if ctx.invoked_subcommand is None:
        command = 'sudo vtysh -c "debug bgp"'
        run_command(command)

@bgp.command()
def events():
    """debug bgp events on"""
    command = 'sudo vtysh -c "debug bgp events"'
    run_command(command)

@bgp.command()
def updates():
    """debug bgp updates on"""
    command = 'sudo vtysh -c "debug bgp updates"'
    run_command(command)

@bgp.command()
def as4():
    """debug bgp as4 actions on"""
    command = 'sudo vtysh -c "debug bgp as4"'
    run_command(command)

@bgp.command()
def filters():
    """debug bgp filters on"""
    command = 'sudo vtysh -c "debug bgp filters"'
    run_command(command)

@bgp.command()
def fsm():
    """debug bgp finite state machine on"""
    command = 'sudo vtysh -c "debug bgp fsm"'
    run_command(command)

@bgp.command()
def keepalives():
    """debug bgp keepalives on"""
    command = 'sudo vtysh -c "debug bgp keepalives"'
    run_command(command)

@bgp.command()
def zebra():
    """debug bgp zebra messages on"""
    command = 'sudo vtysh -c "debug bgp zebra"'
    run_command(command)
