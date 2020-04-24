import os

import discord
from discord.ext import commands

from module_properties import Module
from modules.game.games import Games, GameEntry, PlayerEntry
from modules.game.game_state_listener import GameStateListener
from utils import constants
from utils.errors import CommandRunError

"""
TODO: This does not work if the bot is a member of multiple guilds
TODO: Don't delete channels that don't exist any more
TODO: Fix permissions on channels with a command
TODO: If music mod enabled put some default music on start!
TODO: Readd bot to game command
TODO: If the voice channel exists already handle gracefully
TODO: QOL functions
TODO: Delete game with no name should delete the current game
TODO: !game <gamename> should perhaps be !play <gamename>
TODO: Delete even if you don't have a voice connection?
TODO: What if we want a game, but really we just only want one, want to use general + voice? 


TODO: 1 game per guild active!!!! Multiple games.
"""


class GameMaster(Module):

    def __init__(self, manager):
        super().__init__("game_master", manager)

        self.game_state_listeners = list()
        self.games = dict()
        self.games_loaded = False

        self.game = None
        self.gm = None
        self.gm_real = None
        self.players = list()
        self.original_channel = None
        self.text_channel = None
        self.voice_channel = None

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('This command can\'t be used in DM channels.')

        return True

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, CommandRunError):
            await ctx.send(error.detail)
            return

        await ctx.send('An error occurred: {}'.format(str(error)))

    async def cog_before_invoke(self, ctx: commands.Context):
        if not self.games_loaded:
            self.__load_games(ctx)

        ctx.game = await self.get_game_session(ctx)

    def register_game_state_listener(self, module: GameStateListener):
        self.game_state_listeners.append(module)

    async def can_access_game(self, ctx: commands.Context, minimum_required_permissions=constants.admin):
        # Get our party permissions
        adventuring_party_module = self.manager.get_module("party_manager")
        if adventuring_party_module:
            # This handles both situations where the user does and does not have a game now
            return await adventuring_party_module.is_allowed(minimum_required_permissions, ctx)

        else:
            return minimum_required_permissions == 0 or ctx.author.guild_permissions.administrator

    def get_game_session(self, ctx):
        guild_id = str(ctx.guild.id)
        if guild_id in self.games:
            return self.games[guild_id]
        return None

    def get_game_data_path(self):
        return os.path.join("game", self.game)

    async def __load_game_data(self, ctx):
        games = await self.manager.load_data("game", "game_states")
        if not games:
            games = Games()

    @commands.command(name="game")
    @commands.has_any_role("GM", "@admin")
    async def __game(self, ctx: commands.Context, *, name: str):
        if ctx.game is not None:
            return await ctx.send("`Already running a game: " + ctx.game.get_name() + "`")

        # Validate that our game doesn't exist already
        await self.__load_game_data(ctx)

        # Check if this game is already registered
        existing_game = games._get_game(name)

        # Validate our caller vs internal
        if existing_game and existing_game.get_gm() != ctx.author.id:
            return await ctx.send("`Unfortunately this game already exists and you are not the GM of it.`")

        # Set our local information
        unique_id = ctx.guild.id + name
        path = os.path.join("game", unique_id)
        self.game = name
        self.gm = ctx.author.id
        self.gm_real = ctx.author.name
        if existing_game:
            self.players = existing_game.players
        else:
            self.players.append(PlayerEntry(self.gm, self.gm_real, "GM"))
        await ctx.send("Starting game: " + self.game)

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
        # TODO: Move this to music module
        self.voice_channel = await ctx.guild.create_voice_channel(name, overwrites={ctx.guild.default_role: constants.closed, me_member: constants.open, bot_member: constants.open, admin_role: constants.open}, bitrate=64000, userlimit=0, permissions_synced=True, category=ctx.guild.categories[1])
        if ctx.author.voice:
            self.original_channel = ctx.author.voice.channel
            await ctx.author.move_to(self.voice_channel)
            await ctx.send("You are now active in: " + self.voice_channel.name)

        # Create a data directory
        await self.manager.create(os.path.join("game", self.game))

        # If the music player is present lets pull it into our game too!
        # TODO: Move this to music module
        module = self.manager.get_module("bardic_inspiration")
        if module is not None:
            ctx.voice_state = module.get_voice_state(ctx)
            await module._summon(ctx, channel=self.voice_channel)

        # Remember this game
        if not existing_game:
            game = GameEntry(unique_id, path, self.game, self.gm, self.gm_real, self.players)
            games.add_game(game)
            await self.manager.save_data("game", "game_states", games)
        else:
            game = existing_game

        # Let our game state listeners know
        for listener in self.game_state_listeners:
            await listener.game_started(ctx, game)

    @commands.command(name="end")
    @commands.has_any_role("GM", "@admin")
    async def _end(self, ctx: commands.Context):
        if self.game is None:
            await ctx.send("We aren't currently running a game!")
            return

        # Only allow an administrator or the owner to end a game
        if ctx.author.id == self.gm or ctx.author.guild_permissions.administrator:

            # Notify listeners
            for listener in self.game_state_listeners:
                await listener.game_ended(ctx, self.game)

            await ctx.send("Okay! Thanks for playing in: " + self.game)
            self.game = None
            self.gm = None
            self.gm_real = None
            self.players.clear()

        else:
            await ctx.send("Only your current GM can end a game (or an admin if something is bugged).")

        # Properly exit the channel
        #TODO: Move this to music
        if self.original_channel:
            await ctx.author.move_to(self.original_channel)
            await ctx.send("You have been returned to: " + self.voice_channel.name)

        module = self.manager.get_module("bardic_inspiration")
        if module is not None:
            ctx.voice_state = module.get_voice_state(ctx)
            await module._kick(ctx)

        await self.voice_channel.delete()
        self.voice_channel = None

        # TODO: Save all game data - from this module or otherwise)

    @commands.command(name="list_games")
    async def _list_games(self, ctx: commands.Context):
        games = await self.manager.load_data("game", "game_states")
        async with ctx.typing():
            await ctx.send("The following games are registered with this bot:")
            for game in games.games:
                await ctx.send(str(game))

    @commands.command(name="delete_game")
    @commands.has_any_role("GM", "@admin")
    async def _delete_game(self, ctx: commands.Context, *, name: str):
        # If we are running this game end it first
        if self.game == name:
            await self._end(ctx=ctx)

        # Get the game
        games = await self.manager.load_data("game", "game_states")
        existing_game = games._get_game(name)

        # Exit if we have no game
        if not existing_game:
            return await ctx.send("Could not identify the provided game: " + name)

        # Check if we have permissions to do this
        if ctx.author.id != existing_game.gm or not ctx.author.guild_permissions.administrator:
            return await ctx.send("Only your current GM can delete a game (or an admin if something is bugged).")

        # Delete the game
        games.delete_game(existing_game)
        await self.manager.save_data("game", "game_states", games)

        # Delete the text channel
        text_channel_name = "dndiscord-" + name.lower().replace(" ", "-")
        for channel in ctx.guild.text_channels:
            if channel.name == text_channel_name:
                await channel.delete()

        # Delete our files
        await self.manager.delete(os.path.join("game", name))
        return await ctx.send("Deleted: " + name)

    @commands.command(name="add_adventurer")
    async def _add_adventurer(self, ctx: commands.Context, *, context: str):
        """
        1) split txt into mentions
        2) create player entries for each
        3) update channel permissions
        4) serialize to file
        """
        game = self.get_game_session(ctx)
        if not game:
            return await ctx.send("`You cannot add an adventurer if you are not in a game.`")

        if game.is_adventurer(ctx):
            return await ctx.send("You cannot run this command as you are not in a game!")

        # Check if anyone was mentioned
        if not ctx.message.mentions:
            return await ctx.send("No potential adventurers were mentioned.")

        # Only one adventurer at a time
        if len(ctx.message.mentions) != 1:
            return await ctx.send("You can only add one adventurer at a time!")

        # Check if the player is already a member
        player = ctx.message.mentions[0]
        for current_player in self.players:
            if current_player.player_id == player.id:
                return await ctx.send("This adventurer is already a part of your party.")

        # Loop through our mentions
        adventurer = context.replace(player.mention.replace("<@", "<@!") + " ", "")
        player_entry = PlayerEntry(player.id, player.name, adventurer)
        self.players.append(player_entry)

        # Adjust the channel permissions if present
        await self.text_channel.set_permissions(player, overwrite=GameMaster.member_permissions)
        if self.voice_channel:
            await self.voice_channel.set_permissions(player, overwrite=GameMaster.member_permissions)

        # Validate that our game doesn't exist already
        games = await self.manager.load_data("game", "game_states")

        # Serialize out the data now
        existing_game = games._get_game(self.game)
        existing_game.set_players(self.players)
        await self.manager.save_data("game", "game_states", games)
        return await ctx.send("Added the adventurer: " + adventurer + " to the party.")

    @commands.command(name="remove_adventurer")
    async def _remove_adventurer(self, ctx: commands.Context):
        """
        1) split txt into mentions
        2) update channel permissions
        3) serialize to file
        """
        if not self.is_in_game(ctx):
            return await ctx.send("You cannot run this command as you are not in a game!")

        # Check if anyone was mentioned
        if not ctx.message.mentions:
            return await ctx.send("No potential adventurers were mentioned.")

        # Only one adventurer at a time
        if len(ctx.message.mentions) != 1:
            return await ctx.send("You can only add one adventurer at a time!")

        # Check if the player is already a member
        player = ctx.message.mentions[0]
        identified_player = None
        for current_player in self.players:
            if current_player.player_id == player.id:
                identified_player = current_player
                break

        # Handle if they are not
        if identified_player is None:
            return await ctx.send("This adventurer is not in your party.")

        # Delete the player
        self.players.remove(identified_player)

        # Handle the channel permissions
        await self.text_channel.set_permissions(player, overwrite=None)
        if self.voice_channel:
            await self.voice_channel.set_permissions(player, overwrite=None)

        # Validate that our game doesn't exist already
        games = await self.manager.load_data("game", "game_states")

        # Serialize out the data now
        existing_game = games._get_game(self.game)
        existing_game.set_players(self.players)
        await self.manager.save_data("game", "game_states", games)
        return await ctx.send("Removed the adventurer from the party.")
