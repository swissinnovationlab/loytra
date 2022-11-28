from pathlib import Path

def get_loytra_parent_path():
    return "/".join(str(Path(__file__).resolve().parent).split("/")[:-2])

