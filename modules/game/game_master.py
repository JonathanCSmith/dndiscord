import os

from discord.ext import commands

from module_properties import Module
from modules.game.games import GuildData, Game
from utils import constants
from utils.errors import CommandRunError


class GameMaster(Module):

    def __init__(self, manager):
        super().__init__("game_master_new", manager)

        self.guild_data = dict()
        self.active_sessions = dict()
        self.game_state_listeners = list()

        # Add some special roles for game management - TODO: this should be configurable in the future
        self.gm_roles = ["GM"]

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, CommandRunError):
            await ctx.send(error.detail)
            return

        await ctx.send('`An error occurred: {}`'.format(str(error)))

    def register_game_state_listener(self, obj):
        self.game_state_listeners.append(obj)

    def is_game_running_for_context(self, ctx):
        return ctx.guild.id in self.active_sessions

    async def check_inactive_game_permissions_for_user(self, ctx, game_name, permission_name, permissions_level=constants.admin, special_roles=None):
        # If the user is an administrator we ALWAYS allow
        if ctx.author.guild_permissions.administrator:
            return True

        # Quick check to format the special roles
        if not special_roles:
            special_roles = list()
        elif not isinstance(special_roles, list):
            special_roles = [special_roles]

        # Get the requested game
        game = await self.__get_game(ctx, game_name)
        if not game:
            return False

        # Get game permission overrides
        overwritten_permissions_level = game.get_permission_level(permission_name)
        if overwritten_permissions_level >= 0:
            permissions_level = overwritten_permissions_level

        # If it open to anyone
        if permissions_level == constants.open:
            return True

        # This permissions level allows any member of the party to run the command
        if permissions_level >= constants.party_member and game:
            if game.is_player(ctx.author.id):
                return True

        # This permissions level only allows for the gm or elevated roles
        if permissions_level >= constants.owner_or_role:

            # Check if the user is the gm of the game
            if game and game.is_gm(ctx.author.it):
                return True

            # Check if our user is in one of the special roles provided:
            for role in ctx.author.roles:
                for special_role in special_roles:
                    if role.name == special_role:
                        return True

        # If the permissions level == 3 or if it was an unregistered permission and the user is not an admin
        return False

    async def check_active_game_permissions_for_user(self, ctx, permission_name, permissions_level=constants.admin, special_roles=None):
        # If the user is an administrator we ALWAYS allow
        if ctx.author.guild_permissions.administrator:
            return True

        # Quick check to format the special roles
        if not special_roles:
            special_roles = list()
        elif not isinstance(special_roles, list):
            special_roles = [special_roles]

        # Get the active game
        game = self.get_active_game_for_context(ctx)
        if not game:
            return False

        # Get game permission overrides
        overwritten_permissions_level = game.get_permission_level(permission_name)
        if overwritten_permissions_level >= 0:
            permissions_level = overwritten_permissions_level

        # If it open to anyone
        if permissions_level == constants.open:
            return True

        # This permissions level allows any member of the party to run the command
        if permissions_level >= constants.party_member and game:
            if game.is_player(ctx.author.id):
                return True

        # This permissions level only allows for the gm or elevated roles
        if permissions_level >= constants.owner_or_role:

            # Check if the user is the gm of the game
            if game and game.is_gm(ctx.author.it):
                return True

            # Check if our user is in one of the special roles provided:
            for role in ctx.author.roles:
                for special_role in special_roles:
                    if role.name == special_role:
                        return True

        # If the permissions level == 3 or if it was an unregistered permission and the user is not an admin
        return False

    async def check_guild_permissions_for_user(self, ctx, permission_name, permissions_level=constants.admin, special_roles=None):
        # If the user is an administrator we ALWAYS allow
        if ctx.author.guild_permissions.administrator:
            return True

        # Quick check to format the special roles
        if not special_roles:
            special_roles = list()
        elif not isinstance(special_roles, list):
            special_roles = [special_roles]

        # Obtain any registered permission overwrites
        guild_data = await self.__get_guild_data(ctx)
        overwritten_permissions_level = guild_data.get_permission_level(permission_name)
        if overwritten_permissions_level >= 0:
            permissions_level = overwritten_permissions_level

        # If it open to anyone
        if permissions_level == constants.open:
            return True

        # This permissions level only allows for the gm or elevated roles
        if permissions_level >= constants.owner_or_role:

            # Check if our user is in one of the special roles provided:
            for role in ctx.author.roles:
                for special_role in special_roles:
                    if role.name == special_role:
                        return True

        # If the permissions level == 3 or if it was an unregistered permission and the user is not an admin
        return False

    async def set_guild_permissions_for_context(self, ctx, permissions_name, permissions_level):
        guild_data = await self.__get_guild_data(ctx)
        guild_data.set_permissions_level(permissions_name, permissions_level)
        return await self.__save_guild_data(ctx, guild_data)

    async def set_game_permissions_for_context(self, ctx, permissions_name, permissions_level):
        game = self.get_active_game_for_context(ctx)
        if game:
            game.set_permissions_level(permissions_level, permissions_level)

    async def load_game_data(self, ctx, path_modifier, file_name):
        if not self.is_game_running_for_context(ctx):
            raise RuntimeError("Cannot load data for a game if there is no game running!")
        game = self.get_active_game_for_context(ctx)
        return await self.manager.load_data_from_data_path_for_guild(ctx, os.path.join(game.get_name(), path_modifier), file_name)

    async def save_game_data(self, ctx, path_modifier, file_name, item_to_save):
        if not self.is_game_running_for_context(ctx):
            raise RuntimeError("Cannot save data for a game if there is no game running!")
        game = self.get_active_game_for_context(ctx)
        await self.manager.save_data_in_data_path_for_guild(ctx, os.path.join(game.get_name(), path_modifier), file_name, item_to_save)

    def get_active_game_for_context(self, ctx):
        if not self.is_game_running_for_context(ctx):
            return None

        return self.active_sessions[ctx.guild.id]

    def __set_active_game_for_context(self, ctx, game):
        if self.is_game_running_for_context(ctx):
            raise RuntimeError("You cannot overwrite a running game like this.")

        self.active_sessions[ctx.guild.id] = game

    async def __end_active_game_for_context(self, ctx):
        guild_data = await self.__get_guild_data(ctx)
        return await self.__save_guild_data(ctx, guild_data)  # This is a hack to force the data to serialize out. Because we are not entirely sure how things will interact with our game obj its better to be safe than sorry

    async def __get_game(self, ctx: commands.Context, game_name):
        # Now we can get this game_name
        guild_data = await self.__get_guild_data(ctx)
        return guild_data.get_game(game_name)

    async def __register_new_game(self, ctx: commands.Context, game):
        guild_data = await self.__get_guild_data(ctx)
        guild_data.add_game(game)
        return await self.__save_guild_data(ctx, guild_data)

    async def __delete_game(self, ctx: commands.Context, game):
        guild_data = await self.__get_guild_data(ctx)
        guild_data.remove_game(game)
        self.manager.delete_in_data_path_for_guild(ctx, os.path.join("game", game.game_name))
        return await self.__save_guild_data(ctx, guild_data)

    async def __get_guild_data(self, ctx):
        guild_id = str(ctx.guild.id)  # TODO: Evaluate why this is necessary
        data = None

        # If we don't have it in memory we should try to load it from disk
        if guild_id not in self.guild_data:
            data = await self.manager.load_data_from_data_path_for_guild(ctx, "", "game_master_info.json")

        # Create the guild data
        if data is None:
            data = GuildData(guild_id)

        # Return the guild data
        self.guild_data[ctx.guild.id] = data
        return data

    async def __save_guild_data(self, ctx, guild_data):
        await self.manager.save_data_in_data_path_for_guild(ctx, "", "game_master_info.json", guild_data)
        self.guild_data[ctx.guild.id] = guild_data

    @commands.command(name="game:register")
    async def _register_game(self, ctx: commands.Context, *, game_name: str):
        """
        Register a new game and activate it in the guild.

        :param ctx:
        :return:
        """
        # Can this user initiate the call to this command
        if not await self.check_guild_permissions_for_user(ctx, "game_master:game:register", special_roles=self.gm_roles):
            return await ctx.send("`You do not have permission to run that command.`")

        # Check if there is already a game with the provided name available for this context
        game = await self.__get_game(ctx, game_name)
        if game:
            return await ctx.send("`Unfortunately a game with this name already exists!`")

        # Let's create a game
        game = Game(ctx.guild.id, game_name, ctx.author.id, ctx.author.name)

        # Add the game
        await self.__register_new_game(ctx, game)

        # Let our listeners know
        for listener in self.game_state_listeners:
            await listener.game_created(ctx, game)

        # Let the channel know
        return await ctx.send("`I have created a game called: " + game_name + "`")

    @commands.command(name="game:run")
    async def _run_game(self, ctx: commands.Context, *, game_name: str):
        # Can this user initiate the call to this command
        if not await self.check_inactive_game_permissions_for_user(ctx, game_name, "game_master:game:run", permissions_level=constants.owner_or_role):
            return await ctx.send("`You do not have permission to run that command.`")

        # Is there a game running for this guild
        if self.is_game_running_for_context(ctx):
            game = self.get_active_game_for_context(ctx)
            if game.game_name == game_name:
                return await ctx.send("`It appears this game is already running.`")

            else:
                return await ctx.send("`Unfortunately a game is already running for this guild`")

        # Get the game
        game = await self.__get_game(ctx, game_name)
        if not game:
            return await ctx.send("`There is no registered game with the name: " + game_name + " for this context. Please register it first!`")

        # Set this game as our active game
        self.__set_active_game_for_context(ctx, game)

        # Inform our listeners
        for listener in self.game_state_listeners:
            await listener.game_started(ctx, game)

        # Inform the channel
        return await ctx.send("`Set the game: " + game_name + " as our active game!`")

    @commands.command(name="game:end")
    async def _end_game(self, ctx: commands.Context):
        # Can the user initiate a call to this command
        if not await self.check_active_game_permissions_for_user(ctx, "game_master:game:end", permissions_level=constants.owner_or_role):
            return await ctx.send("`You do not have permission to run that command.`")

        # Is there game currently running
        game = self.get_active_game_for_context(ctx)
        if not game:
            return await ctx.send("`There is no game currently running!`")

        # End this game
        await self.__end_active_game_for_context(ctx)

        # Inform our listeners
        for listener in self.game_state_listeners:
            await listener.game_ended(ctx, game)

        # Inform the author
        return await ctx.send("`Ended " + game.game_name + ". Thanks for playing!`")

    @commands.command(name="game:delete")
    async def _delete_game(self, ctx: commands.Context):
        # Can the user initiate a call to this command
        if not await self.check_active_game_permissions_for_user(ctx, "game_master:game:delete", permissions_level=constants.owner_or_role):
            return await ctx.send("`You do not have permissions to run that command.`")

        # Is there game currently running
        game = self.get_active_game_for_context(ctx)
        if not game:
            return await ctx.send("`There is no game currently running!`")

        # Delete this game
        await self.__delete_game(ctx, game)

        # Inform our listeners
        for listener in self.game_state_listeners:
            await listener.game_deleted(ctx, game)

        return await ctx.send("`Deleted: " + game.game_name + " and all of it's data.`")



    """
    TODO: Create game channel
    """


