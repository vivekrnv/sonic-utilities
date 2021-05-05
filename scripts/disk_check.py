#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
What:
    There have been cases, where disk turns Read-only due to kernel bug.
    In Read-only state, system blocks new remote user login via TACACS.
    This utility is to check & make transient recovery as needed.

How:
    check for Read-Write permission. If Read-only, create writable overlay using tmpfs.

    By default "/etc" & "/home" are checked and if in Read-only state, make them Read-Write
    using overlay on top of tmpfs.

    Making /etc & /home as writable lets successful new remote user login.

    If in Read-only state or in Read-Write state with the help of tmpfs overlay,
    syslog ERR messages are written, to help raise alerts.

    Monit may be used to invoke it periodically, to help scan & fix and
    report via syslog.

"""

import argparse
import os
import sys
import syslog
import subprocess

UPPER_DIR = "/run/mount/upper"
WORK_DIR = "/run/mount/work"
MOUNTS_FILE = "/proc/mounts"

def log_err(m):
    print("Err: {}".format(m), file=sys.stderr)
    syslog.syslog(syslog.LOG_ERR, m)


def log_info(m):
    print("Info: {}".format(m))
    syslog.syslog(syslog.LOG_INFO, m)


def log_debug(m):
    print("debug: {}".format(m))
    syslog.syslog(syslog.LOG_DEBUG, m)


def test_writable(dirs): 
    for d in dirs:
        rw = os.access(d, os.W_OK)
        if not rw:
            log_err("{} is not read-write".format(d))
            return False
        else:
            log_debug("{} is Read-Write".format(d))
    return True


def run_cmd(cmd):
    proc = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    ret = proc.returncode
    if ret:
        log_err("failed: ret={} cmd={}".format(ret, cmd))
    else:
        log_info("ret={} cmd: {}".format(ret, cmd))

    if proc.stdout:
        log_info("stdout: {}".format(str(proc.stdout)))
    if proc.stderr:
        log_info("stderr: {}".format(str(proc.stderr)))
    return ret


def get_dname(path_name):
    return os.path.basename(os.path.normpath(path_name))


def do_mnt(dirs):
    if os.path.exists(UPPER_DIR):
        log_err("Already mounted")
        return 1

    for i in (UPPER_DIR, WORK_DIR):
        try:
            os.mkdir(i)
        except OSError as error:
            log_err("Failed to create {}".format(i))
            return 1

    for d in dirs:
        ret = run_cmd("mount -t overlay overlay_{} -o lowerdir={},"
        "upperdir={},workdir={} {}".format(
            get_dname(d), d, UPPER_DIR, WORK_DIR, d))
        if ret:
            break

    if ret:
        log_err("Failed to mount {} as Read-Write".format(dirs))
    else:
        log_info("{} are mounted as Read-Write".format(dirs))
    return ret


def is_mounted(dirs):
    if not os.path.exists(UPPER_DIR):
        return False

    onames = set()
    for d in dirs:
        onames.add("overlay_{}".format(get_dname(d)))

    with open(MOUNTS_FILE, "r") as s:
        for ln in s.readlines():
            n = ln.strip().split()[0]
            if n in onames:
                log_debug("Mount exists for {}".format(n))
                return True
    return False


def do_check(skip_mount, dirs):
    ret = 0
    if not test_writable(dirs):
        if not skip_mount:
            ret = do_mnt(dirs)

    # Check if mounted
    if (not ret) and is_mounted(dirs):
        log_err("READ-ONLY: Mounted {} to make Read-Write".format(dirs))

    return ret


def main():
    parser=argparse.ArgumentParser(
            description="check disk for Read-Write and mount etc & home as Read-Write")
    parser.add_argument('-s', "--skip-mount", action='store_true', default=False,
            help="Skip mounting /etc & /home as Read-Write")
    parser.add_argument('-d', "--dirs", default="/etc,/home",
            help="dirs to mount")
    args = parser.parse_args()

    ret = do_check(args.skip_mount, args.dirs.split(","))
    return ret


if __name__ == "__main__":
    sys.exit(main())
