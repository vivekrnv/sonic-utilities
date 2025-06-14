#!/usr/bin/env python3

try:
    import click
    import os
    import sys
    import glob
    from pathlib import Path
    import datetime
    import syslog
    from sonic_py_common import device_info
    from utilities_common.auto_techsupport_helper import get_stats, pretty_size
except ImportError as e:
    raise ImportError("%s - required module not found" % str(e))

SYNCD_CONTAINER_NAME = 'syncd'
NASA_CLI = '/usr/sbin/cli/nasa_cli.py -u --exit_on_failure'
NASA_CLI_CMD_F = '/tmp/nasa_cli_cmd.txt'
CFG_REC_CMD_PREFIX = 'set_sai_debug_mode'
PKT_REC_CMD_PREFIX = 'set_packet_debug_mode'

SAI_PROFILE_FILE = '/tmp/sai.profile'
SAI_KEY_DUMP_STORE_PATH = 'SAI_DUMP_STORE_PATH'
SAI_KEY_DUMP_STORE_COUNT = 'SAI_DUMP_STORE_AMOUNT'
CFG_REC_DIR = "config-record"
PKT_REC_DIR = "packet-drop"

def get_sai_profile_value(key, docker_client):
    """Get value for a given key from /tmp/sai.profile file in syncd container.

    Args:
        key (str): Key to look up in the profile file
        docker_client (docker.client.DockerClient): Docker client

    Returns:
        str: Value for the given key, or None if not found
    """
    cmd = f"cat {SAI_PROFILE_FILE}"
    rc, out = run_in_syncd(cmd, docker_client)

    if rc == 0 and out:
        for line in out.splitlines():
            if line.startswith(f"{key}="):
                return line.split('=', 1)[1]
    return ""


def run_in_syncd(cmd, docker_client):
    """Run a command in the syncd container using Docker Python SDK.

    Args:
        cmd (str): Command to run in the container
        docker_client (docker.client.DockerClient): Docker client

    Returns:
        tuple: (return_code, stdout)
    """
    try:
        container = docker_client.containers.get(SYNCD_CONTAINER_NAME)
        exit_code, output = container.exec_run(cmd)
        return exit_code, output.decode('utf-8')
    except Exception as e:
        click.echo(f"Error executing command in syncd container: {str(e)}", err=True)
        return 1, str(e)


def run_nasa_cli(cmd, docker_client):
    """Run a command in the syncd container using NASA CLI

    Args:
        cmd (str): Command to run in the container
            Eg: set_packet_debug_mode on filepath /tmp/nasa_pkt_record.bin
            Eg: set_sai_debug_mode on filepath /tmp/nasa_cfg_record.bin
        docker_client (docker.client.DockerClient): Docker client

    Returns:
        tuple: (return_code, stdout)
    """
    # First create a temp file in the container

    lines = [cmd + '\n', 'quit\n']
    content = ''.join(lines).replace("'", "'\"'\"'")  # Escape single quotes
    command = f"sh -c 'echo -n \"{content}\" > {NASA_CLI_CMD_F}'"
    rc, stdout = run_in_syncd(command, docker_client)

    if rc != 0:
        return rc, stdout

    cmd = f"{NASA_CLI} -l {NASA_CLI_CMD_F}"
    return run_in_syncd(cmd, docker_client)


def rotate_dump_files(path, count, docker_client):
    """Rotate dump files in the given directory

    If the number of dump files in the directory is greater than the or equal to the count,
    the oldest file is deleted.

    Args:
        path (str): Directory to rotate dump files. Should be accessible from the host
        count (int): Number of dump files to keep
        docker_client (docker.client.DockerClient): Docker client

    Returns:
        None
    """
    fs_stats, num_bytes = get_stats(os.path.join(path, "*"))
    syslog.syslog(syslog.LOG_INFO, f"Logrotate: Current size of the directory {path} : {pretty_size(num_bytes)}")

    # If number of files exceeds count, delete the oldest ones
    num_delete = len(fs_stats) - count
    while num_delete >= 0:
        stat = fs_stats.pop()
        os.remove(stat[2])
        num_delete -= 1
        syslog.syslog(syslog.LOG_INFO, f"Logrotate: Deleted {stat[2]}, size: {pretty_size(stat[1])}")

    # Get the new size of the directory
    fs_stats, num_bytes = get_stats(os.path.join(path, "*"))
    return


def get_location_details(docker_client):
    """Get the dump details from the sai.profile file

    Args:
        docker_client (docker.client.DockerClient): Docker client

    Returns:
        tuple: (path, count)
    """
    path_root = get_sai_profile_value(SAI_KEY_DUMP_STORE_PATH, docker_client)
    count = get_sai_profile_value(SAI_KEY_DUMP_STORE_COUNT, docker_client)

    if not Path(path_root).exists():
        click.echo(f"Directory {path_root} does not exist", err=True)
        return (None, None)

    try:
        count = int(count)
    except ValueError as e:
        click.echo(f"Invalid count value: {count}, error: {e}", err=True)
        return (None, None)

    return path_root, count


@click.group()
def nvidia_bluefield():
    """NVIDIA BlueField platform configuration tasks"""
    pass


@nvidia_bluefield.group('sdk')
def sdk():
    """SDK related configuration"""
    pass


@sdk.command('packet-drop')
@click.argument('state', type=click.Choice(['enabled', 'disabled']))
def packet_drop(state):
    """Enable or disable packet drop recording"""
    import docker
    docker_client = docker.from_env()
    if state == 'disabled':
        rc, _ = run_nasa_cli(PKT_REC_CMD_PREFIX, docker_client)
        if rc == 0:
            click.echo(f"Packet drop recording {state}.")
        return rc

    path_root, count = get_location_details(docker_client)
    if path_root is None or count is None:
        return 1
    path = os.path.join(path_root, PKT_REC_DIR)
    Path(path).mkdir(parents=True, exist_ok=True)

    # rotate the dump files
    rotate_dump_files(path, count, docker_client)

    # create the bin file under the path path with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bin_path = os.path.join(path, f"pkt_dump_record_{timestamp}.bin")
    os.mknod(bin_path)

    cmd = f"{PKT_REC_CMD_PREFIX} on filepath {bin_path}"
    rc, stdout = run_nasa_cli(cmd, docker_client)
    if rc != 0:
        click.echo(f"Could not enable packet drop recording: {stdout}", err=True)
    else:
        syslog.syslog(syslog.LOG_NOTICE, f"Packet drop recording enabled on {bin_path}")
        click.echo(f"Packet drop recording {state}.")

    sys.exit(rc)


@sdk.command('config-record')
@click.argument('state', type=click.Choice(['enabled', 'disabled']))
def config_record(state):
    """Enable or disable configuration recording"""
    import docker
    docker_client = docker.from_env()
    if state == 'disabled':
        rc, _ = run_nasa_cli(CFG_REC_CMD_PREFIX, docker_client)
        if rc == 0:
            click.echo(f"Config recording {state}.")
        return rc

    path_root, count = get_location_details(docker_client)
    if path_root is None or count is None:
        return 1
    path = os.path.join(path_root, CFG_REC_DIR)
    Path(path).mkdir(parents=True, exist_ok=True)

    # rotate the dump files
    rotate_dump_files(path, count, docker_client)

    # create the bin file under the path path with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bin_path = os.path.join(path, f"cfg_record_{timestamp}.bin")
    os.mknod(bin_path)

    cmd = f"{CFG_REC_CMD_PREFIX} on filepath {bin_path}"
    rc, stdout = run_nasa_cli(cmd, docker_client)
    if rc != 0:
        click.echo(f"Could not enable config recording: {stdout}", err=True)
    else:
        syslog.syslog(syslog.LOG_NOTICE, f"Config recording enabled on {bin_path}")
        click.echo(f"Config recording {state}.")
    
    sys.exit(rc)


def register(cli):
    version_info = device_info.get_sonic_version_info()
    if (version_info and version_info.get('asic_type') == 'nvidia-bluefield'):
        cli.commands['platform'].add_command(nvidia_bluefield)
