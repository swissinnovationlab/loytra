def _call_module_function(module_name, function_name=""):
    from loytra_common import log_factory
    log_factory.set_log_timestamp(False)

    import importlib
    module = importlib.import_module(module_name)
    if len(function_name) > 0:
        function = getattr(module, function_name)
        function()


def run_systemd_service():
    import sys
    import sdnotify

    n = sdnotify.SystemdNotifier()
    n.notify("READY=1")
    if len(sys.argv) >= 3:
        _call_module_function(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 2:
        _call_module_function(sys.argv[1])
    else:
        pass

def get_service_run_command(module: str, function: str = ""):
    result = "%h/.local/bin/loytra-service-runner"
    result = result + f" '{module}'"
    if len(function) > 0:
        result = result + f" '{function}'"
    return result

