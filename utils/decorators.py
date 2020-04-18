from discord.ext.commands import check

from utils import permissions


def can_run(*, module_source=None, command=None):
    def predicate(ctx):
        return permissions.fire_run_check(ctx, module_source=module_source, command=command)

    return check(predicate)
