from typing import Optional
from loytra_modules._loytra_moduler import Moduler
from loytra_modules._loytra_packager import Packager
from loytra_modules._loytra_servicer import Servicer

class LoytraModule:
    def __init__(self,
            module_name: str,
            moduler: Moduler,
            services: Optional[dict[str, Servicer]] = None,
            packages: Optional[list[Packager]] = None,
            sort_index: int = -1):
        self.module_name = module_name
        self.moduler = moduler
        self.services = services if services is not None else {}

        packages_list = packages if packages is not None else []
        self.packages = { p.name: p for p in packages_list }
        self.sort_index = sort_index
