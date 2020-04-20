from functools import wraps

from discord.ext import commands

permission_interested_module = list()


class CommandRunError(commands.CommandError):
    def __init__(self, detail, *args, **kwargs):
        self.detail = detail


def fire_run_check(ctx, module_source=None, command=None):
    can_run = True
    for module in permission_interested_module:
        can_run &= module.run_permissions_check(ctx, module_source=module_source, command=command)

    return can_run


def add_permission_interested_module(module):
    permission_interested_module.append(module)
