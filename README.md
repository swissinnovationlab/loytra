# LOYTRA - Linux Os pYThon Repository Assistant
Use it to clone and pip install python git projects. Adds support for "syncing" and "unsyncing" custom packages and easily setup and control systemd services provided by an installed repo.

## Intro
To be able to use a git repo as a `loytra` controlled lib, add a `__loytra_module__.py` file to the root of your lib repo. As `loytra` is managed by itself, you can look at [__loytra_module__.py](__loytra_module__.py) to see an example.

## Directory structure
All repos controlled by `loytra` have to be located in the same parent directory as `loytra` itself.

## Setup
### Installation
Make sure that you have `python` and `pip` installed.
Clone this repo and install `loytra` and its' dependencies using `pip install -e ./` in this repos directory.
The `loytra` CLI app should now be available in your $PATH.

### Removal
Use `pip uninstall loytra` to remove it. Remove any leftover files using:
```sh
rm -r loytra.egg-info
rm ~/.local/bin/loytra*
rm -r ~/.local/lib/python3.10/site-packages/loytra*
```

## Usage
Run `loytra` in your terminal to start the integrated CLI or use the available commands directly using `loytra [COMMAND]`.

## Commands
`install [HTTPS_GIT_REPO]` - clone and pip install a repo
...

## DMCloud API client simulator
See [API_SIM.md](API_SIM.md)

## [License](LICENSE)
This program is free software.
It is licensed under the GNU GPL version 3 or later.
That means you are free to use this program for any purpose;
free to study and modify this program to suit your needs;
and free to share this program or your modifications with anyone.
If you share this program or your modifications
you must grant the recipients the same freedoms.
To be more specific: you must share the source code under the same license.
For details see https://www.gnu.org/licenses/gpl-3.0.html
