"""
techsupport_cleanup script.
    This script is invoked by the generate_dump script for techsupport cleanup
    For more info, refer to the Event Driven TechSupport & CoreDump Mgmt HLD
"""
import os
import sys
import glob
import time
import argparse
import subprocess
import syslog
import shutil
from swsscommon.swsscommon import SonicV2Connector
from utilities_common.auto_techsupport_helper import *


def clean_state_db_entries(removed_files, db):
    if not removed_files:
        return
    db_conn = db.get_redis_client(STATE_DB)
    for file in removed_files:
        db_conn.hdel(TS_MAP, os.path.basename(file))


def handle_techsupport_creation_event(dump_name, db):
    file_path = os.path.join(TS_DIR, dump_name)
    if not verify_recent_file_creation(file_path):
        return
    curr_list = get_ts_dumps()

    if db.get(CFG_DB, AUTO_TS, CFG_TS_CLEANUP) != "enabled":
        return

    max_ts = db.get(CFG_DB, AUTO_TS, CFG_MAX_TS)
    try:
        max_ts = float(max_ts)
    except:
        max_ts = 0.0

    if not max_ts:
        _ , num_bytes = get_stats(os.path.join(TS_DIR, TS_PTRN))
        syslog.syslog(syslog.LOG_INFO, "No Cleanup is performed, current size occupied: {}".format(pretty_size(num_bytes)))
        return

    removed_files = cleanup_process(max_ts, TS_PTRN, TS_DIR)
    clean_state_db_entries(removed_files, db)


def main():
    parser = argparse.ArgumentParser(description='Auto Techsupport Invocation and CoreDump Mgmt Script')
    parser.add_argument('name', type=str, help='TechSupport Dump Name')
    args = parser.parse_args()
    syslog.openlog(logoption=syslog.LOG_PID)
    db = SonicV2Connector(use_unix_socket_path=True)
    db.connect(CFG_DB)
    db.connect(STATE_DB)
    handle_techsupport_creation_event(args.name, db)


if __name__ == "__main__":
    main()