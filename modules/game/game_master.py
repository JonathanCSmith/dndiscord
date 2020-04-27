import os

from discord.ext import commands

from module_properties import Module
from modules.game.games import GuildData, Game, Adventurer
from utils import constants
from utils.errors import CommandRunError


"""
TODO: Add configuration for game role management
TODO: Game channels

# Channel creation
    # Permissions
    admin_role = discord.utils.get(ctx.guild.roles, name="@admin")
    me_member = ctx.author
    bot_member = self.manager.get_bot_member(ctx)

    # Create our game channel
    name = "[DNDiscord] " + self.game

    # Don't create the text channel if it already exists
    text_channel_name = "dndiscord-" + self.game.lower().replace(" ", "-")
    exists = False
    for channel in ctx.guild.text_channels:
        if channel.name == text_channel_name:
            self.text_channel = channel
            exists = True
            break

    if not exists:
        self.text_channel = await ctx.guild.create_text_channel(name, overwrites={ctx.guild.default_role: constants.closed, me_member: constants.open, bot_member: constants.open, admin_role: constants.open}, userlimit=0, category=ctx.guild.categories[0])

    # Create the voice channel
    # TODO: Move this to harpers module
    self.voice_channel = await ctx.guild.create_voice_channel(name, overwrites={ctx.guild.default_role: constants.closed, me_member: constants.open, bot_member: constants.open, admin_role: constants.open}, bitrate=64000, userlimit=0, permissions_synced=True, category=ctx.guild.categories[1])
    if ctx.author.voice:
        self.original_channel = ctx.author.voice.channel
        await ctx.author.move_to(self.voice_channel)
        await ctx.send("You are now active in: " + self.voice_channel.name)

    # Channel permissions adjustment for added adventurers
        await self.text_channel.set_permissions(player, overwrite=GameMaster.member_permissions)
        if self.voice_channel:
            await self.voice_channel.set_permissions(player, overwrite=GameMaster.member_permissions)    
    
    # Handle the channel permissions adjustment for removed players
        await self.text_channel.set_permissions(player, overwrite=None)
        if self.voice_channel:
            await self.voice_channel.set_permissions(player, overwrite=None)
TODO: Why do I need to convert guild.id to str when saving some things?
TODO: Don't delete channels that don't exist any more
TODO: Fix permissions on channels with a command
TODO: If music mod enabled put some default music on start!
TODO: Readd bot to game command
TODO: If the voice channel exists already handle gracefully
TODO: Delete game with no name should delete the current game
TODO: Delete even if you don't have a voice connection?
TODO: Documentation
"""


class GameMaster(Module):

    def __init__(self, manager):
        super().__init__("game_master", manager)

        self.guild_data = dict()
        self.active_sessions = dict()
        self.game_state_listeners = list()

        # Add some special roles for game management
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

    async def check_inactive_game_permissions_for_user(self, ctx, game_name, permission_name, permissions_level=constants.admin, elevated_roles=None):
        # Get the requested game - the game check takes precedence over the admin check as usually commands that call this will not function without a game
        game = await self.__get_game(ctx, game_name)
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
        for role in ctx.author.roles:
            for special_role in elevated_roles:
                if role.name == special_role:
                    return True, ""

        # Get game permission overrides
        overwritten_permissions_level = game.get_permission_level(permission_name)
        if overwritten_permissions_level >= 0:
            permissions_level = overwritten_permissions_level

        # If it open to anyone
        if permissions_level == constants.open:
            return True, ""

        # This permissions level allows any member of the party to run the command
        if permissions_level >= constants.party_member:
            if game.is_player(ctx.author.id):
                return True, ""

        # This permissions level only allows for the gm or elevated roles
        if permissions_level >= constants.gm:

            # Check if the user is the gm of the game
            if game.is_gm(ctx.author.it):
                return True, ""

        # If the permissions level == 3 or if it was an unregistered permission and the user is not an admin
        return False, "You do not have permission to do this."

    async def check_active_game_permissions_for_user(self, ctx, permission_name, permissions_level=constants.admin, elevated_roles=None):
        # Get the requested game - the game check takes precedence over the admin check as usually commands that call this will not function without a game
        game = self.get_active_game_for_context(ctx)
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
        for role in ctx.author.roles:
            for special_role in elevated_roles:
                if role.name == special_role:
                    return True, ""

        # Get game permission overrides
        overwritten_permissions_level = game.get_permission_level(permission_name)
        if overwritten_permissions_level >= 0:
            permissions_level = overwritten_permissions_level

        # If it open to anyone
        if permissions_level == constants.open:
            return True, ""

        # This permissions level allows any member of the party to run the command
        if permissions_level >= constants.party_member:
            if game.is_player(ctx.author.id):
                return True, ""

        # This permissions level only allows for the gm or elevated roles
        if permissions_level >= constants.gm:

            # Check if the user is the gm of the game
            if game.is_gm(ctx.author.it):
                return True, ""

        # If the permissions level == 3 or if it was an unregistered permission and the user is not an admin
        return False, "You do not have permission to do that."

    async def check_guild_permissions_for_user(self, ctx, permission_name, permissions_level=constants.admin, elevated_roles=None):
        # If the user is an administrator we ALWAYS allow
        if ctx.author.guild_permissions.administrator:
            return True, ""

        # Quick check to format the special roles
        if not elevated_roles:
            elevated_roles = list()
        elif not isinstance(elevated_roles, list):
            elevated_roles = [elevated_roles]

        # Check if our user is in one of the special roles provided:
        for role in ctx.author.roles:
            for special_role in elevated_roles:
                if role.name == special_role:
                    return True, ""

        # Obtain any registered permission overwrites
        guild_data = await self.__get_guild_data(ctx)
        overwritten_permissions_level = guild_data.get_permission_level(permission_name)
        if overwritten_permissions_level >= 0:
            permissions_level = overwritten_permissions_level

        # If it open to anyone
        if permissions_level == constants.open:
            return True, ""

        # If the permissions level == 3 or if it was an unregistered permission and the user is not an admin
        return False, "You do not have permission to do this."

    async def set_guild_permissions_for_context(self, ctx, permissions_name, permissions_level):
        guild_data = await self.__get_guild_data(ctx)
        guild_data.set_permissions_level(permissions_name, permissions_level)
        return await self.__save_guild_data(ctx, guild_data)

    async def set_game_permissions_for_context(self, ctx, permissions_name, permissions_level):
        game = self.get_active_game_for_context(ctx)
        if game:
            game.set_permissions_level(permissions_name, permissions_level)

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
        await self.__save_guild_data(ctx, guild_data)  # This is a hack to force the data to serialize out. Because we are not entirely sure how things will interact with our game obj its better to be safe than sorry
        del self.active_sessions[ctx.guild.id]

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
        permissions_check, reason = await self.check_guild_permissions_for_user(ctx, "game_master:register", elevated_roles=self.gm_roles)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

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
        permissions_check, reason = await self.check_inactive_game_permissions_for_user(ctx, game_name, "game_master:run", permissions_level=constants.gm)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

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
        permissions_check, reason = await self.check_active_game_permissions_for_user(ctx, "game_master:end", permissions_level=constants.gm)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # Is there game currently running
        game = self.get_active_game_for_context(ctx)
        if not game:
            return await ctx.send("`There is no game currently running!`")

        # Inform our listeners
        for listener in self.game_state_listeners:
            await listener.game_about_to_end(ctx, game)

        # End this game
        await self.__end_active_game_for_context(ctx)

        # Inform the author
        return await ctx.send("`Ended " + game.game_name + ". Thanks for playing!`")

    @commands.command(name="game:delete")
    async def _delete_game(self, ctx: commands.Context):
        # Can the user initiate a call to this command
        permissions_check, reason = self.check_active_game_permissions_for_user(ctx, "game_master:delete", permissions_level=constants.gm)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

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

    @commands.command(name="game:list")
    async def _list_games(self, ctx: commands.Context):
        guild_data = await self.__get_guild_data(ctx)
        await ctx.send("`You are currently involved in the following games:`")
        async with ctx.typing():
            for game in guild_data.games:
                permissions_check, reason = await self.check_inactive_game_permissions_for_user(ctx, game.get_name(), "game_master:game:list", permissions_level=constants.party_member)
                if permissions_check:
                    await ctx.send("`" + game.get_name() + "`")

    @commands.command(name="game:add_adventurer")
    async def _add_adventurer(self, ctx: commands.Context):
        # Can the user initiate a call to this command
        permissions_check, reason = await self.check_active_game_permissions_for_user(ctx, "game_master:add_adventurer", permissions_level=constants.gm)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # If no identifiable adventurers were mentioned
        if not ctx.message.mentions:
            return await ctx.send("`No potential adventurers were mentioned.`")

        # If more than one adventurer was mentioned
        if len(ctx.message.mentions) != 1:
            return await ctx.send("`You can only recruit one adventurer at a time`")

        # Check if the player is already a member
        game = self.get_active_game_for_context(ctx)
        player = ctx.message.mentions[0]
        if game.is_player(player.id):
            return await ctx.send("`This adventurer already is a member of your party.`")

        # Check args
        context = ctx.message.clean_content.replace("!" + ctx.invoked_with, "")
        adventurer_name = context.replace("@" + player.display_name, "").strip()
        if not adventurer_name or adventurer_name == "":
            return await ctx.send("`You must provide an adventurer name`")

        # Create a player entry
        player_entry = Adventurer(player.id, player.name, adventurer_name)

        # Append our player entry and save the guild data
        game.add_player(player_entry)
        guild_data = await self.__get_guild_data(ctx)
        guild_data.update_game(game)
        await self.__save_guild_data(ctx, guild_data)
        return await ctx.send("`Added the adventurer: " + adventurer_name + " to the party.`")

    @commands.command(name="game:remove_adventurer")
    async def _remove_adventurer(self, ctx: commands.Context):
        # Can the user initiate a call to this command
        permissions_check, reason = self.check_active_game_permissions_for_user(ctx, "game_master:remove_adventurer", permissions_level=constants.gm)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # If no identifiable adventurers were mentioned
        if not ctx.message.mentions:
            return await ctx.send("`No potential adventurers were mentioned.`")

        # If more than one adventurer was mentioned
        if len(ctx.message.mentions) != 1:
            return await ctx.send("`You can only recruit one adventurer at a time`")

        # Check if the player is already a member
        game = self.get_active_game_for_context(ctx)
        player = ctx.message.mentions[0]
        adventurer = game.get_player(player.id)

        # Handle if they are not
        if adventurer is None:
            return await ctx.send("`This adventurer is not in your party.`")

        # Remove and update
        game.remove_player(player.id)
        await self.__save_guild_data(ctx, await self.__get_guild_data(ctx))

        return await ctx.send("`Removed the adventurer: " + adventurer.character_name + " from the party.`")

    @commands.command(name="game:adventurer:list")
    async def _list_adventurers(self, ctx: commands.Context):
        # Can the user initiate a call to this command
        permissions_check, reason = await self.check_active_game_permissions_for_user(ctx, "game_master:adventurer:list", permissions_level=constants.gm)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # Check if the player is already a member
        game = self.get_active_game_for_context(ctx)
        adventurers = game.get_adventurers()
        if len(adventurers) == 0:
            return await ctx.send("`There are no adventurers in your party`")

        # Print out the adventurers
        async with ctx.typing():
            for index, adventurer in adventurers.items():
                await ctx.send("`" + adventurer.character_name + " is controlled by: " + adventurer.player_name + "`")

