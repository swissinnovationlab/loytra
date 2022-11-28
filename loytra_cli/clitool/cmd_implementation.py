import cmd
import readline
from loytra_common.utils import TCOL
from loytra_cli.clitool.actions import LoytraCliActions

readline.set_completer_delims(readline.get_completer_delims().replace('/', ''))


class Commander(cmd.Cmd):
    _hidden_methods = ("do_EOF", "do_help")

    def __init__(self, actions: LoytraCliActions):
        super().__init__()
        self._actions = actions
        self.set_prompt()

    # def cmdloop(self, intro=None):
    #     print('cmdloop(%s)' % intro)
    #     return cmd.Cmd.cmdloop(self, intro)
    #
    # def preloop(self):
    #     print('preloop()')
    #
    # def postloop(self):
    #     print('postloop()')
    #
    # def parseline(self, line):
    #     print('parseline(%s) =>' % line)
    #     ret = cmd.Cmd.parseline(self, line)
    #     print(ret)
    #     return ret
    #
    # def onecmd(self, s):
    #     print('onecmd(%s)' % s)
    #     return cmd.Cmd.onecmd(self, s)
    #
    # def emptyline(self):
    #     print('emptyline()')
    #     return cmd.Cmd.emptyline(self)
    #
    # def default(self, line):
    #     print('default(%s)' % line)
    #     return cmd.Cmd.default(self, line)
    #
    # def precmd(self, line):
    #     print('precmd(%s)' % line)
    #     return cmd.Cmd.precmd(self, line)

    def get_modules(self):
        return list(self._actions.modules().keys())

    def get_services(self):
        result = []
        loytra_modules = self._actions.modules()
        for m in loytra_modules:
            services = loytra_modules[m].services
            for s in services:
                result.append(f"{m}/{s}")
        return result

    def get_packages(self):
        result = []
        return result

    def _find_matches(self, text: str, possibilities: list[str]) -> list[str]:
        return list(filter(lambda it: text in it, possibilities))

    def check_completion(self, text, possibilities):
        if not text:
            completions = possibilities[:]
        else:
            completions = self._find_matches(text, possibilities)
        return completions

    def set_prompt(self):
        self.prompt = f"{TCOL.BOLD}[LOYTRA]{TCOL.END}# "

    def postcmd(self, stop, line):
        self.set_prompt()
        return cmd.Cmd.postcmd(self, stop, line)

    def do_EOF(self, line):
        return True

    def postloop(self):
        print()

    def get_names(self):
        return [n for n in dir(self.__class__) if n not in self._hidden_methods]

    def do_install(self, line):
        self._actions.install(line)

    def complete_install(self, text, line, begidx, endidx):
        return self.check_completion(text, self.get_modules())

    def do_uninstall(self, line):
        self._actions.uninstall(line)

    def complete_uninstall(self, text, line, begidx, endidx):
        return self.check_completion(text, self.get_modules())

    def do_start(self, line):
        self._actions.start(line)

    def complete_start(self, text, line, begidx, endidx):
        return self.check_completion(text, self.get_services())

    def do_stop(self, line):
        self._actions.stop(line)

    def complete_stop(self, text, line, begidx, endidx):
        return self.check_completion(text, self.get_services())

    def do_restart(self, line):
        self._actions.restart(line)

    def complete_restart(self, text, line, begidx, endidx):
        return self.check_completion(text, self.get_services())

    def do_enable(self, line):
        self._actions.enable(line)

    def complete_enable(self, text, line, begidx, endidx):
        return self.check_completion(text, self.get_services())

    def do_disable(self, line):
        self._actions.disable(line)

    def complete_disable(self, text, line, begidx, endidx):
        return self.check_completion(text, self.get_services())

    def do_logs(self, line):
        self._actions.logs(line)

    def complete_logs(self, text, line, begidx, endidx):
        return self.check_completion(text, self.get_services())

    def do_debug(self, line):
        self._actions.debug(line)

    def complete_debug(self, text, line, begidx, endidx):
        return self.check_completion(text, self.get_services())

    def do_run(self, line):
        self._actions.run(line)

    def complete_run(self, text, line, begidx, endidx):
        return self.check_completion(text, self.get_services())

    def do_sync(self, line):
        self._actions.sync(line)

    def complete_sync(self, text, line, begidx, endidx):
        return self.check_completion(text, self.get_packages())

    def do_unsync(self, line):
        self._actions.unsync(line)

    def complete_unsync(self, text, line, begidx, endidx):
        return self.check_completion(text, self.get_packages())

    def do_status(self, line):
        self._actions.status()

    def do_list(self, line):
        self._actions.list()

    def do_update(self, line):
        self._actions.update()

    def do_clean(self, line):
        self._actions.clean()

def run():
    commander = Commander(LoytraCliActions())
    commander.cmdloop()
