import discord
from discord.ext.commands import Command

from new_implementation.core.permissions_handler import PermissionContext, PermissionLevel
from new_implementation.utils import utils


class DnDiscordCommand(Command):
    def __init__(
            self,
            func,
            permission_id=None,
            default_minimum_access=PermissionLevel.ADMINISTRATOR,
            is_server_required=True,
            default_permitted_roles=None,
            **kwargs
    ):
        super().__init__(func, **kwargs)

        # Checks
        if permission_id is None or not isinstance(permission_id, str):
            permission_id = self.name

        # Get the permission properties
        self.permission_id = permission_id
        self.default_minimum_access_level_to_execute = default_minimum_access
        self.is_server_required = is_server_required
        if default_permitted_roles is None:
            default_permitted_roles = set()
        self.default_permitted_roles = default_permitted_roles

    def set_default_minimum_level_to_execute(self, engine, invocation_context, level):
        self.default_minimum_access_level_to_execute = level

        # Get the permission holder
        guild_data = await engine.get_guild_data_for_context(invocation_context)
        default_permissions = guild_data.get_default_permissions_for(self.permission_id)
        default_permissions.set_minimum_execution_level(level)
        await engine.save_guild_data_for_context(invocation_context)

    def add_default_role(self, engine, invocation_context, role):
        self.default_permitted_roles.append(role.name)

        # Get the permission holder
        guild_data = await engine.get_guild_data_for_context(invocation_context)
        default_permissions = guild_data.get_default_permissions_for(self.permission_id)
        default_permissions.add_allowed_role(role)
        await engine.save_guild_data_for_context(invocation_context)

    def remove_default_role(self, engine, invocation_context, role):
        self.default_permitted_roles.remove(role.name)

        # Get the permission holder
        guild_data = await engine.get_guild_data_for_context(invocation_context)
        default_permissions = guild_data.get_default_permissions_for(self.permission_id)
        default_permissions.remove_allowed_role(role)
        await engine.save_guild_data_for_context(invocation_context)

    async def check_can_run(self, engine, invocation_context, permission_holder_identifier: str = None, check_permission_holder_for_permissions=True):
        if engine.is_memory_mutex_locked():
            return False, "Please retry this command again later. The bot is currently undergoing a memory purge."

        # Check if the execution context is correct (i.e. if we require a guild there must be guild info)
        if self.is_server_required and not invocation_context.guild:
            return False, "This command can only be run from a server."

        # If this is a DM and a non server specific command, we currently just allow
        if not self.is_server_required:
            return True, ""

        # Guild data
        guild_data = await engine.get_guild_data_for_context(invocation_context)

        # We ALWAYS allow FULL admins to do things (except the above)
        if invocation_context.author.guild_permissions.administrator:
            return True, ""

        # We can check for other types of admins, again these are always allowed
        administrative_roles = guild_data.get_administrator_roles()
        for administrative_role in administrative_roles:
            if self.__check_role_by_name(engine, invocation_context, name=administrative_role):
                return True, ""

        # This flag prevents allows us to conditionally not check this information. Useful for function chaining from child implementations
        if check_permission_holder_for_permissions:
            permissions_data = guild_data.get_permissions_for(self.permission_id)
            execution_permitted_level = permissions_data.get_minimum_execution_level()
            if execution_permitted_level < 0:
                execution_permitted_level = self.default_minimum_access_level_to_execute

            # Special roles are accepted only if this command's permission level < ADMIN
            if execution_permitted_level <= PermissionLevel.SPECIAL_ROLE:
                allowed_roles = self.default_permitted_roles.union(permissions_data.get_allowed_roles())
                for role in allowed_roles:
                    if self.__check_role_by_name(engine, invocation_context, name=role):
                        return True, ""

            # If anyone can run
            if execution_permitted_level == PermissionLevel.ANY:
                return True, ""

        return False, "You do not have permission to do this."

    def change_permission_minimum_execution_level(self, engine, invocation_context, level, permission_holder_identifier=None):
        guild_data = await engine.get_guild_data_for_context(invocation_context)
        permissions_data = guild_data.get_permissions_for(self.permission_id)
        permissions_data.set_minimum_execution_level(level)
        await engine.save_guild_data_for_context(invocation_context)
        return True

    def add_permitted_role(self, engine, invocation_context, role, permission_holder_identifier=None):
        guild_data = await engine.get_guild_data_for_context(invocation_context)
        permissions_data = guild_data.get_permissions_for(self.permission_id)
        permissions_data.add_allowed_role(role)
        await engine.save_guild_data_for_context(invocation_context)
        return True

    def remove_permitted_role(self, engine, invocation_context, role, permission_holder_identifier=None):
        guild_data = await engine.get_guild_data_for_context(invocation_context)
        permissions_data = guild_data.get_permissions_for(self.permission_id)
        permissions_data.remove_allowed_role(role)
        await engine.save_guild_data_for_context(invocation_context)
        return True

    async def __check_role_by_name(self, engine, invocation_context, name):
        role = discord.utils.get(invocation_context.guild.roles, name=name)
        return role in invocation_context.author.roles


class GameAwareCommand(DnDiscordCommand):
    def __init__(self, requires_active_game=False, **kwargs):
        super().__init__(**kwargs)
        self.requires_active_game = requires_active_game

    async def check_can_run(self, engine, invocation_context, permission_holder_identifier: str = None, check_permission_holder_for_permissions=True):
        # First we run it in the parent context - this will tell us if the user can exectute this using guild logic
        guild_specific_outcome, information = super().check_can_run(engine, invocation_context, permission_holder_identifier=permission_holder_identifier, check_permission_holder_for_permissions=False)
        if guild_specific_outcome:
            return guild_specific_outcome, information

        # We need a game here
        game_data = self.__get_game_data(engine, invocation_context, permission_holder_identifier)
        if not game_data:
            return False, "This supplied game pointer could not find a matching game, perhaps you omitted it from the command?"

        # Load the game specific permissions if desired
        if check_permission_holder_for_permissions:
            permissions_data = game_data.get_permissions_for(self.permission_id)
            execution_permitted_level = permissions_data.get_minimum_execution_level()
            if execution_permitted_level < 0:
                execution_permitted_level = self.default_minimum_access_level_to_execute
            user_id = utils.get_user_id_from_context(invocation_context)

            # If anyone can run
            if execution_permitted_level == PermissionLevel.ANY:
                return True, ""

            # Check game master
            if execution_permitted_level <= PermissionLevel.OWNER:
                if game_data.is_owner(user_id):
                    return True, "You are the GM for this game."

            # Check party member
            if execution_permitted_level <= PermissionLevel.MEMBER:
                if game_data.is_member(user_id):
                    return True, "You are a party member for this game."

            # Special roles are accepted only if this command's permission level < ADMIN
            if execution_permitted_level <= PermissionLevel.SPECIAL_ROLE:
                allowed_roles = self.default_permitted_roles.union(permissions_data.get_allowed_roles())
                for role in allowed_roles:
                    if self.__check_role_by_name(engine, invocation_context, name=role):
                        return True, ""

        return False, "You do not have permission to do this."

    def change_permission_minimum_execution_level(self, engine, invocation_context, level, permission_holder_identifier=None):
        # We need a game here
        game_data = self.__get_game_data(engine, invocation_context, permission_holder_identifier)
        if not game_data:
            return False, "This supplied game pointer could not find a matching game, perhaps you omitted it from the command?"

        # Adjust the game specific permissions
        permissions_data = game_data.get_permissions_for(self.permission_id)
        permissions_data.set_minimum_execution_level(level)
        await engine.save_game(invocation_context, game_data)
        return True

    def add_permitted_role(self, engine, invocation_context, role, permission_holder_identifier=None):
        # We need a game here
        game_data = self.__get_game_data(engine, invocation_context, permission_holder_identifier)
        if not game_data:
            return False, "This supplied game pointer could not find a matching game, perhaps you omitted it from the command?"

        permissions_data = game_data.get_permissions_for(self.permission_id)
        permissions_data.add_allowed_role(role)
        await engine.save_game(invocation_context, game_data)
        return True

    def remove_permitted_role(self, engine, invocation_context, role, permission_holder_identifier=None):
        # We need a game here
        game_data = self.__get_game_data(engine, invocation_context, permission_holder_identifier)
        if not game_data:
            return False, "This supplied game pointer could not find a matching game, perhaps you omitted it from the command?"

        permissions_data = game_data.get_permissions_for(self.permission_id)
        permissions_data.remove_allowed_role(role)
        await engine.save_game(invocation_context, game_data)
        return True

    def __get_game_data(self, engine, invocation_context, game_name):
        # If we haven't gotten a pointr for the game, we can try to infer the current active game
        if not game_name:
            if self.requires_active_game:
                return None
            else:
                game_data = engine.get_active_game_for_context(invocation_context)
        else:
            game_data = await engine.get_game(invocation_context, game_name)

        return game_data


# This is legacy code but i may need it
class DnDiscordCommand2(Command):
    def __init__(self, func, **kwargs):
        self.instance = None
        self.owner = None
        super().__init__(func, **kwargs)

    def __get__(self, instance, owner):
        self.instance = instance
        self.owner = owner
