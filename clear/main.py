import configparser
import os
import subprocess
import sys

import click

from utilities_common import util_base

from . import plugins


# This is from the aliases example:
# https://github.com/pallets/click/blob/57c6f09611fc47ca80db0bd010f05998b3c0aa95/examples/aliases/aliases.py
class Config(object):
    """Object to hold CLI config"""

    def __init__(self):
        self.path = os.getcwd()
        self.aliases = {}

    def read_config(self, filename):
        parser = configparser.RawConfigParser()
        parser.read([filename])
        try:
            self.aliases.update(parser.items('aliases'))
        except configparser.NoSectionError:
            pass


# Global Config object
_config = None



class AliasedGroup(click.Group):
    """This subclass of click.Group supports abbreviations and
       looking up aliases in a config file with a bit of magic.
    """

    def get_command(self, ctx, cmd_name):
        global _config

        # If we haven't instantiated our global config, do it now and load current config
        if _config is None:
            _config = Config()

            # Load our config file
            cfg_file = os.path.join(os.path.dirname(__file__), 'aliases.ini')
            _config.read_config(cfg_file)

        # Try to get builtin commands as normal
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv

        # No builtin found. Look up an explicit command alias in the config
        if cmd_name in _config.aliases:
            actual_cmd = _config.aliases[cmd_name]
            return click.Group.get_command(self, ctx, actual_cmd)

        # Alternative option: if we did not find an explicit alias we
        # allow automatic abbreviation of the command.  "status" for
        # instance will match "st".  We only allow that however if
        # there is only one command.
        matches = [x for x in self.list_commands(ctx)
                   if x.lower().startswith(cmd_name.lower())]
        if not matches:
            return None
        elif len(matches) == 1:
            return click.Group.get_command(self, ctx, matches[0])
        ctx.fail('Too many matches: %s' % ', '.join(sorted(matches)))


# To be enhanced. Routing-stack information should be collected from a global
# location (configdb?), so that we prevent the continous execution of this
# bash oneliner. To be revisited once routing-stack info is tracked somewhere.
def get_routing_stack():
    command = "sudo docker ps | grep bgp | awk '{print$2}' | cut -d'-' -f3 | cut -d':' -f1"

    try:
        proc = subprocess.Popen(command,
                                stdout=subprocess.PIPE,
                                shell=True,
                                text=True)
        stdout = proc.communicate()[0]
        proc.wait()
        result = stdout.rstrip('\n')

    except OSError as e:
        raise OSError("Cannot detect routing-stack")

    return (result)


# Global Routing-Stack variable
routing_stack = get_routing_stack()


def run_command(command, pager=False, return_output=False, return_exitstatus=False):
    # Provide option for caller function to Process the output.
    proc = subprocess.Popen(command, shell=True, text=True, stdout=subprocess.PIPE)
    if return_output:
        output = proc.communicate()
        return output if not return_exitstatus else output + (proc.returncode,)
    elif pager:
        #click.echo(click.style("Command: ", fg='cyan') + click.style(command, fg='green'))
        click.echo_via_pager(proc.stdout.read())
    else:
        #click.echo(click.style("Command: ", fg='cyan') + click.style(command, fg='green'))
        click.echo(proc.stdout.read())


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help', '-?'])


#
# 'cli' group (root group) ###
#

# This is our entrypoint - the main "Clear" command
@click.group(cls=AliasedGroup, context_settings=CONTEXT_SETTINGS)
def cli():
    """SONiC command line - 'Clear' command"""
    pass

#
# 'ip' group ###
#

# This allows us to add commands to both cli and ip groups, allowing for
# "Clear <command>" and "Clear ip <command>" to function the same
@cli.group()
def ip():
    """Clear IP """
    pass


# 'ipv6' group

@cli.group()
def ipv6():
    """Clear IPv6 information"""
    pass


#
# Inserting BGP functionality into cli's clear parse-chain.
# BGP commands are determined by the routing-stack being elected.
#
if routing_stack == "quagga":
    from .bgp_quagga_v4 import bgp
    ip.add_command(bgp)
    from .bgp_quagga_v6 import bgp
    ipv6.add_command(bgp)
elif routing_stack == "frr":
    from .bgp_quagga_v4 import bgp
    ip.add_command(bgp)
    from .bgp_frr_v6 import bgp
    ipv6.add_command(bgp)

@cli.command()
def counters():
    """Clear counters"""
    command = "portstat -c"
    run_command(command)

@cli.command()
@click.argument('interface', metavar='<interface_name>', required=False, type=str)
def rifcounters(interface):
    """Clear RIF counters"""
    command = "intfstat -c"
    if interface is not None:
        command = "intfstat -i {} -c".format(interface)
    run_command(command)

@cli.command()
def queuecounters():
    """Clear queue counters"""
    command = "queuestat -c"
    run_command(command)

@cli.command()
def pfccounters():
    """Clear pfc counters"""
    command = "pfcstat -c"
    run_command(command)

@cli.command()
def dropcounters():
    """Clear drop counters"""
    command = "dropstat -c clear"
    run_command(command)

#
# 'clear watermarks
#

@cli.group(name='priority-group')
def priority_group():
    """Clear priority_group WM"""
    pass

@priority_group.group()
def watermark():
    """Clear priority_group user WM. One does not simply clear WM, root is required"""
    if os.geteuid() != 0:
        exit("Root privileges are required for this operation")

@watermark.command('headroom')
def clear_wm_pg_headroom():
    """Clear user headroom WM for pg"""
    command = 'watermarkstat -c -t pg_headroom'
    run_command(command)

@watermark.command('shared')
def clear_wm_pg_shared():
    """Clear user shared WM for pg"""
    command = 'watermarkstat -c -t pg_shared'
    run_command(command)

@priority_group.group()
def drop():
    """Clear priority-group dropped packets stats"""
    pass

@drop.command('counters')
def clear_pg_counters():
    """Clear priority-group dropped packets counter """

    if os.geteuid() != 0 and os.environ.get("UTILITIES_UNIT_TESTING", "0") != "2":
        exit("Root privileges are required for this operation")
    command = 'pg-drop -c clear'
    run_command(command)

@priority_group.group(name='persistent-watermark')
def persistent_watermark():
    """Clear queue persistent WM. One does not simply clear WM, root is required"""
    if os.geteuid() != 0:
        exit("Root privileges are required for this operation")

@persistent_watermark.command('headroom')
def clear_pwm_pg_headroom():
    """Clear persistent headroom WM for pg"""
    command = 'watermarkstat -c -p -t pg_headroom'
    run_command(command)

@persistent_watermark.command('shared')
def clear_pwm_pg_shared():
    """Clear persistent shared WM for pg"""
    command = 'watermarkstat -c -p -t pg_shared'
    run_command(command)


@cli.group()
def queue():
    """Clear queue WM"""
    pass

@queue.group()
def watermark():
    """Clear queue user WM. One does not simply clear WM, root is required"""
    if os.geteuid() != 0:
        exit("Root privileges are required for this operation")

@watermark.command('unicast')
def clear_wm_q_uni():
    """Clear user WM for unicast queues"""
    command = 'watermarkstat -c -t q_shared_uni'
    run_command(command)

@watermark.command('multicast')
def clear_wm_q_multi():
    """Clear user WM for multicast queues"""
    command = 'watermarkstat -c -t q_shared_multi'
    run_command(command)

@watermark.command('all')
def clear_wm_q_all():
    """Clear user WM for all queues"""
    command = 'watermarkstat -c -t q_shared_all'
    run_command(command)

@queue.group(name='persistent-watermark')
def persistent_watermark():
    """Clear queue persistent WM. One does not simply clear WM, root is required"""
    if os.geteuid() != 0:
        exit("Root privileges are required for this operation")

@persistent_watermark.command('unicast')
def clear_pwm_q_uni():
    """Clear persistent WM for persistent queues"""
    command = 'watermarkstat -c -p -t q_shared_uni'
    run_command(command)

@persistent_watermark.command('multicast')
def clear_pwm_q_multi():
    """Clear persistent WM for multicast queues"""
    command = 'watermarkstat -c -p -t q_shared_multi'
    run_command(command)

@persistent_watermark.command('all')
def clear_pwm_q_all():
    """Clear persistent WM for all queues"""
    command = 'watermarkstat -c -p -t q_shared_all'
    run_command(command)

@cli.group(name='headroom-pool')
def headroom_pool():
    """Clear headroom pool WM"""
    pass

@headroom_pool.command('watermark')
def watermark():
    """Clear headroom pool user WM. One does not simply clear WM, root is required"""
    if os.geteuid() != 0:
        exit("Root privileges are required for this operation")

    command = 'watermarkstat -c -t headroom_pool'
    run_command(command)

@headroom_pool.command('persistent-watermark')
def persistent_watermark():
    """Clear headroom pool persistent WM. One does not simply clear WM, root is required"""
    if os.geteuid() != 0:
        exit("Root privileges are required for this operation")

    command = 'watermarkstat -c -p -t headroom_pool'
    run_command(command)

#
# 'arp' command ####
#

@click.command()
@click.argument('ipaddress', required=False)
def arp(ipaddress):
    """Clear IP ARP table"""
    if ipaddress is not None:
        command = 'sudo ip -4 neigh show {}'.format(ipaddress)
        (out, err) = run_command(command, return_output=True)
        if not err and 'dev' in out:
            outputList = out.split()
            dev = outputList[outputList.index('dev') + 1]
            command = 'sudo ip -4 neigh del {} dev {}'.format(ipaddress, dev)
        else:
            click.echo("Neighbor {} not found".format(ipaddress))
            return
    else:
        command = "sudo ip -4 -s -s neigh flush all"

    run_command(command)

#
# 'ndp' command ####
#

@click.command()
@click.argument('ipaddress', required=False)
def ndp(ipaddress):
    """Clear IPv6 NDP table"""
    if ipaddress is not None:
        command = 'sudo ip -6 neigh show {}'.format(ipaddress)
        (out, err) = run_command(command, return_output=True)
        if not err and 'dev' in out:
            outputList = out.split()
            dev = outputList[outputList.index('dev') + 1]
            command = 'sudo ip -6 neigh del {} dev {}'.format(ipaddress, dev)
        else:
            click.echo("Neighbor {} not found".format(ipaddress))
            return
    else:
        command = 'sudo ip -6 -s -s neigh flush all'

    run_command(command)

# Add 'arp' command to both the root 'cli' group and the 'ip' subgroup
cli.add_command(arp)
cli.add_command(ndp)
ip.add_command(arp)
ip.add_command(ndp)

#
# 'fdb' command ####
#
@cli.group()
def fdb():
    """Clear FDB table"""
    pass

@fdb.command('all')
def clear_all_fdb():
    """Clear All FDB entries"""
    command = 'fdbclear'
    run_command(command)

# 'sonic-clear fdb port' and 'sonic-clear fdb vlan' will be added later
'''
@fdb.command('port')
@click.argument('portid', required=True)
def clear_port_fdb(portid):
    """Clear FDB entries learned from one port"""
    command = 'fdbclear' + ' -p ' + portid
    run_command(command)

@fdb.command('vlan')
@click.argument('vlanid', required=True)
def clear_vlan_fdb(vlanid):
    """Clear FDB entries learned in one VLAN"""
    command = 'fdbclear' + ' -v ' + vlanid
    run_command(command)
'''

#
# 'line' command
#
@cli.command('line')
@click.argument('target')
@click.option('--devicename', '-d', is_flag=True, help="clear by name - if flag is set, interpret target as device name instead")
def line(target, devicename):
    """Clear preexisting connection to line"""
    cmd = "consutil clear {}".format("--devicename " if devicename else "") + str(target)
    (output, _, exitstatus) = run_command(cmd, return_output=True, return_exitstatus=True)
    click.echo(output)
    sys.exit(exitstatus)

#
# 'nat' group ("clear nat ...")
#

@cli.group(cls=AliasedGroup)
def nat():
    """Clear the nat info"""
    pass

# 'statistics' subcommand ("clear nat statistics")
@nat.command()
def statistics():
    """ Clear all NAT statistics """

    cmd = "natclear -s"
    run_command(cmd)

# 'translations' subcommand ("clear nat translations")
@nat.command()
def translations():
    """ Clear all NAT translations """

    cmd = "natclear -t"
    run_command(cmd)


# Load plugins and register them
helper = util_base.UtilHelper()
for plugin in helper.load_plugins(plugins):
    helper.register_plugin(plugin, cli)


if __name__ == '__main__':
    cli()
