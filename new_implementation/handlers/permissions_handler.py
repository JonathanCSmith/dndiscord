class PermissionContext:
    ANY = 0
    GUILD = 1
    GAME = 2


class PermissionLevel:
    ANY = 0
    SPECIAL_ROLE = 1
    PARTY = 2
    GAME_MASTER = 3
    ADMINISTRATOR = 4


class PermissionsHandler:
    def __init__(self, application):
        self.application = application

    async def check_inactive_game_permissions_for_user(self, ctx, game_name, permission_name, permissions_level=PermissionLevel.ADMINISTRATOR, elevated_roles=None):
        # Get the requested game - the game check takes precedence over the admin check as usually commands that call this will not function without a game
        game = await self.application.get_game(ctx, game_name)
        if not game:
            return False, "You cannot do this as there is no game of that name."

        # If the user is an administrator we ALWAYS allow
        if ctx.author.guild_permissions.administrator:
            return True, ""

        # Quick check to format the special roles
        if not elevated_roles:
            elevated_roles = list()
        elif not isinstance(elevated_roles, list):
            elevated_roles = [elevated_roles]

        # Check if our user is in one of the special roles provided:
        for special_role in elevated_roles:
            if special_role in ctx.author.roles:
                return True, ""

        # Get game permission overrides
        overwritten_permissions_level = game.get_permission_level(permission_name)
        if overwritten_permissions_level >= 0:
            permissions_level = overwritten_permissions_level

        # If it open to anyone
        if permissions_level == PermissionLevel.ANY:
            return True, ""

        # This permissions level allows any member of the party to run the command
        if permissions_level <= PermissionLevel.PARTY:
            if game.is_adventurer(ctx.author.id):
                return True, ""

        # This permissions level only allows for the gm or elevated roles
        if permissions_level <= PermissionLevel.GAME_MASTER:

            # Check if the user is the gm of the game
            if game.is_gm(ctx.author.id):
                return True, ""

        # If the permissions level == 3 or if it was an unregistered permission and the user is not an admin
        return False, "You do not have permission to do this."

    async def check_active_game_permissions_for_user(self, ctx, permission_name, permissions_level=PermissionLevel.ADMINISTRATOR, elevated_roles=None):
        # Get the requested game - the game check takes precedence over the admin check as usually commands that call this will not function without a game
        game = self.application.get_active_game_for_context(ctx)
        if not game:
            return False, "You cannot do this as there is no game running in your guild."

        # If the user is an administrator we ALWAYS allow
        if ctx.author.guild_permissions.administrator:
            return True, ""

        # Quick check to format the special roles
        if not elevated_roles:
            elevated_roles = list()
        elif not isinstance(elevated_roles, list):
            elevated_roles = [elevated_roles]

        # Check if our user is in one of the special roles provided:
        for special_role in elevated_roles:
            if special_role in ctx.author.roles:
                return True, ""

        # Get game permission overrides
        overwritten_permissions_level = game.get_permission_level(permission_name)
        if overwritten_permissions_level >= 0:
            permissions_level = overwritten_permissions_level

        # If it open to anyone
        if permissions_level == PermissionLevel.ANY:
            return True, ""

        # This permissions level allows any member of the party to run the command
        if permissions_level <= PermissionLevel.PARTY:
            if game.is_adventurer(ctx.author.id):
                return True, ""

        # This permissions level only allows for the gm or elevated roles
        if permissions_level <= PermissionLevel.GAME_MASTER:

            # Check if the user is the gm of the game
            if game.is_gm(ctx.author.id):
                return True, ""

        # If the permissions level == 3 or if it was an unregistered permission and the user is not an admin
        return False, "You do not have permission to do that."

    async def check_guild_permissions_for_user(self, ctx, permission_name, permissions_level=PermissionLevel.ADMINISTRATOR, elevated_roles=None):
        # If the user is an administrator we ALWAYS allow
        if ctx.author.guild_permissions.administrator:
            return True, ""

        # Quick check to format the special roles
        if not elevated_roles:
            elevated_roles = list()
        elif not isinstance(elevated_roles, list):
            elevated_roles = [elevated_roles]

        # Check if our user is in one of the special roles provided:
        for special_role in elevated_roles:
            if special_role in ctx.author.roles:
                return True, ""

        # Obtain any registered permission overwrites
        guild_data = await self.application.get_guild_data_for_context(ctx)
        overwritten_permissions_level = guild_data.get_permission_level(permission_name)
        if overwritten_permissions_level >= 0:
            permissions_level = overwritten_permissions_level

        # If it open to anyone
        if permissions_level == PermissionLevel.ANY:
            return True, ""

        # If the permissions level == 3 or if it was an unregistered permission and the user is not an admin
        return False, "You do not have permission to do this."

    async def set_guild_permissions_for_context(self, ctx, permissions_name, permissions_level):
        guild_data = await self.application.get_guild_data_for_context(ctx)
        guild_data.set_permissions_level(permissions_name, permissions_level)
        return await self.__save_guild_data(ctx, guild_data)

    async def set_game_permissions_for_context(self, ctx, permissions_name, permissions_level):
        game = self.application.get_active_game_for_context(ctx)
        if game:
            game.set_permissions_level(permissions_name, permissions_level)
