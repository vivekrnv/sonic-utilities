import click
import subprocess

from . import bgp_frr
from . import zebra_frr
from . import bgp_quagga
from . import zebra_quagga

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help', '-?'])

#
# 'cli' group (root group) ###
#
@click.group(cls=click.Group, context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
def cli():
    """SONiC command line - 'debug' command"""
    pass


p = subprocess.check_output(["sudo vtysh -c 'show version'"], shell=True, text=True)
if 'FRRouting' in p:
    cli.add_command(bgp_frr.bgp)
    cli.add_command(zebra_frr.zebra)  
else:
    cli.add_command(bgp_quagga.bgp)
    cli.add_command(zebra_quagga.zebra)  
    
    
if __name__ == '__main__':
    cli()
