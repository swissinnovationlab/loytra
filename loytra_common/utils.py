#!/usr/bin/env python3
import os
import sys
import shutil
import select
import pty
from subprocess import Popen
from time import time, sleep
import asyncio
import getpass
from pathlib import Path


async def async_parallel_loop(items, func):
    tasks = []
    for item in items:
        task = asyncio.create_task(asyncio.to_thread(func, item))
        tasks.append(task)
    for task in tasks:
        await task


def parallel_loop(items, func):
    asyncio.run(async_parallel_loop(items, func))


class TCOL:
    # Foreground:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    # Formatting
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    # End colored text
    END = '\033[0m'
    NC = '\x1b[0m'  # No Color


def get_millis():
    return round(time() * 1000)


def millis_passed(timestamp):
    return get_millis() - timestamp


loytra_linux_password = None


def get_linux_password_noninteractive():
    env_password = os.getenv('LOYTRA_LINUX_PASSWORD')
    if loytra_linux_password is not None:
        return loytra_linux_password
    elif env_password is not None:
        return env_password
    return None


def get_linux_password():
    global loytra_linux_password
    password = get_linux_password_noninteractive()
    if password is None:
        from getpass import getpass
        password = getpass("Enter [sudo] password: ")
        loytra_linux_password = password
        return loytra_linux_password
    return password


def run_bash_cmd(cmd, logger=None, interaction={}, return_lines=True, return_code=False, cr_as_newline=False, remove_empty_lines=False):
    if logger: logger(f"CMD: {cmd}")
    if "sudo " in cmd: interaction["sudo"] = get_linux_password()
    master_fd, slave_fd = pty.openpty()
    line = ""
    lines = []
    with Popen(cmd, shell=True, preexec_fn=os.setsid, stdin=slave_fd, stdout=slave_fd, stderr=slave_fd, universal_newlines=True) as p:
        while p.poll() is None:
            r, w, e = select.select([sys.stdin, master_fd], [], [], 0.01)
            if master_fd in r:
                o = os.read(master_fd, 10240).decode("UTF-8")
                if o:
                    for c in o:
                        if cr_as_newline and c == "\r":
                            c = "\n"
                        if c == "\n":
                            if line and line not in interaction.values():
                                clean = line.strip().split('\r')[-1]
                                lines.append(clean)
                                if logger: logger(f"STD: {line}")
                            line = ""
                        else:
                            line += c
            if line:  # pass password to prompt
                for key in interaction:
                    if key in line:
                        if logger: logger(f"PMT: {line}")
                        # sleep(1) #TODO: if stops working check this
                        os.write(master_fd, ("%s" % (interaction[key])).encode())
                        os.write(master_fd, "\r\n".encode())
                        line = ""
        if line:
            clean = line.strip().split('\r')[-1]
            lines.append(clean)

    os.close(master_fd)
    os.close(slave_fd)

    if remove_empty_lines:
        lines = list(filter(lambda l: len(l) > 0, lines))

    if return_lines and return_code:
        return lines, p.returncode
    elif return_code:
        return p.returncode
    else:
        return lines


def get_full_path(path):
    return os.path.realpath(os.path.expanduser(path))


def _write_lines_to_file(lines, filename):
    filename = get_full_path(filename)
    with open(filename, 'w') as f:
        f.write("\n".join(lines) + "\n")


def write_lines_to_file(lines, filename, sudo_required=False):
    if not sudo_required:
        _write_lines_to_file(lines, filename)
    else:
        tmp = "/dev/shm/loytra_tmp_write_lines_to_file"
        _write_lines_to_file(lines, tmp)
        run_bash_cmd(f"sudo mv {tmp} {get_full_path(filename)}")


def read_lines_from_file(filename):
    filename = get_full_path(filename)
    with open(filename, 'r') as f:
        lines = f.read().splitlines()
    return lines


def check_if_path_exists(path):
    return os.path.exists(get_full_path(path))


def create_path(path):
    os.makedirs(get_full_path(path), exist_ok=True)


def remove_path(path, sudo_required=False):
    if check_if_path_exists(path):
        if not sudo_required:
            shutil.rmtree(get_full_path(path))
        else:
            run_bash_cmd(f"sudo rm {get_full_path(path)} -r")


def remove_file(path, sudo_required=False):
    if check_if_path_exists(path):
        if not sudo_required:
            os.remove(get_full_path(path))
        else:
            run_bash_cmd(f"sudo rm {get_full_path(path)}")


def get_file_list_in_path(path):
    return os.listdir(path)


def get_user():
    getpass.getuser()


def get_path_of_current_file(f):
    return str(Path(f).resolve().parent)
