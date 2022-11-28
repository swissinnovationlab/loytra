#!/usr/bin/env python3

import sys

def run():
    if len(sys.argv) > 1:
        import loytra_cli.clitool.typer_implementation as t
        t.app()
    else:
        import loytra_cli.clitool.cmd_implementation as c
        c.run()

