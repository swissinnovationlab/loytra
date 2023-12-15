import sys, os, os.path
import importlib, pkgutil

def import_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except:
        import traceback
        traceback.print_exc()
        return None

def _iter_modules(path: str, prefix: str, recursive: bool = True):
    for (loader, name, ispkg) in pkgutil.iter_modules([path]):
        modulepath = f"{prefix}{name}"
        yield modulepath

    for subdir in os.listdir(path):
        dirpath = os.path.join(path, subdir)
        if not os.path.isdir(dirpath):
            continue
        if subdir == '__pycache__':
            continue
        if recursive:
            yield from _iter_modules(dirpath, prefix + f"{subdir}.")

def get_all_modules(module_name: str, recursive: bool = True) -> list[str]:
    result: list[str] = []
    module = import_module(module_name)
    result.append(module_name)

    if module is not None:
        module_file = module.__file__
        if module_file is not None:
            path = os.path.dirname(module_file)
            for submodule in _iter_modules(path, module_name + '.', recursive):
                if submodule not in result:
                    result.append(submodule)

    return result

def get_imported_modules():
    return [key for key, value in sys.modules.items()]

