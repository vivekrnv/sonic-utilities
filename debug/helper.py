import subprocess

def run_command(command, pager=False):
    click.echo(click.style("Command: ", fg='cyan') + click.style(command, fg='green'))
    p = subprocess.Popen(command, shell=True, text=True, stdout=subprocess.PIPE)
    output = p.stdout.read()
    if pager:
        click.echo_via_pager(output)
    else:
        click.echo(output)