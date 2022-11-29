from git.repo import Repo
from git.exc import InvalidGitRepositoryError, NoSuchPathError
from loytra_common import log_factory
from loytra_common.utils import run_bash_cmd, check_if_path_exists, get_full_path, TCOL, remove_path
from loytra_modules._util import get_loytra_parent_path


class Moduler:
    def __init__(self, package=None, module=None, url=None, hash=None, github_token=None):
        self.package = package
        self.module = module
        self.url = url
        self.hash = hash
        self.github_token = github_token
        self.install_location = self._get_install_location_from_url(self.url)
        self.logger = log_factory.get(name="svs_moduler", tag="MODULER")

    def _is_repo(self, install_location):
        try:
            Repo(get_full_path(install_location))
            return True
        except (InvalidGitRepositoryError, NoSuchPathError):
            return False

    def _get_github_token_interaction(self, github_token):
        return {"Username": ["", github_token][github_token != None], "Password": ""}

    def _fetch_repo(self, install_location, github_token=None):
        if not self._is_repo(install_location):
            return None
        cmd = f"git -C {get_full_path(install_location)} fetch"
        interaction = self._get_github_token_interaction(github_token)
        return run_bash_cmd(cmd, interaction=interaction, return_lines=False, return_code=True) == 0

    def _get_git_tag(self, repo):
        tag = next((tag for tag in repo.tags if tag.commit == repo.head.commit), None)
        if tag:
            return str(tag)
        return tag

    def _get_git_branch_name(self, repo):
        if repo.head.is_detached:
            return None
        return repo.active_branch.name

    def _get_git_sha(self, repo):
        sha = repo.head.commit.hexsha
        short_sha = repo.git.rev_parse(sha, short=7)
        return short_sha

    def _get_commits(self, repo, pattern):
        return [c for c in repo.iter_commits(pattern)]

    def _count_commits(self, repo, pattern):
        return len(self._get_commits(repo, pattern))

    def _get_repo_local_version(self, repo):
        tag = self._get_git_tag(repo)
        if not repo.head.is_detached:
            return self._get_git_branch_name(repo)
        elif tag:
            return tag
        else:
            return self._get_git_sha(repo)

    def _get_repo_status(self, install_location, request_version=None):
        if not self._is_repo(install_location):
            return None
        status = ""
        repo = Repo(get_full_path(install_location))
        branch = self._get_git_branch_name(repo)
        is_git_repo_with_changes_to_be_committed = len(repo.index.diff("HEAD")) > 0
        is_git_repo_modified = len(repo.index.diff(None)) > 0
        is_git_repo_with_untracked_files = len(repo.untracked_files) > 0
        is_git_repo_behind = bool(branch is not None and self._count_commits(repo, '%s..origin/%s' % (branch, branch)) > 0)
        is_git_repo_ahead = bool(branch is not None and self._count_commits(repo, 'origin/%s..%s' % (branch, branch)) > 0)
        repo_hash = self._get_repo_local_version(repo)

        if request_version != None and repo_hash != request_version:
            status += "%s%s%s -> %s%s%s " % (TCOL.FAIL, repo_hash, TCOL.END, TCOL.FAIL, request_version, TCOL.END)
        else:
            status += "%s%s%s " % (TCOL.WARNING, repo_hash, TCOL.END)

        status += ("", TCOL.HEADER + "B" + TCOL.END)[is_git_repo_behind]
        status += ("", TCOL.HEADER + "A" + TCOL.END)[is_git_repo_ahead]

        status += ("", TCOL.OKBLUE + "M" + TCOL.END)[is_git_repo_modified]
        status += ("", TCOL.OKBLUE + "S" + TCOL.END)[is_git_repo_with_changes_to_be_committed]
        status += ("", TCOL.OKBLUE + "U" + TCOL.END)[is_git_repo_with_untracked_files]
        return status.rstrip()

    def _get_package_from_url(self, url):
        return url.split('/')[-1]

    def _get_install_location_from_url(self, url):
        return f"{get_loytra_parent_path()}/{self._get_package_from_url(url)}"

    def _clone_repo(self, url, request_version=None, github_token=None):
        self.logger.info(f"clone_repo {github_token != None}@{url}@{request_version}")
        install_location = self._get_install_location_from_url(url)
        if self._is_repo(install_location):
            return True
        github_token_str = ["", f"{github_token}@"][github_token != None]
        cmd = f"git clone https://{github_token_str}{url} {install_location}"
        if run_bash_cmd(cmd, self.logger.debug, return_lines=False, return_code=True) == 0:
            if request_version != None:
                repo = Repo(self._get_install_location_from_url(url))
                repo_hash = self._get_repo_local_version(repo)
                if repo_hash != request_version:
                    return self._checkout_repo(url, request_version, github_token)
                else:
                    return True
            else:
                return True
        else:
            return False

    def _checkout_repo(self, install_location, request_version=None, github_token=None):
        self.logger.info(f"checkout_repo {github_token != None}@{install_location}@{request_version}")
        cmd = f"git -C {install_location} checkout {request_version}"
        interaction = self._get_github_token_interaction(github_token)
        return run_bash_cmd(cmd, self.logger.debug, interaction=interaction, return_lines=False, return_code=True) == 0

    def _clean_repo(self, install_location):
        self.logger.info(f"clean_repo {install_location}")
        cmd = []
        cmd.append(f"git -C {install_location} reset")
        cmd.append(f"git -C {install_location} checkout -- .")
        cmd.append(f"git -C {install_location} clean -dfx")
        success_count = 0
        for c in cmd:
            success_count += 1 if run_bash_cmd(c, return_lines=False, return_code=True) else 0
        return success_count == 0

    def _pull_repo(self, install_location, github_token=None):
        self.logger.info(f"pull_repo {github_token != None}@{install_location}")
        cmd = f"git -C {install_location} pull"
        interaction = self._get_github_token_interaction(github_token)
        run_bash_cmd(cmd, self.logger.debug, interaction=interaction)

    def _update_repo(self, install_location, request_version=None, github_token=None):
        self.logger.info(f"update_repo {github_token != None}@{install_location}@{request_version}")
        repo = Repo(install_location)
        if repo:
            if self._get_repo_local_version(repo) != request_version:
                self._checkout_repo(install_location, request_version)
            if self._get_repo_local_version(repo) != request_version:
                self.logger.info(f"  Could not checkout, trying to fetch")
                self._fetch_repo(install_location)
                self._checkout_repo(install_location, request_version)
            if self._get_repo_local_version(repo) != request_version:
                self.logger.info(f"  Could not checkout, wrong hash or unclean repo")
            if self._get_git_branch_name(repo):
                self._pull_repo(install_location, github_token)
        return None

    def _remove_repo(self, install_location):
        self.logger.info(f"remove_repo {install_location}")
        remove_path(install_location)
        return check_if_path_exists(install_location) == False

    def is_installed(self):
        return self._is_installed_pip() and self._is_repo(self.install_location)

    def install(self):
        return self._clone_repo(self.url, self.hash, self.github_token) and self._install_pip_editable()

    def download_module(self):
        return self._clone_repo(self.url, self.hash, self.github_token)

    def install_module(self):
        return self._install_pip_editable()

    def uninstall(self):
        return self._uninstall_pip() and self._remove_repo(self.install_location)

    def _get_local_version(self):
        return self._get_repo_local_version(Repo(self.install_location))

    def get_status(self):
        repo_status = self._get_repo_status(self.install_location, self.hash)
        pip_status = self._get_status_pip()
        if pip_status is None:
            return f"{repo_status}"
        else:
            return f"{repo_status} {pip_status}"

    def fetch(self):
        return self._fetch_repo(self.install_location, self.github_token)

    def _install_pip_editable(self):
        if self.module == None:
            return True
        # cmd = f"pip install -e {self.install_location}"
        cmd = f"pip install --prefix=$(python -m site --user-base) --editable {self.install_location}"
        return run_bash_cmd(cmd, self.logger.debug, return_lines=False, return_code=True) == 0

    def update(self, request_version=None):
        return self._update_repo(self.install_location, request_version, self.github_token) and self._install_pip_editable()

    def _is_installed_pip(self):
        if self.module == None:
            return True
        # reload sys.path
        import site
        from importlib import reload
        reload(site)

        # check if module is in sys.path
        from importlib import util as imput
        return imput.find_spec(self.module) is not None

    def _uninstall_pip(self):
        if self.module == None:
            return True
        cmd = f"pip uninstall {self.package}"
        interaction = {"Proceed (": "y"}
        return run_bash_cmd(cmd, self.logger.debug, interaction=interaction, return_lines=False, return_code=True) == 0

    def _get_status_pip(self):
        if self.module == None:
            return None
        return [f"{TCOL.FAIL}pip{TCOL.END}", f"{TCOL.OKGREEN}PIP{TCOL.END}"][self._is_installed_pip()]

    def clean(self):
        self._clean_repo(self.install_location)


if __name__ == "__main__":
    import readline
    import code

    readline.parse_and_bind("tab: complete")
    code.interact(local=locals())
