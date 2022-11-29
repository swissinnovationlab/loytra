#!/usr/bin/env python3

import os
import traceback
from typing import Optional
from loytra_common import log_factory
from loytra_common.utils import TCOL
from loytra_modules import Moduler
from loytra_modules._module_finder import find_loytra_modules, get_loytra_modules_by_folder_name
from loytra_modules._token_storage import storage_write_value
from loytra_modules._module_spec import LoytraModule, LoytraModuleInstance
from loytra_modules._loytra_packager import Packager, PackagerGroup


class LoytraCliActions:
    def __init__(self):
        self._logger = log_factory.get(name="svs_cli_actions", tag="SVS:CLI:ACTIONS")
        self._modules = find_loytra_modules()

    def modules(self):
        return self._modules

    def get_moduler_by_module_name(self, module_name, print_error=True):
        module = self._modules.get(module_name)
        if module is None:
            if print_error:
                self._logger.error(f"Module {module_name} not supported.")
            return None
        return module.moduler

    def get_servicer_by_module_service_name(self, module_service_name):
        module_name, _, service_name = module_service_name.partition("/")

        module = self._modules.get(module_name)
        if module is None:
            self._logger.error(f"Module {module_name} not supported.")
            return None

        moduler = module.moduler
        if not moduler.is_installed() or not isinstance(module, LoytraModuleInstance):
            self._logger.error(f"Module {module_name} not installed.")
            return None

        servicer = module.services.get(service_name)
        if servicer is None:
            self._logger.error(f"Servicer for {module_service_name} not found.")

        return servicer

    def get_packager_by_module_package_name(self, module_package_name):
        module_name, _, package_name = module_package_name.partition("/")

        module = self._modules.get(module_name)
        if module is None:
            self._logger.error(f"Module {module_name} not supported.")
            return None

        moduler = module.moduler
        if not moduler.is_installed() or not isinstance(module, LoytraModuleInstance):
            self._logger.error(f"Module {module_name} not installed.")
            return None

        packager = module.packages.get(package_name)
        if packager is None:
            self._logger.error(f"Packager for {module_package_name} not found.")

        return packager

    def install(self, module_name):
        moduler = self.get_moduler_by_module_name(module_name, print_error=False)
        if moduler is not None:
            return moduler.install()
        else:
            if "https://" in module_name:
                try:
                    def input_or_none(message):
                        string = input(message)
                        if len(string):
                            return string
                        return None

                    url = module_name.replace("https://", "")
                    url = url.removesuffix(".git")
                    url = url.removesuffix("/")
                    folder_name = url.split("/")[-1]
                    hash = input_or_none("Hash[default]: ")
                    github_token = input_or_none("Token[None]: ")
                    moduler = Moduler(url=url, hash=hash, github_token=github_token)
                    if (moduler.download_module() and github_token is not None):
                        loytra_modules = get_loytra_modules_by_folder_name(folder_name)
                        if len(loytra_modules) > 0:
                            target_module = loytra_modules[0]
                            target_module.moduler.install_module()
                            storage_write_value(target_module.module_name, github_token)
                except Exception as e:
                    print(f"Install module failed with {e}, {traceback.print_exc()}")
        return None

    def uninstall(self, module_name):
        moduler = self.get_moduler_by_module_name(module_name)
        if moduler is not None:
            return moduler.uninstall()
        return None

    def start(self, module_service_name):
        servicer = self.get_servicer_by_module_service_name(module_service_name)
        if servicer is not None:
            servicer.install()
            servicer.start()

    def stop(self, module_service_name=None):
        servicer = self.get_servicer_by_module_service_name(module_service_name)
        if servicer is not None:
            servicer.stop()
            if not servicer.is_enabled():
                servicer.uninstall()

    def restart(self, module_service_name=None):
        if module_service_name is None or len(module_service_name.strip()) == 0:
            print(f"{TCOL.FAIL}{TCOL.BOLD}{'Restarting running services:'}{TCOL.END}")
            for module in self._modules.values():
                if not isinstance(module, LoytraModuleInstance):
                    self._logger.warning(f"Module {module.module_name} is not installed!")
                    continue

                for service in module.services:
                    servicer = module.services[service]
                    active = servicer.get_active_state().startswith("activ")
                    servicer.install()
                    if active:
                        name = f"{module.module_name}/{service}"
                        print(f"  {name}")
                        servicer.restart()
        else:
            servicer = self.get_servicer_by_module_service_name(module_service_name)
            if servicer is not None:
                active = servicer.get_active_state().startswith("activ")
                servicer.install()
                if active:
                    servicer.restart()

    def enable(self, module_service_name):
        servicer = self.get_servicer_by_module_service_name(module_service_name)
        if servicer is not None:
            servicer.install()
            servicer.enable()
            servicer.start()

    def disable(self, module_service_name):
        servicer = self.get_servicer_by_module_service_name(module_service_name)
        if servicer is not None:
            servicer.stop()
            servicer.disable()
            servicer.uninstall()

    def logs(self, module_service_name):
        servicer = self.get_servicer_by_module_service_name(module_service_name)
        if servicer is not None:
            servicer.logs()

    def debug(self, module_service_name):
        servicer = self.get_servicer_by_module_service_name(module_service_name)
        if servicer is not None:
            servicer.stop()
            cmd = " ".join(servicer._exec_start)
            cmd = cmd.replace("%h", "~")
            cmd = f"python -m pdb {cmd}"
            print("b: [[filename:]lineno | function[, condition]]")
            print("c: continue debugging until you hit a breakpoint")
            print("s: step through the code")
            print("n: to go to next line of code")
            print("l: list source code for the current file (default: 11 lines including the line being executed)")
            print("u: navigate up a stack frame")
            print("d: navigate down a stack frame")
            print("p: to print the value of an expression in the current context")
            os.system(cmd)

    def run(self, module_service_name):
        servicer = self.get_servicer_by_module_service_name(module_service_name)
        if servicer is not None:
            servicer.stop()
            cmd = " ".join(servicer._exec_start)
            cmd = cmd.replace("%h", "~")
            os.system(cmd)

    def _find_packager_in_path(self, packagers: list[Packager], path: list[str], level: int = 0):
        if level >= len(path):
            return None

        for packager in packagers:
            if packager.name == path[level]:
                if level + 1 == len(path):
                    return packager
                elif isinstance(packager, PackagerGroup):
                    return self._find_packager_in_path(packager.children, path, level + 1)

        return None

    def _find_module_packager_in_path(self, module_package_path: str) -> tuple[Optional[LoytraModule], Optional[Packager]]:
        found_module: Optional[LoytraModule] = None
        found_packager: Optional[Packager] = None
        path_parts = list(filter(lambda it: len(it) > 0, module_package_path.split('/')))
        if len(path_parts) > 0:
            target_module_name = path_parts[0]
            target_packager_path = path_parts[1:]
            for module_name, module in self._modules.items():
                if module_name == target_module_name and isinstance(module, LoytraModuleInstance):
                    found_module = module
                    packager = self._find_packager_in_path(list(module.packages.values()), target_packager_path)
                    if packager is not None:
                        found_packager = packager
                        break
        return (found_module, found_packager)

    def sync(self, module_package_name):
        found_module, found_packager = self._find_module_packager_in_path(module_package_name)
        if found_module is not None and found_packager is not None and found_module.moduler.is_installed():
            found_packager.sync()
        else:
            self._logger.error(f"Package {module_package_name} not found.")

    def unsync(self, module_package_name):
        found_module, found_packager = self._find_module_packager_in_path(module_package_name)
        if found_module is not None and found_packager is not None and found_module.moduler.is_installed():
            found_packager.unsync()
        else:
            self._logger.error(f"Package {module_package_name} not found.")

    def status(self):
        for module in self._modules.values():
            string = ""
            if isinstance(module, LoytraModuleInstance) and module.moduler.is_installed():
                services = module.services
                if len(services) > 0:
                    string += f"{TCOL.BOLD}{module.module_name}{TCOL.END}"
                    for service_name, servicer in services.items():
                        string += "\n"
                        if not servicer.is_installed():
                            string += f"  {TCOL.FAIL}{TCOL.BOLD}{service_name}{TCOL.END}"
                        else:
                            color = TCOL.OKGREEN
                            if servicer.is_enabled():
                                if not servicer.get_active_state().startswith("activ"):
                                    color = TCOL.OKBLUE
                            else:
                                if servicer.get_active_state().startswith("activ"):
                                    color = TCOL.WARNING

                            string += f"  {color}{TCOL.BOLD}{service_name}{TCOL.END} [{servicer.get_status()}]"
            if len(string): print(string)

    def _traverse_packagers_for_list(self, packagers: list[Packager], level: int = 0):
        for packager in packagers:
            if isinstance(packager, PackagerGroup):
                yield (packager, level, True)
                yield from self._traverse_packagers_for_list(packager.children, level + 1)
            else:
                yield (packager, level, False)

    def list(self):
        for module in self._modules.values():
            string = ""
            if isinstance(module, LoytraModuleInstance) and module.moduler.is_installed():
                module.moduler.fetch()
                string += f"{TCOL.OKGREEN}{TCOL.BOLD}{module.module_name}{TCOL.END} [{module.moduler.get_status()}]"
                for packager, level, is_group in self._traverse_packagers_for_list(list(module.packages.values())):
                    string += "\n"
                    padd = "  " + ("  " * level)
                    if is_group:
                        string += f"{TCOL.BOLD}{padd}{packager.name}:{TCOL.END}"
                    else:
                        string += f"{padd}{packager.name} [{packager.get_status()}]"
            else:
                string += f"{TCOL.FAIL}{TCOL.BOLD}{module.module_name}{TCOL.END}"
            if len(string): print(string)

    def update(self, module_name=None):
        if module_name is None or len(module_name.strip()) == 0:
            running_services = {}
            print(f"{TCOL.FAIL}{TCOL.BOLD}{'Stoping running services:'}{TCOL.END}")
            for module in self._modules.values():
                if not isinstance(module, LoytraModuleInstance):
                    continue

                for service in module.services:
                    servicer = module.services[service]
                    if servicer.get_active_state().startswith("activ"):
                        name = f"{module.module_name}/{service}"
                        running_services[name] = servicer
                        print(f"  {name}")
                        servicer.stop()

            print(f"{TCOL.OKBLUE}{TCOL.BOLD}{'Updating repos:'}{TCOL.END}")
            for module in self._modules.values():
                if not isinstance(module, LoytraModuleInstance):
                    continue

                moduler = module.moduler
                if moduler.is_installed():
                    print(f"  {module.module_name}")
                    moduler.update()
                    moduler.install()

            print(f"{TCOL.OKGREEN}{TCOL.BOLD}{'Resuming services:'}{TCOL.END}")
            for service in running_services:
                print(f"  {service}")
                running_services[service].install()
                running_services[service].start()
        else:
            moduler = self.get_moduler_by_module_name(module_name)
            if moduler is not None:
                running_services = {}
                module = self._modules.get(module_name)
                if module is not None and isinstance(module, LoytraModuleInstance):
                    print(f"{TCOL.FAIL}{TCOL.BOLD}{'Stoping running services:'}{TCOL.END}")
                    for service in module.services:
                        servicer = module.services[service]
                        if servicer.get_active_state().startswith("activ"):
                            name = f"{module_name}/{service}"
                            running_services[name] = servicer
                            print(f"  {name}")
                            servicer.stop()
                    print(f"{TCOL.OKBLUE}{TCOL.BOLD}{'Updating repo:'}{TCOL.END}")
                    if moduler.is_installed():
                        print(f"  {module_name}")
                        moduler.update()
                    print(f"{TCOL.OKGREEN}{TCOL.BOLD}{'Resuming services:'}{TCOL.END}")
                    for service in running_services:
                        print(f"  {service}")
                        running_services[service].install()
                        running_services[service].start()

    def clean(self):
        for module in self._modules.values():
            if isinstance(module, LoytraModuleInstance):
                moduler = module.moduler
                if moduler.is_installed():
                    moduler.clean()
                    moduler.install()

