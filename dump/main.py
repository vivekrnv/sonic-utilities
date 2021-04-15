import os,sys
import click
from tabulate import tabulate
sys.path.append(os.path.dirname(__file__))

import plugins
from helper import print_dump, extract_rid

# Autocompletion Helper
def get_available_modules(ctx, args, incomplete):
    return [k for k in plugins.dump_modules.keys() if incomplete in k]

# Display Modules Callback
def show_modules(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    header = ["Module", "Args"]
    display = []
    for mod in plugins.dump_modules:
        display.append((mod, plugins.dump_modules[mod].ARGS))
    click.echo(tabulate(display, header))
    ctx.exit()

@click.group()
def dump():
    pass

@dump.command()
@click.pass_context
@click.argument('module', required=True, type=str, autocompletion=get_available_modules)
@click.argument('vargs', nargs=-1) 
@click.option('--show', '-s', is_flag=True, default=False, help='Display Modules Available', is_eager=True, expose_value=False, callback=show_modules)
@click.option('--db', '-d', multiple=True, help='Only dump from these Databases')
@click.option('--table', '-t', is_flag=True, default=False, help='Print in tabular format', show_default=True)
@click.option('--rid', '-r', is_flag=True, default=True, help='Dont Extract VidToRid Mappings for ASIC DB Dumps', show_default=True)
def state(ctx, module, vargs, db, table, rid):
    """
    Dump the redis state of the module specified
    """

    if module not in plugins.dump_modules:
        click.echo("No Matching Plugin has been Implemented")
        ctx.exit()
    
    ctx.module = module
    
    if len(vargs) != plugins.dump_modules[module].N_ARGS:
        click.echo("Did not pass an expected arguments. Expected Argumets: ")
        click.echo(plugins.dump_modules[module].ARGS)
    
    obj = plugins.dump_modules[module]() 
    final_dict = obj.execute(vargs)
    
    if rid and not final_dict['vidtorid']:
        final_dict['vidtorid'] = extract_rid(final_dict)
    elif not rid:
        del final_dict['vidtorid']
        
    print_dump(final_dict, table, db)
    
    return 


if __name__ == '__main__':
    dump()
