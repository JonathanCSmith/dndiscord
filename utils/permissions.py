from discord.ext import commands

permission_interested_module = list()


class CommandRunError(commands.CommandError):
    def __init__(self, detail, *args, **kwargs):
        self.detail = detail


def fire_run_check(ctx, module_source=None, command=None):
    for module in permission_interested_module:
        return module.run_check(ctx, module_source=module_source, command=command)


def add_permission_interested_module(module):
    permission_interested_module.append(module)


class PermissionsMixin:
    def run_check(self, ctx, module_source=None, command=None):
        pass
