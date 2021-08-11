import os, re
import sys
import glob
import time
import argparse
import subprocess
import shutil
import math
import syslog

AUTO_TS = "AUTO_TECHSUPPORT|global"
CFG_DB = "CONFIG_DB"
CFG_STATE = "state"
CFG_MAX_TS = "max_techsupport_size"
COOLOFF = "cooloff"
CFG_CORE_USAGE = "core_usage"
CFG_SINCE = "since"

CORE_DUMP_DIR = "/var/core"
CORE_DUMP_PTRN = "*.core.gz"

TS_DIR = "/var/dump"
TS_PTRN = "sonic_dump_*.tar*"

# FEATURE Table fields
FEATURE = "FEATURE|{}"
TS = "auto_techsupport"

# State DB Attributes
STATE_DB = "STATE_DB"
TS_MAP = "AUTO_TECHSUPPORT|TS_CORE_MAP"

TIME_BUF = 20
SINCE_DEFAULT = "2 days ago"

##### Helper methods 
def subprocess_exec(cmd):
    output = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )
    return output.returncode, output.stdout, output.stderr

def get_ts_dumps(full_path=False):
    """ Get the list of TS dumps in the TS_DIR, sorted by the creation time """
    curr_list = glob.glob(os.path.join(TS_DIR, TS_PTRN))
    curr_list.sort(key=os.path.getmtime)
    if full_path:
        return curr_list
    return [os.path.basename(name) for name in curr_list]

def verify_recent_file_creation(file_path, in_last_sec=TIME_BUF):
    """ Verify if the file exists and is created within the last TIME_BUF sec """
    curr = time.time()
    try:
        was_created_on = os.path.getmtime(file_path)
    except:
        return False
    if curr - was_created_on < in_last_sec:
        return True 
    else:
        return False

def get_stats(ptrn, collect_stats=True):
    """
    Returns the size of the files (matched by the ptrn) occupied. 
    Also returns the list of files Sorted by the Descending order of creation time & size
    """
    files = glob.glob(ptrn)
    file_stats = []
    total_size = 0
    for file in files:
        file_size = os.path.getsize(file)
        if collect_stats:
            file_stats.append((os.path.getmtime(file), file_size, file))
        total_size += file_size
    if collect_stats:
        # Sort by the Descending order of file_creation_time, size_of_file
        file_stats = sorted(file_stats, key = lambda sub: (-sub[0], sub[1], sub[2]))
    return (file_stats, total_size)

def pretty_size(bytes):
    """Get human-readable file sizes"""
    UNITS_MAPPING = [
        (1<<50, ' PB'),
        (1<<40, ' TB'),
        (1<<30, ' GB'),
        (1<<20, ' MB'),
        (1<<10, ' KB'),
        (1, (' byte', ' bytes')),
    ]
    for factor, suffix in UNITS_MAPPING:
        if bytes >= factor:
            break
    amount = int(bytes / factor)

    if isinstance(suffix, tuple):
        singular, multiple = suffix
        if amount == 1:
            suffix = singular
        else:
            suffix = multiple
    return str(amount) + suffix

def cleanup_process(limit, file_ptrn, dir):
    """Deletes the oldest files incrementally until the size is under limit"""
    if not(1 <= limit and limit <= 100):
        syslog.syslog(syslog.LOG_ERR, "core_usage_limit can only be between 1 and 100, whereas the configured value is: {}".format(limit))
        return 
    
    fs_stats, curr_size = get_stats(os.path.join(dir, file_ptrn))
    orig_dumps = len(fs_stats)
    disk_stats = shutil.disk_usage(dir) 
    max_limit_bytes = math.floor((limit*disk_stats.total/100))
    
    if curr_size <= max_limit_bytes:
        return 
    
    num_bytes_to_del = curr_size - max_limit_bytes
    num_deleted = 0
    removed_files = []
    # Preserve the latest file created
    while num_deleted < num_bytes_to_del and len(fs_stats) > 1:
        stat = fs_stats.pop()
        try:
            os.remove(stat[2])
            removed_files.append(stat[2])
        except OSError as error:
            continue
        num_deleted += stat[1]
    syslog.syslog(syslog.LOG_INFO, "{} deleted from {}".format(pretty_size(num_deleted), dir))
    return removed_files