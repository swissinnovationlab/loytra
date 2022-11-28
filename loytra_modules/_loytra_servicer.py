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


class Servicer:
    def __init__(self, name, exec_start, description, type="simple", environment=(), exec_start_pre=()):
        self._name = name
        self._exec_start = [exec_start]
        self._description = [description]
        self._type = [type]
        self._environment = environment
        self._exec_start_pre = exec_start_pre
        self.logger = log_factory.get(name="svs_servicer", tag="SERVICER")

    def _generic_systemd_func(self, action):
        run_bash_cmd(f"systemctl --user {action} {self._name}")

    def _systemd_deamon_reload(self):
        cmd = "systemctl --user daemon-reload"
        run_bash_cmd(cmd)

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

    def enable(self):
        self._generic_systemd_func("enable")

    def disable(self):
        self._generic_systemd_func("disable")

    def is_enabled(self):
        cmd = f"systemctl --user is-enabled --quiet {self._name}"
        return run_bash_cmd(cmd, return_lines=False, return_code=True) == 0

    def start(self):
        self._generic_systemd_func("start")

    def stop(self):
        self._generic_systemd_func("stop")

    def restart(self):
        self._generic_systemd_func("restart")

    def is_started(self):
        cmd = f"systemctl --user is-active --quiet {self._name}"
        return run_bash_cmd(cmd, return_lines=False, return_code=True) == 0

    def install(self):
        self._copy_service_file()
        self._systemd_deamon_reload()

    def uninstall(self):
        remove_file(f"{SYSTEMD_CONFIG_USER_PATH}/{self._name}")
        self._systemd_deamon_reload()

    def is_installed(self):
        return check_if_path_exists(f"{SYSTEMD_CONFIG_USER_PATH}/{self._name}")

    def logs(self, follow=True, since=None):
        cmd = "journalctl"
        cmd += " -o short-precise"
        if since != None:
            cmd += f" -S {since}"
        else:
            cmd += f" -n 1000"
        if follow:
            cmd += " -f"
        else:
            cmd += " --no-pager"
        cmd += f" --user-unit={self._name}"
        cmd = f"bash -c '{cmd}'"
        os.system(cmd)

    def get_active_state(self):
        if not self.is_installed():
            return "N/A"
        else:
            cmd = f"systemctl --user show -p ActiveState --value {self._name}"
            lines = run_bash_cmd(cmd)
            if lines is None or not isinstance(lines, list):
                lines = [""]
            return ANSI_ESCAPE.sub('', lines[0].strip())

    def get_sub_state(self):
        if not self.is_installed():
            return "N/A"
        else:
            cmd = f"systemctl --user show -p SubState --value {self._name}"
            lines = run_bash_cmd(cmd)
            if lines is None or not isinstance(lines, list):
                lines = [""]
            return ANSI_ESCAPE.sub('', lines[0].strip())

    def is_systemd_file_modified(self):
        # TODO: implement
        return False

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


class PythonServicer(Servicer):
    def __init__(self, name, exec_start, description):
        super().__init__(name=name, exec_start=exec_start, description=description, type="notify", environment=["PYTHONUNBUFFERED=true"])


if __name__ == "__main__":
    import readline
    import code

    servicer = Servicer(name="testing_date", exec_start="/usr/bin/date", description="Testing date")

    readline.parse_and_bind("tab: complete")
    code.interact(local=locals())
