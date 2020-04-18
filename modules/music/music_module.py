import asyncio
import functools
import itertools
import math
from random import random

import discord
from async_timeout import timeout
from discord.ext import commands
from discord.ext.commands import MissingAnyRole

from module_properties import Module
from modules.music import data
from modules.music.data import Music
from modules.music.ytdl_source import YTDLSource, YTDLError

from utils import decorators
from utils.permissions import CommandRunError
from utils.strings import find_urls


class VoiceError(Exception):
    pass


class Song:
    __slots__ = ('source', 'requester')

    def __init__(self, source: YTDLSource):
        self.source = source
        self.requester = source.requester

    def create_embed(self):
        embed = (discord.Embed(title='Now playing',
                               description='```css\n{0.source.title}\n```'.format(self),
                               color=discord.Color.blurple())
                 .add_field(name='Duration', value=self.source.duration)
                 .add_field(name='Requested by', value=self.requester.mention)
                 .add_field(name='Uploader', value='[{0.source.uploader}]({0.source.uploader_url})'.format(self))
                 .add_field(name='URL', value='[Click]({0.source.url})'.format(self))
                 .set_thumbnail(url=self.source.thumbnail))

        return embed


class SongQueue(asyncio.Queue):
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        random.shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]


class VoiceState:
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        self.bot = bot
        self._ctx = ctx

        self.current = None
        self.voice = None
        self.next = asyncio.Event()
        self.songs = SongQueue()

        self._loop = False
        self._volume = 0.5
        self.skip_votes = set()

        self.audio_player = bot.loop.create_task(self.audio_player_task())

    def __del__(self):
        self.audio_player.cancel()

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value: float):
        self._volume = value

        if self.is_playing:
            self.current.source.volume = value

    @property
    def is_playing(self):
        return self.voice is not None and self.current is not None

    async def audio_player_task(self):
        while True:
            self.next.clear()

            if not self.loop:
                # Try to get the next song within 3 minutes.
                # If no song will be added to the queue in time,
                # the player will disconnect due to performance
                # reasons.
                try:
                    async with timeout(180):  # 3 minutes
                        self.current = await self.songs.get()
                except asyncio.TimeoutError:
                    self.bot.loop.create_task(self.stop())
                    return

            self.current.source.volume = self._volume
            self.voice.play(self.current.source, after=self.play_next_song)
            await self.current.source.channel.send(embed=self.current.create_embed())

            await self.next.wait()

    def play_next_song(self, error=None):
        if error:
            raise VoiceError(str(error))

        self.next.set()

    def skip(self):
        self.skip_votes.clear()

        if self.is_playing:
            self.voice.stop()

    async def stop(self):
        self.songs.clear()

        if self.voice:
            await self.voice.disconnect()
            self.voice = None


class MusicPlayer(Module):
    def __init__(self, manager):
        super().__init__("MusicPlayer", manager)

        self.voice_states = dict()

    def get_voice_state(self, ctx: commands.Context):
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state

        return state

    def cog_unload(self):
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('This command can\'t be used in DM channels.')

        return True

    async def cog_before_invoke(self, ctx: commands.Context):
        ctx.voice_state = self.get_voice_state(ctx)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, CommandRunError):
            await ctx.send(error.detail)
            return

        await ctx.send('An error occurred: {}'.format(str(error)))

    def run_check(self, ctx, module_source=None, command=None):

        # if module_source == "music" and command == "music":
        #
        #     # Only store music information if we have a session
        #     session_manager = self.manager.get_module("SessionManager")
        #     if session_manager is not None and not session_manager.get_session():
        #         raise CommandRunError("A session is required in order to run the music storage features.")

        if module_source == "music":

            # If a session is running, only the GM or and administrator can run these commands
            session_manager = self.manager.get_module("SessionManager")
            if session_manager is not None and session_manager.get_session() is not None and (
                    ctx.author.id != session_manager.get_gm() and not ctx.author.guild_permissions.administrator):
                raise CommandRunError(
                    "A session is currently using the music bot. Please contact an admin or GM: " + session_manager.get_gm_real() + " to negotiate custody.")

            elif not ctx.author.guild_permissions.administrator:
                items = ["DJ", "GM", "admin"]  # TODO: Configurable
                getter = functools.partial(discord.utils.get, ctx.author.roles)
                if any(getter(id=item) is not None if isinstance(item, int) else getter(name=item) is not None for
                       item in items):
                    return True
                raise MissingAnyRole(items)

        return True

    @commands.command(name='summon')
    @decorators.can_run(module_source="music", command="summon")
    async def _summon(self, ctx: commands.Context, *, channel: discord.VoiceChannel = None):
        await self.summon_duck(ctx, channel=channel)

    async def summon_duck(self, ctx: commands.Context, *, channel: discord.VoiceChannel = None):
        """Summons the bot to a voice channel.
        If no channel was specified, it joins your channel.
        """
        if len(self.bot.voice_clients) != 0:
            await ctx.send("Sorry, I am currently in: " + self.bot.voice_clients[0].channel.name + " - Kick me if you want me to move!")
            return

        if not channel and not ctx.author.voice:
            raise VoiceError('You are neither connected to a voice channel nor specified a channel to join.')

        destination = channel or ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            await ctx.message("I am now active in: " + destination)
            return

        ctx.voice_state.voice = await destination.connect()

    @commands.command(name='kick', aliases=['leave', 'disconnect'])
    @commands.has_permissions(manage_guild=True)
    @decorators.can_run(module_source="music", command="kick")
    async def _kick(self, ctx: commands.Context):
        """Clears the queue and leaves the voice channel."""

        if not ctx.voice_state.voice:
            return await ctx.send('Not connected to any voice channel.')

        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild.id]

    @commands.command(name='play')
    @decorators.can_run(module_source="music", command="play")
    async def _play(self, ctx: commands.Context, *, info: str, channel: discord.VoiceChannel = None):
        if not ctx.voice_state.voice:
            await self.summon_duck(ctx, channel=channel)

        async with ctx.typing():

            try:
                source = await YTDLSource.create_source(ctx, info, loop=self.bot.loop)

            except YTDLError as e:
                await ctx.send('An error occurred while processing this request: {}'.format(str(e)))

            else:
                song = Song(source)

                await ctx.voice_state.songs.put(song)
                await ctx.send('Enqueued {}'.format(str(source)))

    @commands.command(name='skip')
    @decorators.can_run(module_source="music", command="skip")
    async def _skip(self, ctx: commands.Context):
        """Vote to skip a song. The requester can automatically skip.
        3 skip votes are needed for the song to be skipped.
        """

        if not ctx.voice_state.is_playing:
            return await ctx.send('Not playing any music right now...')

        voter = ctx.message.author
        if voter == ctx.voice_state.current.requester:
            await ctx.message.add_reaction('⏭')
            ctx.voice_state.skip()

        elif voter.id not in ctx.voice_state.skip_votes:
            ctx.voice_state.skip_votes.add(voter.id)
            total_votes = len(ctx.voice_state.skip_votes)

            if total_votes >= 3:
                await ctx.message.add_reaction('⏭')
                ctx.voice_state.skip()
            else:
                await ctx.send('Skip vote added, currently at **{}/3**'.format(total_votes))

        else:
            await ctx.send('You have already voted to skip this song.')

    @commands.command(name='volume')
    @decorators.can_run(module_source="music", command="volume")
    async def _volume(self, ctx: commands.Context, *, volume: int):
        """Sets the volume of the player."""

        if not ctx.voice_state.is_playing:
            return await ctx.send('Nothing being played at the moment.')

        if 0 > volume > 100:
            return await ctx.send('Volume must be between 0 and 100')

        ctx.voice_state.volume = volume / 100
        await ctx.send('Volume of the player set to {}%'.format(volume))

    @commands.command(name='pause')
    @decorators.can_run(module_source="music", command="pause")
    async def _pause(self, ctx: commands.Context):
        """Pauses the currently playing song."""

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.pause()
            await ctx.message.add_reaction('⏯')

    @commands.command(name='resume')
    @decorators.can_run(module_source="music", command="resume")
    async def _resume(self, ctx: commands.Context):
        """Resumes a currently paused song."""

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_paused():
            ctx.voice_state.voice.resume()
            await ctx.message.add_reaction('⏯')

    @commands.command(name='stop')
    @decorators.can_run(module_source="music", command="stop")
    async def _stop(self, ctx: commands.Context):
        """Stops playing song and clears the queue."""

        ctx.voice_state.songs.clear()

        if not ctx.voice_state.is_playing:
            ctx.voice_state.voice.stop()
            await ctx.message.add_reaction('⏹')

    @commands.command(name='shuffle')
    @decorators.can_run(module_source="music", command="shuffle")
    async def _shuffle(self, ctx: commands.Context):
        """Shuffles the queue."""

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        ctx.voice_state.songs.shuffle()
        await ctx.message.add_reaction('✅')

    @commands.command(name='remove')
    @decorators.can_run(module_source="music", command="shuffle")
    async def _remove(self, ctx: commands.Context, index: int):
        """Removes a song from the queue at a given index."""

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        ctx.voice_state.songs.remove(index - 1)
        await ctx.message.add_reaction('✅')

    @commands.command(name='loop')
    @decorators.can_run(module_source="music", command="shuffle")
    async def _loop(self, ctx: commands.Context):
        """Loops the currently playing song.
        Invoke this command again to unloop the song.
        """

        if not ctx.voice_state.is_playing:
            return await ctx.send('Nothing being played at the moment.')

        # Inverse boolean value to loop and unloop.
        ctx.voice_state.loop = not ctx.voice_state.loop
        await ctx.message.add_reaction('✅')

    @commands.command(name='queue')
    async def _queue(self, ctx: commands.Context, *, page: int = 1):
        """Shows the player's queue.
        You can optionally specify the page to show. Each page contains 10 elements.
        """

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        items_per_page = 10
        pages = math.ceil(len(ctx.voice_state.songs) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ''
        for i, song in enumerate(ctx.voice_state.songs[start:end], start=start):
            queue += '`{0}.` [**{1.source.title}**]({1.source.url})\n'.format(i + 1, song)

        embed = (discord.Embed(description='**{} tracks:**\n\n{}'.format(len(ctx.voice_state.songs), queue))
                 .set_footer(text='Viewing page {}/{}'.format(page, pages)))
        await ctx.send(embed=embed)

    @commands.command(name='now', aliases=['current', 'playing'])
    async def _now(self, ctx: commands.Context):
        """Displays the currently playing song."""

        await ctx.send(embed=ctx.voice_state.current.create_embed())

    @commands.command(name='tag')
    @decorators.can_run(module_source="music", command="tag")
    async def _tag(self, ctx: commands.Context, *, terms: str):
        urls = find_urls(terms)
        if len(urls) != 1:
            raise CommandRunError("The format for the music command is: !music tag1 tag2 tag3 url - the url must start with an http!")

        # Load existing
        user_songs = await self.manager.load_data_for_user_in_context(ctx, "music")
        if user_songs is None:
            user_songs = Music()

        # Append entry if applicable
        tags = terms.replace(urls[0], "").split()
        found = False
        for entry in user_songs.music:
            if entry.url == urls[0]:
                entry.append_tags(tags)
                found = True
                break

        # Save out to userdata
        if not found:
            entry = data.MusicEntry(tags, urls[0])
            user_songs.add_music(entry)

        await self.manager.save_data_for_user_in_context(ctx, "music", user_songs)

    @commands.command(name="tag_current")
    @decorators.can_run(module_source="music", command="tag_current")
    async def _tag_current(self, ctx: commands.Context, *, terms: str):
        if ctx.voice_state.current is None:
            raise CommandRunError("There is no song currently playing")

        # Get our properties
        tags = terms.split()
        url = ctx.voice_state.current.source.url

        # Load existing
        user_songs = await self.manager.load_data_for_user_in_context(ctx, "music")
        if user_songs is None:
            user_songs = Music()

        # Append entry if applicable
        found = False
        for entry in user_songs.music:
            if entry.url == url:
                entry.append_tags(tags)
                found = True
                break

        # Save out to userdata
        if not found:
            entry = data.MusicEntry(tags, url)
            user_songs.add_music(entry)

        await self.manager.save_data_for_user_in_context(ctx, "music", user_songs)

    @commands.command(name='find_tagged')
    @decorators.can_run(module_source="music", command="find_tagged")
    async def _find_tagged(self, ctx: commands.Context, *, terms: str):
        tags = terms.split()

        # Load existing
        user_songs = await self.manager.load_data_for_user_in_context(ctx, "music")
        if user_songs is None:
            raise CommandRunError("You have not tagged any songs yet!")

        # Find the most matching tags
        count = 0
        best_count = 0
        current_best = None
        for entry in user_songs.music:
            tags_to_check = entry.tags
            for tag in tags:
                if tag in tags_to_check:
                    count += 1
                    if count > best_count:
                        current_best = entry
                        best_count = count

            count = 0

        if current_best is not None:
            await self._play(ctx, info=current_best.url)

        """
        TODO: List tagged
        TODO: Remove tagged
        """
