import os

class Options:
    verbose: bool = False

options = Options()

loytra_verbose = os.environ.get("LOYTRA_VERBOSE", "0")
if loytra_verbose == "1":
    options.verbose = True
