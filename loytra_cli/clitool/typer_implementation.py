#!/usr/bin/env python3

import typer
from typing import Optional
from loytra_cli.clitool.actions import LoytraCliActions
import loytra_cli.dmapi_sim.dmapi_client as dmapi_client
from loytra_common.options import options
from loytra_common import log_factory



actions: Optional[LoytraCliActions] = None
app = typer.Typer(help="Loytra")


@app.command()
def install(module_name, hash = None, github_token = None):
    
    if actions is None:
        return
    actions.install(module_name, hash, github_token)


@app.command()
def uninstall(module_name):
    if actions is None:
        return
    actions.uninstall(module_name)


@app.command()
def start(module_service_name):
    if actions is None:
        return
    actions.start(module_service_name)


@app.command()
def stop(module_service_name: Optional[str] = typer.Argument(None)):
    if actions is None:
        return
    actions.stop(module_service_name)


@app.command()
def restart(module_service_name: Optional[str] = typer.Argument(None)):
    if actions is None:
        return
    actions.restart(module_service_name)


@app.command()
def enable(module_service_name):
    if actions is None:
        return
    actions.enable(module_service_name)


@app.command()
def disable(module_service_name):
    if actions is None:
        return
    actions.disable(module_service_name)


@app.command()
def logs(module_service_name):
    if actions is None:
        return
    actions.logs(module_service_name)


@app.command()
def debug(module_service_name):
    if actions is None:
        return
    actions.debug(module_service_name)


@app.command()
def run(module_service_name):
    if actions is None:
        return
    actions.run(module_service_name)


@app.command()
def sync(module_package_name):
    if actions is None:
        return
    actions.sync(module_package_name)


@app.command()
def unsync(module_package_name):
    if actions is None:
        return
    actions.unsync(module_package_name)


@app.command()
def status():
    if actions is None:
        return
    actions.status()


@app.command()
def list():
    if actions is None:
        return
    actions.list()


@app.command()
def update(module_name: Optional[str] = typer.Argument(None)):
    if actions is None:
        return
    actions.update(module_name)


@app.command()
def clean():
    if actions is None:
        return
    actions.clean()

@app.command()
def api_sim(definition: Optional[str] = typer.Argument(None)):
    if definition is None:
        return
    dmapi_client.run(definition)


@app.callback()
def main(verbose: bool = False):
    global actions
    options.verbose = verbose
    if actions is None:
        actions = LoytraCliActions()
