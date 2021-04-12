import os,sys
import click

sys.path.append(os.path.realpath(__file__))

import plugins

@click.group()
def cli():
    pass


@cli.command()
@click.argument('module', required=True, type=str)
@click.argument('id', required=True, type=str)
def state(module, id):
    """
    Dump the switch state of the id for the module specified
    """
    
    if module not in plugins.dump_modules:
        click.echo("No Matching Plugin has been Implemented")
        return 
    
    obj = plugins.dump_modules[module]() 
    obj.execute(id)


if __name__ == '__main__':
    cli()
