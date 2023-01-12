import re
from loytra_common import log_factory
from loytra_common.utils import *

ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
SYSTEMD_CONFIG_USER_PATH = "~/.config/systemd/user"
SYSTEMD_SERVICE_TEMPLATE = [
    "[Unit]",
    "Description=",
    "StartLimitIntervalSec=0",
    "",
    "[Service]",
    "Type=",
    "Environment=",
    "ExecStartPre=",
    "ExecStart=",
    "TimeoutStopSec=2",
    "",
    "Restart=always",
    "RestartSec=1",
    "",
    "[Install]",
    "WantedBy=default.target"
]


class _ServicerBase:
    def __init__(self, is_user_unit, is_dynamic, name):
        self._is_user_unit = is_user_unit
        self._is_dynamic = is_dynamic
        self._name = name
        self._journalctl_cmd = "journalctl"
        self._journalctl_unit = "--user-unit" if self._is_user_unit else "--unit"

    def _systemd_cmd(self, is_action):
        if self._is_user_unit:
            return "systemctl --user"
        else:
            if is_action:
                return "sudo systemctl"
            else:
                return "systemctl"

    def _systemd_deamon_reload(self):
        cmd = f"{self._systemd_cmd(is_action=True)} daemon-reload"
        run_bash_cmd(cmd)

    def _call_systemd_action(self, action):
        run_bash_cmd(f"{self._systemd_cmd(is_action=True)} {action} {self._name}")

    def enable(self):
        self._call_systemd_action("enable")

    def disable(self):
        self._call_systemd_action("disable")

    def is_enabled(self):
        cmd = f"{self._systemd_cmd(is_action=False)} is-enabled --quiet {self._name}"
        return run_bash_cmd(cmd, return_lines=False, return_code=True) == 0

    def start(self):
        self._call_systemd_action("start")

    def stop(self):
        self._call_systemd_action("stop")

    def restart(self):
        self._call_systemd_action("restart")

    def is_started(self):
        cmd = f"{self._systemd_cmd(is_action=False)} is-active --quiet {self._name}"
        return run_bash_cmd(cmd, return_lines=False, return_code=True) == 0

    def logs(self, follow=True, since=None):
        cmd = self._journalctl_cmd
        cmd += " -o short-precise"
        if since != None:
            cmd += f" -S {since}"
        else:
            cmd += f" -n 1000"
        if follow:
            cmd += " -f"
        else:
            cmd += " --no-pager"
        cmd += f" {self._journalctl_unit}={self._name}"
        cmd = f"bash -c '{cmd}'"
        os.system(cmd)

    def is_installed(self):
        verb = "list-units" if self._is_dynamic else "list-unit-files"
        cmd = f"{self._systemd_cmd(is_action=False)} {verb} --type service --no-pager | grep -Fq \"{self._name}\""
        return run_bash_cmd(cmd, return_lines=False, return_code=True) == 0

    def is_systemd_file_modified(self):
        # TODO: implement
        return False

    def get_active_state(self):
        cmd = f"{self._systemd_cmd(is_action=False)} show -p ActiveState --value {self._name}"
        lines = run_bash_cmd(cmd, remove_empty_lines=True)
        if lines is None or not isinstance(lines, list):
            lines = [""]
        return ANSI_ESCAPE.sub('', lines[0].strip())

    def get_sub_state(self):
        cmd = f"{self._systemd_cmd(is_action=False)} show -p SubState --value {self._name}"
        lines = run_bash_cmd(cmd, remove_empty_lines=True)
        if lines is None or not isinstance(lines, list):
            lines = [""]
        return ANSI_ESCAPE.sub('', lines[0].strip())

    def get_status(self):
        message = ""
        installed = self.is_installed()
        if installed:
            message += f"{[TCOL.FAIL + 'disabled' + TCOL.END, TCOL.OKGREEN + 'ENABLED' + TCOL.END][self.is_enabled()]}"
            active_status = f"{self.get_active_state()}|{self.get_sub_state()}"
            message += f", {[TCOL.FAIL + active_status.lower() + TCOL.END, TCOL.OKGREEN + active_status.upper() + TCOL.END]['running' in active_status]}"
            if self.is_systemd_file_modified():
                message += f" {TCOL.OKBLUE}M{TCOL.END}"
        return message

    def install(self):
        pass

    def uninstall(self):
        pass


class Servicer(_ServicerBase):
    def __init__(self, name, exec_start, description, type="simple", environment=(), exec_start_pre=(), is_user_unit=True):
        super().__init__(is_user_unit=is_user_unit, is_dynamic=False, name=name)
        self._exec_start = [exec_start]
        self._description = [description]
        self._type = [type]
        self._environment = environment
        self._exec_start_pre = exec_start_pre
        self.logger = log_factory.get(name="svs_servicer", tag="SERVICER")

    @staticmethod
    def _add_field_values_to_file_lines(field, values, file_lines):
        index = next(iter([i for i, s in enumerate(file_lines) if field in s]), None)
        if index:
            for value in values:
                file_lines.insert(index + 1, field + value)
        file_lines.pop(index)

    def _generate_systemd_service(self):
        file_lines = list(SYSTEMD_SERVICE_TEMPLATE)
        self._add_field_values_to_file_lines("Description=", self._description, file_lines)
        self._add_field_values_to_file_lines("ExecStart=", self._exec_start, file_lines)
        self._add_field_values_to_file_lines("Type=", self._type, file_lines)
        self._add_field_values_to_file_lines("Environment=", self._environment, file_lines)
        self._add_field_values_to_file_lines("ExecStartPre=", self._exec_start_pre, file_lines)
        return file_lines

    def _copy_service_file(self):
        if not check_if_path_exists(SYSTEMD_CONFIG_USER_PATH):
            create_path(SYSTEMD_CONFIG_USER_PATH)
        write_lines_to_file(self._generate_systemd_service(), f"{SYSTEMD_CONFIG_USER_PATH}/{self._name}")

    def install(self):
        self._copy_service_file()
        self._systemd_deamon_reload()

    def uninstall(self):
        remove_file(f"{SYSTEMD_CONFIG_USER_PATH}/{self._name}")
        self._systemd_deamon_reload()


class DynamicServicer(_ServicerBase):
    def __init__(self, name, is_user_unit=True):
        super().__init__(name=name, is_user_unit=is_user_unit, is_dynamic=True)


class PythonServicer(Servicer):
    def __init__(self, name, exec_start, description):
        super().__init__(name=name, exec_start=exec_start, description=description, type="notify", environment=["PYTHONUNBUFFERED=true"])


if __name__ == "__main__":
    import code
    import readline
    import rlcompleter

    # servicer = Servicer(name="testing_date", exec_start="/usr/bin/date", description="Testing date")
    servicer = DynamicServicer(name="openvpn-client@dmp.service", is_user_unit=False)

    readline.parse_and_bind("tab: complete")
    code.interact(local=locals())
