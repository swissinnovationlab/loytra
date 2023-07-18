from loytra_common import log_factory
from loytra_common.utils import run_bash_cmd, TCOL, write_lines_to_file, read_lines_from_file, check_if_path_exists, get_full_path, get_linux_password
import os
import stat
import re


class Packager:
    def __init__(self, name: str):
        self.name = name
        self.logger = log_factory.get(name=f"svs_packager_{self.name}", tag=f"PACKAGER:{self.name}")

    def is_sync(self) -> bool:
        return False

    def sync(self) -> bool:
        return False

    def unsync(self) -> bool:
        return False

    def get_status(self) -> str:
        return ""


class PackagerGroup(Packager):
    def __init__(self, name: str, children: list[Packager]):
        super().__init__(name)
        self.children = children

    def is_sync(self) -> bool:
        return all([c.is_sync() for c in self.children])

    def sync(self) -> bool:
        all_success = True
        for c in self.children:
            if not c.sync():
                all_success = False
        return all_success

    def unsync(self) -> bool:
        all_success = True
        for c in self.children:
            if not c.unsync():
                all_success = False
        return all_success

    def get_status(self) -> str:
        return super().get_status()


class PackagerUserGroup(Packager):
    def __init__(self, name: str, group: str):
        super().__init__(name)
        self.group = group

    def sync(self):
        cmd = f"sudo gpasswd -a $USER {self.group}"
        ret_code = run_bash_cmd(cmd, return_lines=False, return_code=True)
        self.logger.info("Reboot or logout for changes to take efect!")
        return ret_code == 0

    def unsync(self):
        cmd = f"sudo gpasswd -d $USER {self.group}"
        ret_code = run_bash_cmd(cmd, return_lines=False, return_code=True)
        self.logger.info("Reboot or logout for changes to take efect!")
        return ret_code == 0

    def is_sync(self):
        cmd = "groups"
        lines = run_bash_cmd(cmd)
        if isinstance(lines, list) and len(lines) == 1:
            groups = lines[0].split(" ")
            return self.group in groups
        return False

    def get_status(self):
        user_is_in_group = self.is_sync()
        if user_is_in_group is not None:
            status = f"{(TCOL.FAIL, TCOL.OKGREEN)[user_is_in_group]}{self.group}{TCOL.END}"
        else:
            status = f"{TCOL.WARNING}N/A{TCOL.END}"
        return status


class PackagerExecToPath(Packager):
    def __init__(self, name: str, exec, path, env_file="~/.bashrc"):
        super().__init__(name)
        self.exec = exec
        self.path = path
        self.env_file = env_file

    def generate_path_line(self):
        return f"export PATH=$PATH:{self.path}"

    def add_and_remove_lines_from_file(self, file_path, lines_to_add=None, lines_to_remove=None):
        full_file_path = get_full_path(file_path)
        if check_if_path_exists(full_file_path):
            lines = read_lines_from_file(full_file_path)
            for i in reversed(range(len(lines))):
                if (lines_to_add is not None and lines[i] in lines_to_add) or (lines_to_remove is not None and lines[i] in lines_to_remove):
                    lines.pop(i)
            if lines_to_add is not None:
                lines.extend(lines_to_add)
            write_lines_to_file(lines, full_file_path)
        self.logger.info("Restart the terminal for changes to take efect!")
        return True

    def sync(self):
        self.add_and_remove_lines_from_file(self.env_file, lines_to_add=[self.generate_path_line()])
        if not self.is_exec_executable():
            full_path = get_full_path(f"{self.path}/{self.exec}")
            st = os.stat(full_path)
            os.chmod(full_path, st.st_mode | stat.S_IEXEC)
        return True

    def unsync(self):
        return self.add_and_remove_lines_from_file(self.env_file, lines_to_remove=[self.generate_path_line()])

    def is_exec_executable(self):
        full_path = get_full_path(f"{self.path}/{self.exec}")
        return os.access(full_path, os.X_OK)

    def is_sync(self):
        import distutils.spawn
        return distutils.spawn.find_executable(self.exec) is not None

    def is_ready_for_usage(self):
        return self.is_sync() and self.is_exec_executable()

    def get_status(self):
        if not self.is_sync():
            status = TCOL.FAIL + self.exec + TCOL.END
        else:
            if not self.is_exec_executable():
                status = TCOL.OKBLUE + self.exec + TCOL.END
            else:
                status = TCOL.OKGREEN + self.exec + TCOL.END
        return status


class PackagerFileCreator(Packager):
    def __init__(self, name: str, path, line, sudo=False):
        super().__init__(name)
        self.path = path
        self.line = line
        self.sudo = sudo

    def get_sudo_interaction(self):
        interaction = {}
        if self.sudo:
            interaction["[sudo]"] = get_linux_password()
        return interaction

    def sync(self):
        cmd = f"echo '{self.line}' | {['', 'sudo '][self.sudo]}tee {self.path}"
        ret_code = run_bash_cmd(cmd, interaction=self.get_sudo_interaction(), return_lines=False, return_code=True)
        return ret_code

    def unsync(self):
        cmd = f"{['', 'sudo '][self.sudo]}rm {self.path}"
        return run_bash_cmd(cmd, interaction=self.get_sudo_interaction(), return_lines=False, return_code=True)

    def is_sync(self):
        try:
            lines = read_lines_from_file(self.path)
            if len(lines) == 1 and self.line in lines[0]:
                return True
        except FileNotFoundError:
            pass
        return False

    def get_status(self):
        return f"{(TCOL.FAIL, TCOL.OKGREEN)[self.is_sync()]}{self.path}{TCOL.END}"


class PackagerUdevRule(PackagerFileCreator):
    def __init__(self, name: str, path, line):
        super().__init__(name, path, line, sudo=True)

    def sync(self):
        super().sync()
        self.logger.info("Reboot or logout for changes to take efect!")


class PackagerRepoPacman(Packager):
    def __init__(self, name: str, package_name):
        super().__init__(name)
        self.sl = []
        self.qi = []
        self.repo = package_name.split("/")[0]
        self.package = package_name.split("/")[1]

    def get_sl(self):
        if len(self.sl) == 0:
            lines = run_bash_cmd("/usr/bin/pacman --color never -Sl")
            if lines is not None and isinstance(lines, list):
                self.sl = lines
        return self.sl

    def get_qi(self):
        if len(self.qi) == 0:
            lines = run_bash_cmd("/usr/bin/pacman --color never -Qi")
            if lines is not None and isinstance(lines, list):
                self.qi = lines
        return self.qi

    def is_sync(self):
        re_sl = re.compile(r"^(\S+)\s(\S+)\s(.*)$")
        for line in self.get_sl():
            # some lines look like this ['\x1b', '[', '?', '2', '5', 'h']
            try:
                m = re_sl.match(line)
                if m is not None:
                    g = m.groups()
                    if g[0] == self.repo and g[1] == self.package and "installed" in g[2]:
                        return True
            except:
                pass
        re_qi = re.compile(r"^Name\s+:\s(\S+)$")
        for line in self.get_qi():
            try:
                m = re_qi.match(line)
                if m is not None:
                    g = m.groups()
                    if g is not None and len(g) > 0 and g[0] == self.package:
                        return True
            except:
                pass
        return False

    def install_aur_package(self):
        cmds = [
            f"git clone https://aur.archlinux.org/{self.package}.git /tmp/{self.package}",
            f"cd /tmp/{self.package}; makepkg -siA",
            f"sudo rm /tmp/{self.package} -rv"
        ]
        interaction = {
            "[sudo]": get_linux_password(),
            "Proceed with installation": "Y",
            "are in conflict. Remove": "y",
        }
        for cmd in cmds:
            run_bash_cmd(cmd, interaction=interaction)

    def install_repo_package(self):
        cmd = f"sudo pacman -S {self.package}"
        interaction = {
            "Proceed with installation": "Y",
            "are in conflict. Remove": "y",
        }
        lines = run_bash_cmd(cmd, interaction=interaction)
        success = True
        if lines is not None and isinstance(lines, list):
            for line in lines:
                if "error" in line:
                    success = False
        if not success:
            self.logger.error(f"cant install, try manually: {TCOL.WARNING}{cmd}{TCOL.END}")

    def sync(self):
        if self.repo == "aur":
            self.install_aur_package()
        else:
            self.install_repo_package()

    def unsync(self):
        if self.is_sync():
            cmd = f"sudo pacman -Rs {self.package}"
            interaction = {
                "Proceed with installation": "Y",
                "are in conflict. Remove": "y",
            }
            lines = run_bash_cmd(cmd, interaction=interaction)
            success = True
            if lines is not None and isinstance(lines, list):
                for line in lines:
                    if "error" in line:
                        success = False
            if not success:
                self.logger.error(f"cant remove, try manually: {TCOL.WARNING}{cmd}{TCOL.END}")

    def get_status(self):
        return f"{(TCOL.FAIL, TCOL.OKGREEN)[self.is_sync()]}{self.repo}/{self.package}{TCOL.END}"

    @staticmethod
    def is_valid():
        return check_if_path_exists("/usr/bin/pacman")


class PackagerRepoApt(Packager):
    def __init__(self, name: str, package_name):
        super().__init__(name)
        self.package_name = package_name

    def is_sync(self):
        cmd = f"dpkg -s {self.package_name}"
        lines = run_bash_cmd(cmd)
        if lines is not None and isinstance(lines, list):
            for line in lines:
                if "Status: install ok installed" in line:
                    return True
        return False

    def sync(self):
        cmd = f"sudo apt install {self.package_name}"
        interaction = {
            "Do you want to continue? [Y/n]": "Y"
        }
        lines = run_bash_cmd(cmd, interaction=interaction)
        if lines is not None and isinstance(lines, list):
            for line in lines:
                if f"Setting up {self.package_name}" in line:
                    return True

        self.logger.error(f"cant install, try manually: {TCOL.WARNING}{cmd}{TCOL.END}")
        return False

    def unsync(self):
        if self.is_sync():
            cmd = f"sudo apt purge {self.package_name}"
            interaction = {
                "Do you want to continue? [Y/n]": "Y"
            }
            lines = run_bash_cmd(cmd, interaction=interaction)
            if lines is not None and isinstance(lines, list):
                for line in lines:
                    if f"Removing {self.package_name}" in line:
                        return True
            self.logger.error(f"cant remove, try manually: {TCOL.WARNING}{cmd}{TCOL.END}")
            return False

    def get_status(self):
        return f"{(TCOL.FAIL, TCOL.OKGREEN)[self.is_sync()]}{self.package_name}{TCOL.END}"

    @staticmethod
    def is_valid():
        return check_if_path_exists("/usr/bin/apt")


class PackagerRepo(Packager):
    def __init__(self, name: str, pacman_package_name: str, apt_package_name):
        super().__init__(name)
        if PackagerRepoPacman.is_valid():
            self.package_manager = PackagerRepoPacman(name, pacman_package_name)
        elif PackagerRepoApt.is_valid():
            self.package_manager = PackagerRepoApt(name, apt_package_name)
        else:
            self.logger.error("No package manager found!")
            raise RuntimeError("No package manager found!")

    def is_sync(self):
        return self.package_manager.is_sync()

    def sync(self):
        return self.package_manager.sync()

    def unsync(self):
        return self.package_manager.unsync()

    def get_status(self):
        return self.package_manager.get_status()


class MultiPackager(Packager):
    def __init__(self, name: str, packagers: list[Packager]):
        super().__init__(name)
        self.packagers = packagers

    def is_sync(self) -> bool:
        for packager in self.packagers:
            if packager.is_sync():
                return True
        return False

    def sync(self) -> bool:
        print(f"{TCOL.BOLD}{self.name}{TCOL.END}")
        for e, packager in enumerate(self.packagers):
            print(f"  [{e}] {packager.name}")
        try:
            return self.packagers[int(input("select number to install: "))].sync()
        except Exception as e:
            print(f"ERROR: cant install with {e}")
            return False

    def unsync(self) -> bool:
        for packager in self.packagers:
            if packager.is_sync():
                packager.unsync()
        return True

    def get_status(self) -> str:
        statuses = []
        for packager in self.packagers:
            if packager.is_sync():
                statuses.append(packager.get_status())
        return "|".join(statuses)


class PackagerPip(Packager):
    def __init__(self, name: str, package: str, module: str):
        super().__init__(name)
        self.package = package
        self.module = module

    def is_sync(self) -> bool:
        from importlib import util as imput
        return imput.find_spec(self.module) is not None

    def sync(self) -> bool:
        cmd = f"pip install {self.package}"
        interaction = {"Proceed (": "y"}
        return run_bash_cmd(cmd, interaction=interaction, return_lines=False, return_code=True) == 0

    def unsync(self) -> bool:
        cmd = f"pip uninstall {self.package}"
        interaction = {"Proceed (": "y"}
        return run_bash_cmd(cmd, interaction=interaction, return_lines=False, return_code=True) == 0

    def get_status(self) -> str:
        return [f"{TCOL.FAIL}pip{TCOL.END}", f"{TCOL.OKGREEN}PIP{TCOL.END}"][self.is_sync()]
