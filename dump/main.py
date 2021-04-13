import os,sys
import click

sys.path.append(os.path.realpath(__file__))

import plugins

from helper import print_dump

@click.group()
def dump():
    pass


@dump.command()
@click.argument('module', required=True, type=str)
@click.argument('id', required=True, type=str)
def state(module, id):
    """
    Dump the switch state of the id for the module specified
    """
    
    if module not in plugins.dump_modules:
        click.echo("No Matching Plugin has been Implemented")
        return 
    
    params = {"id" : id}
    
    obj = plugins.dump_modules[module]() 
    final_dict = obj.execute(params)  
    print_dump(final_dict)


if __name__ == '__main__':
    dump()
