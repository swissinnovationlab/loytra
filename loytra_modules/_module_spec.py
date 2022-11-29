import abc
from typing import Optional
from loytra_modules._loytra_moduler import Moduler
from loytra_modules._loytra_packager import Packager
from loytra_modules._loytra_servicer import Servicer


class LoytraModule(metaclass=abc.ABCMeta):
    def __init__(self, module_name: str, moduler: Moduler, sort_index: int = -1):
        self.module_name = module_name
        self.moduler = moduler
        self.sort_index = sort_index

    @abc.abstractmethod
    def is_reference(self):
        pass


class LoytraModuleReference(LoytraModule):
    def __init__(self, module_name: str, moduler: Moduler, sort_index: int = -1):
        super().__init__(module_name, moduler, sort_index)

    def is_reference(self):
        return True


class LoytraModuleInstance(LoytraModule):
    def __init__(self, module_name: str, moduler: Moduler, sort_index: int = -1,
            services: Optional[dict[str, Servicer]] = None,
            packages: Optional[list[Packager]] = None):

        super().__init__(module_name, moduler, sort_index)

        self.services = services if services is not None else {}
        packages_list = packages if packages is not None else []
        self.packages = { p.name: p for p in packages_list }

    def is_reference(self):
        return False

