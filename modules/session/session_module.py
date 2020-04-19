from discord.ext import commands

from module_properties import Module
from utils.permissions import CommandRunError


class SessionManager(Module):

    def __init__(self, manager):
        super().__init__("SessionManager", manager)

        self.session = None
        self.gm = None
        self.gm_real = None
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

    def get_session(self):
        return self.session

    def get_gm(self):
        return self.gm

    def get_gm_real(self):
        return self.gm_real

    @commands.command(name="session")
    @commands.has_role("GM")
    async def __session(self, ctx: commands.Context, *, name: str):
        if self.session is not None:
            await ctx.send("Already running a session: " + self.session)
            return

        self.session = name
        self.gm = ctx.author.id
        self.gm_real = ctx.author.name
        await ctx.send("Starting session: " + self.session)

        # Create our session channel
        self.text_channel = await ctx.guild.create_text_channel("[DNDiscord] " + self.session, userlimit=0, permissions_synced=True, category=ctx.guild.categories[0])
        self.voice_channel = await ctx.guild.create_voice_channel("[DNDiscord] " + self.session, bitrate=64000, userlimit=0, permissions_synced=True, category=ctx.guild.categories[1])
        if ctx.author.voice:
            self.original_channel = ctx.author.voice.channel
            await ctx.author.move_to(self.voice_channel)
            await ctx.message("You are now active in: " + self.voice_channel.name)

        # If the music player is present lets pull it into our session too!
        module = self.manager.get_module("MusicPlayer")
        if module is not None:
            ctx.voice_state = module.get_voice_state(ctx)
            await module.summon_duck(ctx, channel=self.voice_channel)

    @commands.command(name="end")
    async def __end(self, ctx: commands.Context):
        if self.session is None:
            await ctx.send("We aren't currently running a session!")
            return

        if ctx.author.id == self.gm or ctx.author.guild_permissions.administrator:
            await ctx.send("Okay! Thanks for playing in: " + self.session)
            self.session = None
            self.gm = None
            self.gm_real = None

        else:
            await ctx.send("Only your current GM can end a session (or an admin if something is bugged).")

        if self.original_channel:
            await ctx.author.move_to(self.original_channel)
            await ctx.message("You have been returned to: " + self.voice_channel.name)

        await self.voice_channel.delete()
        await self.text_channel.delete()
