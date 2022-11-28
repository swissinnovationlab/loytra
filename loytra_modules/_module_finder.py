from loytra_modules._module_spec import LoytraModule
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
    import sys
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    foo = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = foo
    spec.loader.exec_module(foo)
    return foo.__loytra_module__


def _parse_loytra_module_export(loytra_module_export) -> list[LoytraModule]:
    result: list[LoytraModule] = []
    if isinstance(loytra_module_export, list):
        for item in loytra_module_export:
            if isinstance(item, LoytraModule):
                result.append(item)
    elif isinstance(loytra_module_export, LoytraModule):
        result.append(loytra_module_export)
    else:
        raise RuntimeError("Invalid module export type!")
    return result


def _get_loytra_modules() -> list[LoytraModule]:
    loytra_modules: list[LoytraModule] = []
    for folder_name in _get_folder_names_in_loytra_parent_path():
        file_path = _get_loytra_module_file_path(folder_name)
        if check_if_path_exists(file_path):
            try:
                module_export = _get_loytra_module_from_file_path(folder_name, file_path)
                loytra_modules.extend(_parse_loytra_module_export(module_export))
            except Exception as e:
                print(f"Error importing loytra module with {e}")
    return loytra_modules


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
    return _parse_loytra_module_export(module_export)
