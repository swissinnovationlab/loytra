import os.path
from loytra_modules._module_spec import LoytraModule, LoytraModuleInstance, LoytraModuleReference
from loytra_modules._util import get_loytra_parent_path
from loytra_common.utils import get_file_list_in_path, check_if_path_exists

LOYTRA_MODULE_FILE = "__loytra_module__.py"


def _get_loytra_module_folder_path(folder_name):
    return f"{get_loytra_parent_path()}/{folder_name}"


def _get_loytra_module_file_path(folder_name):
    return f"{_get_loytra_module_folder_path(folder_name)}/{LOYTRA_MODULE_FILE}"


def _get_folder_names_in_loytra_parent_path():
    return get_file_list_in_path(get_loytra_parent_path())


def _get_loytra_module_from_file_path(module_name, file_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None:
        return None

    foo = importlib.util.module_from_spec(spec)

    #TODO: check if this is needed, as it overwrites actual packages
    #import sys
    #sys.modules[module_name] = foo

    if spec.loader is None:
        return None

    spec.loader.exec_module(foo)
    return foo


def _parse_loytra_module_export(loytra_module_export) -> list[LoytraModule]:
    result: list[LoytraModule] = []

    # load module instance
    module_instance = None
    try:
        module_instance = loytra_module_export.__loytra_module__
    except:
        module_instance = None

    if module_instance is not None:
        if isinstance(module_instance, LoytraModuleInstance):
            result.append(module_instance)
        else:
            raise RuntimeError("__loytra_module__ must be of 'LoytraModuleInstance' type!")

    # load module references
    module_references = None
    try:
        module_references = loytra_module_export.__loytra_references__
    except:
        module_references = None
    if module_references is not None:
        if isinstance(module_references, list):
            for ref in module_references:
                if isinstance(ref, LoytraModuleReference):
                    result.append(ref)
                else:
                    raise RuntimeError("__loytra_references must be a list of 'LoytraModuleReference' objects!")
        else:
            raise RuntimeError("__loytra_references must be a list of 'LoytraModuleReference' objects!")

    return result


def _get_loytra_modules() -> list[LoytraModule]:
    loytra_modules: list[LoytraModule] = []
    for folder_name in _get_folder_names_in_loytra_parent_path():
        file_path = _get_loytra_module_file_path(folder_name)
        if check_if_path_exists(file_path):
            try:
                module_export = _get_loytra_module_from_file_path(folder_name, file_path)
                if module_export is None:
                    print(f"Failed to load module from {folder_name}")
                    continue
                loytra_modules.extend(_parse_loytra_module_export(module_export))
            except Exception as e:
                print(f"Error importing loytra module {folder_name} with {e}")

    result: list[LoytraModule] = []

    # take all instances
    for module in loytra_modules:
        if isinstance(module, LoytraModuleInstance):
            result.append(module)

    # filter out references which are already installed
    for module in loytra_modules:
        if isinstance(module, LoytraModuleReference):
            if not os.path.exists(module.moduler.install_location):
                result.append(module)

    return result


def find_loytra_modules() -> dict[str, LoytraModule]:
    result: dict[str, LoytraModule] = {}
    modules = _get_loytra_modules()
    modules = sorted(modules, key=lambda m: m.sort_index if m.sort_index >= 0 else 999999)
    for module in modules:
        result[module.module_name] = module
    return result


def get_loytra_modules_by_folder_name(folder_name):
    file_path = _get_loytra_module_file_path(folder_name)
    module_export = _get_loytra_module_from_file_path(folder_name, file_path)
    if module_export is None:
        print(f"Failed to load module from {folder_name}::{file_path}")
        return []
    return _parse_loytra_module_export(module_export)
