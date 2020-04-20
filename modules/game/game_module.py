import discord
from discord.ext import commands

from module_properties import Module
from modules.game.data import Games, GameEntry, PlayerEntry
from utils import decorators
from utils.permissions import CommandRunError

"""
TODO: This does not work if the bot is a member of multiple guilds
TODO: Closed channel membership until game invites are made, we can use this to setup character aliases (gm can do it)
"""


class GameManager(Module):

    def __init__(self, manager):
        super().__init__("GameManager", manager)

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
        # TODO: Store a list of adventurers
        return False

    def run_permissions_check(self, ctx, module_source=None, command=None):
        if module_source != "GameManager":
            return True

        # Admins can always!
        if ctx.author.guild_permissions.administrator:
            return True

        elif command == "add_adventurer":
            if not self.get_game():
                raise CommandRunError("You cannot add an adventurer if you are not running a game!")

            elif self.get_game().get_gm() != ctx.author.id:
                raise CommandRunError("You cannot add an adventurer if you are not the GM!")

        return True

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
        existing_game = None
        for game in games.games:
            if game.name == name:
                existing_game = game
                break

        # Validate our caller vs internal
        if existing_game and existing_game.gm != ctx.author.id:
            await ctx.send("Unfortunately this game already exists and you are not the GM of it.")
            return

        # Set our local information
        self.game = name
        self.gm = ctx.author.id
        self.gm_real = ctx.author.name
        self.players.append(PlayerEntry(self.gm, self.gm_real, "GM"))
        await ctx.send("Starting game: " + self.game)

        # Get the server defaults
        server = ctx.message.server

        # Permissions
        everyone = discord.PermissionOverwrite(read_messages=False, send_messages=False, create_instant_invite=False, manage_channel=False, manage_permissions=False, manage_webhooks=False, send_TTS_messages=False, manage_messages=False, embed_links=False, attach_files=False, read_message_history=False, mention_everyone=False, use_external_emojis=False, add_reactions=False)

        admin_role = discord.utils.get(ctx.guild.roles, name="@admin")
        admin = discord.PermissionOverwrite(read_messages=True, send_messages=True, create_instant_invite=True, manage_channel=True, manage_permissions=True, manage_webhooks=True, send_TTS_messages=True, manage_messages=True, embed_links=True, attach_files=True, read_message_history=True, mention_everyone=True, use_externam_emojis=True, add_reactions=True)

        me_member = ctx.author
        me = discord.PermissionOverwrite(read_messages=True, send_messages=True, create_instant_invite=True, manage_channel=True, manage_permissions=True, manage_webhooks=True, send_TTS_messages=True, manage_messages=True, embed_links=True, attach_files=True, read_message_history=True, mention_everyone=True, use_externam_emojis=True, add_reactions=True)

        # Create our game channel
        name = "[DNDiscord] " + self.game

        # Don't create the text channel if it already exists
        if not existing_game:
            self.text_channel = await ctx.guild.create_text_channel(name, (server.default_role, everyone), (me_member, me), (admin_role, admin), userlimit=0, category=ctx.guild.categories[0])

        # Create the voice channel
        self.voice_channel = await ctx.guild.create_voice_channel(name,  (server.default_role, everyone), (me_member, me), (admin_role, admin), bitrate=64000, userlimit=0, permissions_synced=True, category=ctx.guild.categories[1])
        if ctx.author.voice:
            self.original_channel = ctx.author.voice.channel
            await ctx.author.move_to(self.voice_channel)
            await ctx.send("You are now active in: " + self.voice_channel.name)

        # If the music player is present lets pull it into our game too!
        module = self.manager.get_module("MusicPlayer")
        if module is not None:
            ctx.voice_state = module.get_voice_state(ctx)
            await module.summon_duck(ctx, channel=self.voice_channel)

        # Remember this game
        if not existing_game:
            game = GameEntry(self.game, self.gm, self.gm_real, self.players)
            games.add_game(game)
            await self.manager.save_data("game", "game_states", games)

    @commands.command(name="end")
    @commands.has_any_role("GM", "@admin")
    async def __end(self, ctx: commands.Context):
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
        module = self.manager.get_module("MusicPlayer")
        if module is not None:
            ctx.voice_state = module.get_voice_state(ctx)
            await module._kick(ctx)

        await self.voice_channel.delete()

        # TODO: Save all game data - from this module or otherwise

    @commands.command(name="list_games")
    async def _list_games(self, ctx: commands.Context):
        games = await self.manager.load_data("game", "game_states")
        async with ctx.typing():
            await ctx.send("The following games are registered with this bot:")
            for game in games.games:
                await ctx.send(str(game))

    """
    TODO: The code below is enough to create default permissions on a channel etc, however we need to add admin, GM (i.e. caller) on create
    TODO: Add mentioned users to EXISTING channel
    
    server = message.server
    
    # Permissions
    everyone = discord.PermissionOverwrite(read_messages=False, send_messages=False, create_instant_invite=False, manage_channel=False, manage_permissions=False, manage_webhooks=False, send_TTS_messages=False, manage_messages=False, embed_links=False, attach_files=False, read_message_history=False, mention_everyone=False, use_external_emojis=False, add_reactions=False)
    admin = discord.PermissionsOverwrite(read_messages=True, send_messages=True, create_instant_invite=True, manage_channel=True, manage_permissions=True, manage_webhooks=True, send_TTS_messages=True, manage_messages=True, embed_links=True, attach_files=True, read_message_history=True, mention_everyone=True, use_externam_emojis=True, add_reactions=True)
    me = discord.PermissionsOverwrite(read_messages=True, send_messages=True, create_instant_invite=True, manage_channel=True, manage_permissions=True, manage_webhooks=True, send_TTS_messages=True, manage_messages=True, embed_links=True, attach_files=True, read_message_history=True, mention_everyone=True, use_externam_emojis=True, add_reactions=True)
    channel_member = discord.PermissionOverwrite(read_messages=True, send_messages=True, create_instant_invite=False, manage_channel=False, manage_permissions=False, manage_webhooks=False)
    
        channel_member = discord.PermissionOverwrite(read_messages=True, send_messages=True, create_instant_invite=False, manage_channel=False, manage_permissions=False, manage_webhooks=False)
    # Create a tuple for individuals
    member_perms = [(mentioned, channel_member) for mentioned in message.mentions]        
    
    # Apply to the channel
    await channel.set_permissions(mentioned, channel_member)
    await client.create_channel(server, cmd_args[1], (server.default_role, everyone), *member_perms)
    """

    @commands.command(name="add_adventurer")
    @decorators.can_run(module_source="game_module", command="add_adventurer")
    async def _add_adventurer(self, ctx: commands.Context):
        """
        1) split txt into mentions
        2) create player entries for each
        3) update channel permissions
        4) serialize to file
        """
        return

    @commands.command(name="remove_adventurer")
    @decorators.can_run(module_source="game_module", command="remove_adventurer")
    async def _remove_adventurer(self, ctx: commands.Context):
        """
        1) split txt into mentions
        2) update channel permissions
        3) serialize to file
        """
        return
