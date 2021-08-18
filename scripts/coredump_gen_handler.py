"""
coredump_gen_handler script.
    This script is invoked by the coredump-compress script
    for auto techsupport invocation and cleanup core dumps.
    For more info, refer to the Event Driven TechSupport & CoreDump Mgmt HLD
"""
import os
import re
import sys
import glob
import time
import argparse
import subprocess
import syslog
from swsscommon.swsscommon import SonicV2Connector
from utilities_common.auto_techsupport_helper import *


def handle_coredump_cleanup(dump_name, db):
    if db.get(CFG_DB, AUTO_TS, CFG_CORE_CLEANUP) != "enabled":
        return

    core_usage = db.get(CFG_DB, AUTO_TS, CFG_CORE_USAGE)
    try:
        core_usage = float(core_usage)
    except Exception as e:
        core_usage = 0.0

    if not core_usage:
        _, num_bytes = get_stats(os.path.join(CORE_DUMP_DIR, CORE_DUMP_PTRN))
        syslog.syslog(syslog.LOG_INFO, "No Cleanup is performed, current size occupied: {}".format(pretty_size(num_bytes)))
        return

    cleanup_process(core_usage, CORE_DUMP_PTRN,  CORE_DUMP_DIR)


class CriticalProcCoreDumpHandle():
    """
    Class to handle coredump creation event for critical processes
    """
    def __init__(self, core_name, db):
        self.core_name = core_name
        self.db = db
        self.proc_mp = {}
        self.core_ts_map = {}
        self.curr_ts_list = []

    def handle_core_dump_creation_event(self):
        file_path = os.path.join(CORE_DUMP_DIR, self.core_name)
        if not verify_recent_file_creation(file_path):
            syslog.syslog(syslog.LOG_INFO, "Spurious Invocation. {} is not created within last {} sec".format(file_path, TIME_BUF))
            return

        if self.db.get(CFG_DB, AUTO_TS, CFG_INVOC_TS) != "enabled":
            return

        container_name, process_name = self.fetch_exit_event()
        if not (process_name and container_name):
            msg = "No Corresponding Exit Event was found for {}. Techsupport Invocation is skipped".format(self.core_name)
            syslog.syslog(syslog.LOG_INFO, msg)
            return

        FEATURE_KEY = FEATURE.format(container_name)
        if self.db.get(CFG_DB, FEATURE_KEY, TS) != "enabled":
            msg = "auto-techsupport feature for {} is not enabled. Techsupport Invocation is skipped. core: {}"
            syslog.syslog(syslog.LOG_NOTICE, msg.format(container_name, self.core_name))
            return

        global_cooloff = self.db.get(CFG_DB, AUTO_TS, COOLOFF)
        proc_cooloff = self.db.get(CFG_DB, FEATURE_KEY, COOLOFF)

        try:
            global_cooloff = float(global_cooloff)
        except:
            global_cooloff = 0.0

        try:
            proc_cooloff = float(proc_cooloff)
        except:
            proc_cooloff = 0.0

        cooloff_passed = self.verify_cooloff(global_cooloff, proc_cooloff, process_name)
        print(cooloff_passed)
        if cooloff_passed:
            since_cfg = self.get_since_arg()
            new_file = self.invoke_ts_cmd(since_cfg)
            if new_file:
                field = os.path.basename(new_file[0])
                value = "{};{};{}".format(self.core_name, int(time.time()), process_name)
                self.db.set(STATE_DB, TS_MAP, field, value)

    def get_since_arg(self):
        since_cfg = self.db.get(CFG_DB, AUTO_TS, CFG_SINCE)
        if not since_cfg:
            return SINCE_DEFAULT
        rc, _, stderr = subprocess_exec(["date", "--date='{}'".format(since_cfg)])
        if rc == 0:
            return since_cfg
        return SINCE_DEFAULT

    def invoke_ts_cmd(self, since_cfg):
        since_cfg = "'" + since_cfg + "'"
        cmd = " ".join(["show", "techsupport", "--since", since_cfg])
        _, _, _ = subprocess_exec(["show", "techsupport", "--since", since_cfg])
        new_list = get_ts_dumps(True)
        diff = list(set(new_list).difference(set(self.curr_ts_list)))
        self.curr_ts_list = new_list
        if not diff:
            syslog.syslog(syslog.LOG_ERR, "{} was run, but no techsupport dump is found".format(cmd))
        else:
            syslog.syslog(syslog.LOG_INFO, "{} is successful, {} is created".format(cmd, diff))
        return diff

    def verify_cooloff(self, global_cooloff, proc_cooloff, proc):
        """Verify both the global cooloff and per-proc cooloff has passed"""
        self.curr_ts_list = get_ts_dumps(True)
        if global_cooloff and self.curr_ts_list:
            last_ts_dump_creation = os.path.getmtime(self.curr_ts_list[-1])
            if time.time() - last_ts_dump_creation < global_cooloff:
                msg = "Global Cooloff period has not passed. Techsupport Invocation is skipped. Core: {}"
                syslog.syslog(syslog.LOG_INFO, msg.format(self.core_name))
                return False

        ts_map = self.db.get_all(STATE_DB, TS_MAP)
        self.parse_ts_map(ts_map)
        print(self.core_ts_map)
        if proc_cooloff and proc in self.core_ts_map:
            last_creation_time = self.core_ts_map[proc][0][0]
            if time.time() - last_creation_time < proc_cooloff:
                msg = "Process Cooloff period for {} has not passed. Techsupport Invocation is skipped. Core: {}"
                syslog.syslog(syslog.LOG_INFO, msg.format(proc, self.core_name))
                return False
        return True

    def parse_ts_map(self, ts_map):
        """Create proc_name, ts_dump & creation_time map"""
        if not ts_map:
            return
        for ts_dump, tup in ts_map.items():
            core_dump, creation_time, proc_name = tup.split(";")
            if proc_name not in self.core_ts_map:
                self.core_ts_map[proc_name] = []
            self.core_ts_map[proc_name].append((int(creation_time), ts_dump))
        for proc_name in self.core_ts_map:
            self.core_ts_map[proc_name].sort()

    def fetch_exit_event(self):
        """Fetch the relevant entry in the AUTO_TECHSUPPORT|PROC_EXIT_EVENTS table"""
        comm, _, pid, _, _ = self.core_name.split(".")
        feature_name, supervisor_proc_name = "", ""
        start = time.time()
        while time.time() - start <= WAIT_BUFFER:
            data = self.db.get_all("STATE_DB", CRITICAL_PROC)
            if data:
                for field in data:
                    try:
                        pid_, comm_ = data[field].split(";")
                        if pid_ == pid and comm in comm_:
                            feature_name, supervisor_proc_name = field.split(";")
                            break
                        elif comm_ == NO_COMM and pid_ == pid:
                            feature_name, supervisor_proc_name = field.split(";")
                            continue
                    except Exception as e:
                        continue
            if feature_name and supervisor_proc_name:
                break
            time.sleep(SLEEP_FOR)
        return feature_name, supervisor_proc_name


def main():
    parser = argparse.ArgumentParser(description='Auto Techsupport Invocation and CoreDump Mgmt Script')
    parser.add_argument('name', type=str, help='Core Dump Name')
    args = parser.parse_args()
    syslog.openlog(logoption=syslog.LOG_PID)
    db = SonicV2Connector(use_unix_socket_path=True)
    db.connect(CFG_DB)
    db.connect(STATE_DB)
    cls = CriticalProcCoreDumpHandle(args.name, db)
    cls.handle_core_dump_creation_event()
    handle_coredump_cleanup(args.name, db)

if __name__ == "__main__":
    main()