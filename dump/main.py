import click

sys.path.append(os.path.realpath(__file__))

import plugins

@click.group()
@click.argument('module', required=True, type=str)
@click.argument('id', required=True, type=str)
def cli(module, id):
    """
    Dump utility of the id for the module specified
    """
    
    if module not in plugins.child_classes:
        click.echo("Not found")
    
    plugins.child_classes[module].execute(id)
    
if __name__ == '__main__':
    cli()