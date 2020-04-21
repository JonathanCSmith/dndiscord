import os

import discord
from discord.ext import commands

from module_properties import Module
from modules.game.data import Games, GameEntry, PlayerEntry
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
"""


class GameMaster(Module):
    member_permissions = discord.PermissionOverwrite(read_messages=True, send_messages=True, create_instant_invite=True, manage_channels=True, manage_permissions=True, manage_webhooks=True, send_tts_messages=True, manage_messages=True, embed_links=True, attach_files=True, read_message_history=True, mention_everyone=True, external_emojis=True, add_reactions=True)

    def __init__(self, manager):
        super().__init__("game_master", manager)

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

    def get_game(self):
        return self.game

    def get_gm(self):
        return self.gm

    def get_gm_real(self):
        return self.gm_real

    def is_adventurer(self, id):
        for player in self.players:
            if player.player_id == id:
                return True

        return False

    def get_game_data_path(self):
        return os.path.join("game", self.game)

    def is_in_game(self, ctx):
        if self.get_game():
            return self.is_adventurer(ctx.author.id)

        return False

    @commands.command(name="game")
    @commands.has_any_role("GM", "@admin")
    async def __game(self, ctx: commands.Context, *, name: str):
        if self.game is not None:
            await ctx.send("Already running a game: " + self.game)
            return

        # Validate that our game doesn't exist already
        games = await self.manager.load_data("game", "game_states")
        if not games:
            games = Games()

        # Check if this game is already registered
        existing_game = games.get_game(name)

        # Validate our caller vs internal
        if existing_game and existing_game.gm != ctx.author.id:
            await ctx.send("Unfortunately this game already exists and you are not the GM of it.")
            return

        # Set our local information
        self.game = name
        self.gm = ctx.author.id
        self.gm_real = ctx.author.name
        if existing_game:
            self.players = existing_game.players
        else:
            self.players.append(PlayerEntry(self.gm, self.gm_real, "GM"))
        await ctx.send("Starting game: " + self.game)

        # Permissions
        everyone = discord.PermissionOverwrite(read_messages=False, send_messages=False, create_instant_invite=False, manage_channels=False, manage_permissions=False, manage_webhooks=False, send_tts_messages=False, manage_messages=False, embed_links=False, attach_files=False, read_message_history=False, mention_everyone=False, external_emojis=False, add_reactions=False)

        admin_role = discord.utils.get(ctx.guild.roles, name="@admin")
        admin = discord.PermissionOverwrite(read_messages=True, send_messages=True, create_instant_invite=True, manage_channels=True, manage_permissions=True, manage_webhooks=True, send_tts_messages=True, manage_messages=True, embed_links=True, attach_files=True, read_message_history=True, mention_everyone=True, external_emojis=True, add_reactions=True)

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
            self.text_channel = await ctx.guild.create_text_channel(name, overwrites={ctx.guild.default_role: everyone, me_member: GameMaster.member_permissions, bot_member: GameMaster.member_permissions, admin_role: admin}, userlimit=0, category=ctx.guild.categories[0])

        # Create the voice channel
        self.voice_channel = await ctx.guild.create_voice_channel(name, overwrites={ctx.guild.default_role: everyone, me_member: GameMaster.member_permissions, bot_member: GameMaster.member_permissions, admin_role: admin}, bitrate=64000, userlimit=0, permissions_synced=True, category=ctx.guild.categories[1])
        if ctx.author.voice:
            self.original_channel = ctx.author.voice.channel
            await ctx.author.move_to(self.voice_channel)
            await ctx.send("You are now active in: " + self.voice_channel.name)

        # Create a data directory
        await self.manager.create(os.path.join("game", self.game))

        # If the music player is present lets pull it into our game too!
        module = self.manager.get_module("bardic_inspiration")
        if module is not None:
            ctx.voice_state = module.get_voice_state(ctx)
            await module._summon(ctx, channel=self.voice_channel)

        # Remember this game
        if not existing_game:
            game = GameEntry(self.game, self.gm, self.gm_real, self.players)
            games.add_game(game)
            await self.manager.save_data("game", "game_states", games)

    @commands.command(name="end")
    @commands.has_any_role("GM", "@admin")
    async def _end(self, ctx: commands.Context):
        if self.game is None:
            await ctx.send("We aren't currently running a game!")
            return

        # Only allow an administrator or the owner to end a game
        if ctx.author.id == self.gm or ctx.author.guild_permissions.administrator:
            await ctx.send("Okay! Thanks for playing in: " + self.game)
            self.game = None
            self.gm = None
            self.gm_real = None
            self.players.clear()

        else:
            await ctx.send("Only your current GM can end a game (or an admin if something is bugged).")

        if self.original_channel:
            await ctx.author.move_to(self.original_channel)
            await ctx.send("You have been returned to: " + self.voice_channel.name)

        # Properly exit the channel
        module = self.manager.get_module("bardic_inspiration")
        if module is not None:
            ctx.voice_state = module.get_voice_state(ctx)
            await module._kick(ctx)

        await self.voice_channel.delete()
        self.voice_channel = None

        # TODO: Save all game data - from this module or otherwise

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
        existing_game = games.get_game(name)

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
        existing_game = games.get_game(self.game)
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
        existing_game = games.get_game(self.game)
        existing_game.set_players(self.players)
        await self.manager.save_data("game", "game_states", games)
        return await ctx.send("Removed the adventurer from the party.")
