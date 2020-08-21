import asyncio
import itertools
import math
from asyncio import QueueFull
from random import random

import discord
from async_timeout import timeout
from discord.ext import commands

from new_implementation.audio.sources.source import SourceError
from new_implementation.audio.sources.ytdl_source import YTDLSource
from new_implementation.core.engine import DnDiscordCog
from new_implementation.handlers.permissions_handler import PermissionLevel
from new_implementation.utils import utils
from new_implementation.utils.message import send_message


class BardError(Exception):
    pass


class Track:
    __slots__ = ('source', 'requester', 'creation_info')

    def __init__(self, source: YTDLSource, creation_info: str):
        self.source = source
        self.requester = source.requester
        self.creation_info = creation_info

    def create_embed(self):
        embed = (discord.Embed(title='Now playing',
                               description='```css\n{0.source.title}\n```'.format(self),
                               color=discord.Color.blurple())
                 #.add_field(name='Duration', value=self.source.duration)
                 .add_field(name='Requested by', value=self.requester.mention)
                 .add_field(name='Uploader', value='[{0.source.uploader}]({0.source.uploader_url})'.format(self))
                 .add_field(name='URL', value='[Click]({0.source.url})'.format(self))
                 .set_thumbnail(url=self.source.thumbnail)
        )

        return embed


class Playlist(asyncio.Queue):
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    async def play_now(self, item):
        while self.full():
            putter = self._loop.create_future()
            self._putters.append(putter)
            try:
                await putter
            except:
                putter.cancel()
                try:
                    self._putters.remove(putter)
                except ValueError:
                    pass

                if not self.full() and not putter.cancelled():
                    self._wakeup_next(self._putters)
                raise
        return self.play_now_nowait(item)

    def play_now_nowait(self, item):
        if self.full():
            raise QueueFull
        self._queue.appendleft(item)
        self._unfinished_tasks += 1
        self._finished.clear()
        self._wakeup_next(self._getters)

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        random.shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]


class AudioPlayer:
    def __init__(self, bot):
        self.bot = bot
        self.player = self.bot.loop.create_task(self.audio_player_task())

        self.exists = True
        self.current_track = None
        self.voice_channel = None
        self.next = asyncio.Event()
        self.playlist = Playlist()
        self.volume = 0.5
        self.info = None

        self._loop = False

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
            self.current_track.source.volume = value

    @property
    def is_playing(self):
        return self.voice_channel is not None and self.current_track is not None

    async def audio_player_task(self):
        try:
            while True:
                self.next.clear()

                if not self.loop:
                    try:
                        async with timeout(600):  # 10 Minutes
                            self.current_track = await self.playlist.get()

                    except asyncio.TimeoutError:
                        self.bot.loop.create_task(self.stop())
                        self.exists = False
                        return

                self.current_track.source.volume = self.volume
                self.voice_channel.play(self.current_track.source, after=self.play_next_track)
                await self.info.send(embed=self.current_track.create_embed())
                await self.next.wait()

        except:
            print("Error in audio loop")

    def play_next_track(self, error=None):
        if error:
            raise BardError(str(error))
        self.next.set()

    async def play_now(self, track):
        await self.playlist.play_now(track)

    def skip(self):
        if self.is_playing:
            self.voice_channel.stop()

    async def stop(self):
        self.playlist.clear()

        if self.voice_channel:
            await self.voice_channel.disconnect()
            self.voice_channel = None

    def __del__(self):
        self.player.cancel()


class AudioCog(DnDiscordCog):
    def __init__(self, bot, engine, command_prefix, audio_bot_type):
        super().__init__(bot, engine)

        self.command_prefix = command_prefix
        self.audio_bot_type = audio_bot_type

        # guild -> audio player dictionary
        self.audio_players = dict()

        # Rename all of our commands to be specific to this instance
        self.__rename_commands()

    def __rename_commands(self):
        self.summon_command.name = self.command_prefix + ":summon"
        self.kick_command.name = self.command_prefix + ":kick"
        self.notify_command.name = self.command_prefix + ":notify"
        self.play_now_command.name = self.command_prefix + ":play_now"
        self.play_now_command.name = self.command_prefix + ":play"
        self.play_now_command.name = self.command_prefix + ":pause"
        self.play_now_command.name = self.command_prefix + ":resume"
        self.play_now_command.name = self.command_prefix + ":skip"
        self.play_now_command.name = self.command_prefix + ":stop"
        self.volume_command.name = self.command_prefix + ":volume"
        self.volume_command.name = self.command_prefix + ":repeat"
        self.volume_command.name = self.command_prefix + ":currently_playing"
        self.volume_command.name = self.command_prefix + ":playlist"

    def cog_unload(self):
        for audio_player in self.audio_players.values():
            self.bot.loop.create_task(audio_player.stop())

    def get_audio_player_for_context(self, ctx: commands.Context):
        guild_id = utils.get_guild_id_from_context(ctx)
        if guild_id in self.audio_players:
            return self.audio_players[guild_id]

        # Build a new audio player
        audio_player = AudioPlayer(self.bot)
        self.audio_players[guild_id] = audio_player
        return audio_player

    async def delete_audio_player(self, ctx):
        guild_id = utils.get_guild_id_from_context(ctx)
        if guild_id in self.audio_players:
            audio_player = self.audio_players[guild_id]
            await audio_player.stop()
            del self.audio_players[guild_id]

    @staticmethod
    def get_command_prefix():
        pass

    @commands.command(name="audio_player:summon")
    async def summon_command(self, ctx: commands.Context):
        """
        Summons the audio bot to the voice channel the caller is currently in.

        :param ctx:
        :return:
        """
        # Check if we the caller is a game master
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, self.command_prefix + ":summon", permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:

            # Handle the special case where a game was not actually running - if that's the case check for a couple of special roles
            if reason == "You cannot do this as there is no game running in your guild.":
                permission, reason = await self.engine.get_permission_handler().check_guild_permissions_for_user(ctx, self.command_prefix + ":summon", permissions_level=PermissionLevel.GAME_MASTER, elevated_roles=["Bard"])
                if not permission:
                    return await send_message(ctx, reason)

            else:
                return await send_message(ctx, reason)

        # Check if the author is in the channel
        if not ctx.author.voice:
            return await send_message(ctx, "You must be in a voice channel to summon the audio bot.")

        # Get a audio player and add it to the author's voice channel
        audio_player = self.get_audio_player_for_context(ctx)
        if audio_player.voice_channel:
            await audio_player.voice_channel.move_to(ctx.author.voice.channel)

        else:
            audio_player.voice_channel = await ctx.author.voice.channel.connect()

        # Set our info channel
        audio_player.info = ctx.channel

        # Inform
        return await send_message(ctx, "The guild's " + self.audio_bot_type + " is now playing in: " + ctx.author.voice.channel.name)

    @commands.command(name="audio_player:kick")
    async def kick_command(self, ctx: commands.Context):
        """
        Kick's the audio bot from it's current voice chat. This will clear the playlist and disconnect the bot from the voice channel.

        :param ctx:
        :return:
        """
        # Check if we the caller is a game master
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, self.command_prefix + ":kick", permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:

            # Handle the special case where a game was not actually running - if that's the case check for a couple of special roles
            if reason == "You cannot do this as there is no game running in your guild.":
                permission, reason = await self.engine.get_permission_handler().check_guild_permissions_for_user(ctx, self.command_prefix + ":kick", permissions_level=PermissionLevel.GAME_MASTER, elevated_roles=["Bard"])
                if not permission:
                    return await send_message(ctx, reason)

            else:
                return await send_message(ctx, reason)

        # Get the audio player and stop it
        audio_player = self.get_audio_player_for_context(ctx)
        if audio_player:
            await self.delete_audio_player(ctx)
            return await send_message(ctx, "Goodbye!")
        else:
            return await send_message(ctx, "There is no " + self.audio_bot_type + " summoned at the moment.")

    @commands.command(name="audio_player:notify")
    async def notify_command(self, ctx: commands.Context):
        """

        :param ctx:
        :return:
        """
        # Check if we the caller is a game master
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, self.command_prefix + ":notify", permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:

            # Handle the special case where a game was not actually running - if that's the case check for a couple of special roles
            if reason == "You cannot do this as there is no game running in your guild.":
                permission, reason = await self.engine.get_permission_handler().check_guild_permissions_for_user(ctx, self.command_prefix + ":notify", permissions_level=PermissionLevel.GAME_MASTER, elevated_roles=["Bard"])
                if not permission:
                    return await send_message(ctx, reason)

            else:
                return await send_message(ctx, reason)

        # Get the audio player
        audio_player = self.get_audio_player_for_context(ctx)
        if not audio_player.voice_channel:
            return await send_message(ctx, "The " + self.audio_bot_type + " has not been summoned yet.")

        # If there is 1 channel mention - set it as our notification channel
        if len(ctx.message.channel_mentions) == 1:
            audio_player.info = ctx.message.channel_mentions[0]
            return await send_message(ctx, "The " + self.audio_bot_type + " is now notifying " + audio_player.info.name)
        else:
            return await send_message(ctx, "The " + self.audio_bot_type + " is currently notifying: " + audio_player.info.name)

    @commands.command(name="audio_player:play_now")
    async def play_now_command(self, ctx: commands.Context, *, info: str):
        """

        :param ctx:
        :param info:
        :return:
        """
        # Check if we the caller is a game master
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, self.command_prefix + ":play_now", permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:

            # Handle the special case where a game was not actually running - if that's the case check for a couple of special roles
            if reason == "You cannot do this as there is no game running in your guild.":
                permission, reason = await self.engine.get_permission_handler().check_guild_permissions_for_user(ctx, self.command_prefix + ":play_now", permissions_level=PermissionLevel.GAME_MASTER, elevated_roles=["Bard"])
                if not permission:
                    return await send_message(ctx, reason)

            else:
                return await send_message(ctx, reason)

        # Check that we have an audio player and that the audio player has been summoned
        audio_player = self.get_audio_player_for_context(ctx)
        if not audio_player.voice_channel:
            return await send_message(ctx, "Please summon the: " + self.audio_bot_type + " to a voice channel first.")

        # Finding a valid thing to play can take some time
        async with ctx.typing():
            try:
                # Create a youtube-dl source
                source = await YTDLSource.create_source(ctx, info, loop=self.bot.loop)

            except SourceError as e:
                return await send_message(ctx, "I encountered the following issue: {} - when trying to play your request".format(str(e)))

            else:
                track = Track(source, info)
                await audio_player.play_now(track)
                audio_player.skip()
                await send_message(ctx, "Playing: ", embed=track.create_embed())

    @commands.command(name="audio_player:play")
    async def play_command(self, ctx: commands.Context, *, info: str):
        """

        :param ctx:
        :param info:
        :return:
        """
        # Check if we the caller is a game master
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, self.command_prefix + ":play", permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:

            # Handle the special case where a game was not actually running - if that's the case check for a couple of special roles
            if reason == "You cannot do this as there is no game running in your guild.":
                permission, reason = await self.engine.get_permission_handler().check_guild_permissions_for_user(ctx, self.command_prefix + ":play", permissions_level=PermissionLevel.GAME_MASTER, elevated_roles=["Bard"])
                if not permission:
                    return await send_message(ctx, reason)

            else:
                return await send_message(ctx, reason)

        # Check that we have an audio player and that the audio player has been summoned
        audio_player = self.get_audio_player_for_context(ctx)
        if not audio_player.voice_channel:
            return await send_message(ctx, "Please summon the: " + self.audio_bot_type + " to a voice channel first.")

        # Finding a valid thing to play can take some time
        async with ctx.typing():
            try:
                # Create a youtube-dl source
                source = await YTDLSource.create_source(ctx, info, loop=self.bot.loop)

            except SourceError as e:
                return await send_message(ctx, "I encountered the following issue: {} - when trying to play your request".format(str(e)))

            else:
                track = Track(source, info)
                await audio_player.playlist.put(track)
                await send_message(ctx, "Playing: ", embed=track.create_embed())

    @commands.command(name="audio_player:pause")
    async def pause_command(self, ctx: commands.Context):
        """

        :param ctx:
        :return:
        """
        # Check if we the caller is a game master
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, self.command_prefix + ":pause", permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:

            # Handle the special case where a game was not actually running - if that's the case check for a couple of special roles
            if reason == "You cannot do this as there is no game running in your guild.":
                permission, reason = await self.engine.get_permission_handler().check_guild_permissions_for_user(ctx, self.command_prefix + ":pause", permissions_level=PermissionLevel.GAME_MASTER, elevated_roles=["Bard"])
                if not permission:
                    return await send_message(ctx, reason)

            else:
                return await send_message(ctx, reason)

        # Check that we have an audio player and that the audio player has been summoned and that the audio player is playing something
        audio_player = self.get_audio_player_for_context(ctx)
        if not audio_player.is_playing() or not audio_player.is_playing:
            return await send_message(ctx, "The " + self.audio_bot_type + " is not currently running.")

        audio_player.voice_channel.pause()
        return await send_message(ctx, "The " + self.audio_bot_type + " is paused.")

    @commands.command(name="audio_player:resume")
    async def resume_command(self, ctx: commands.Context):
        """

        :param ctx:
        :return:
        """
        # Check if we the caller is a game master
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, self.command_prefix + ":resume", permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:

            # Handle the special case where a game was not actually running - if that's the case check for a couple of special roles
            if reason == "You cannot do this as there is no game running in your guild.":
                permission, reason = await self.engine.get_permission_handler().check_guild_permissions_for_user(ctx, self.command_prefix + ":resume", permissions_level=PermissionLevel.GAME_MASTER, elevated_roles=["Bard"])
                if not permission:
                    return await send_message(ctx, reason)

            else:
                return await send_message(ctx, reason)

        # Check that there is an audio player, that the audio player has a voice, that the audio player could be playing but is paused
        audio_player = self.get_audio_player_for_context(ctx)
        if audio_player.is_playing() and audio_player.is_playing and audio_player.voice_channel.is_paused():
            audio_player.voice_channel.resume()
            return await send_message(ctx, "The " + self.audio_bot_type + " has been resumed.")

        # Inform failure
        return await send_message(ctx, "The " + self.audio_bot_type + " was not in the correct state to handle that command. Try summoning, playing and then pausing something first!")

    @commands.command(name="audio_player:skip")
    async def skip_command(self, ctx: commands.Context):
        """

        :param ctx:
        :return:
        """
        # Check if we the caller is a game master
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, self.command_prefix + ":skip", permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:

            # Handle the special case where a game was not actually running - if that's the case check for a couple of special roles
            if reason == "You cannot do this as there is no game running in your guild.":
                permission, reason = await self.engine.get_permission_handler().check_guild_permissions_for_user(ctx, self.command_prefix + ":skip", permissions_level=PermissionLevel.GAME_MASTER, elevated_roles=["Bard"])
                if not permission:
                    return await send_message(ctx, reason)

            else:
                return await send_message(ctx, reason)

        # Check that there is an audio player and that they are playing something
        audio_player = self.get_audio_player_for_context(ctx)
        if not audio_player.is_playing() or not audio_player.is_playing:
            return await send_message(ctx, "The " + self.audio_bot_type + " is not playing anything right now.")

        # Skip the song
        audio_player.skip()
        return await send_message(ctx, self.audio_bot_type + " skipped a song!")

    @commands.command(name="audio_player:stop")
    async def stop_command(self, ctx: commands.Context):
        """

        :param ctx:
        :return:
        """
        # Check if we the caller is a game master
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, self.command_prefix + ":stop", permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:

            # Handle the special case where a game was not actually running - if that's the case check for a couple of special roles
            if reason == "You cannot do this as there is no game running in your guild.":
                permission, reason = await self.engine.get_permission_handler().check_guild_permissions_for_user(ctx, self.command_prefix + ":stop", permissions_level=PermissionLevel.GAME_MASTER, elevated_roles=["Bard"])
                if not permission:
                    return await send_message(ctx, reason)

            else:
                return await send_message(ctx, reason)

        # Check that there is an audio player and that they are playing something
        audio_player = self.get_audio_player_for_context(ctx)
        if not audio_player.is_playing() or not audio_player.is_playing:
            return await send_message(ctx, "The " + self.audio_bot_type + " is not playing anything right now.")

        # Clear the playlist and stop the audio player
        audio_player.playlist.clear()
        audio_player.voice_channel.stop()
        return await send_message(ctx, "The " + self.audio_bot_type + " has been stopped and the playlist cleared.")

    @commands.command(name="audio_player:volume")
    async def volume_command(self, ctx: commands.Context, volume: str = ""):
        """

        :param ctx:
        :param volume:
        :return:
        """
        # Check if we the caller is a game master
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, self.command_prefix + ":volume", permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:

            # Handle the special case where a game was not actually running - if that's the case check for a couple of special roles
            if reason == "You cannot do this as there is no game running in your guild.":
                permission, reason = await self.engine.get_permission_handler().check_guild_permissions_for_user(ctx, self.command_prefix + ":volume", permissions_level=PermissionLevel.GAME_MASTER, elevated_roles=["Bard"])
                if not permission:
                    return await send_message(ctx, reason)

            else:
                return await send_message(ctx, reason)

        # Get the audio player
        audio_player = self.get_audio_player_for_context(ctx)

        # Infer the volume
        if volume == "":
            return await send_message(ctx, "The " + self.audio_bot_type + " is currently playing at " + str(audio_player.volume * 100) + "%")
        else:
            try:
                volume = int(volume)
            except:
                return await send_message(ctx, "The volume provided must be a whole number")

        # Check the volume is within expected bounds
        if 0 > volume > 100:
            return await send_message(ctx, "The volume must be a number between 0 and 100.")

        # Set the volume and inform
        audio_player.volume = volume / 100
        return await send_message(ctx, "The " + self.audio_bot_type + "'s volume is set to: " + str(audio_player.volume * 100) + "%")

    @commands.command(name="audio_player:repeat")
    async def repeat_command(self, ctx: commands.Context):
        """

        :param ctx:
        :return:
        """
        # Check if we the caller is a game master
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, self.command_prefix + ":repeat", permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:

            # Handle the special case where a game was not actually running - if that's the case check for a couple of special roles
            if reason == "You cannot do this as there is no game running in your guild.":
                permission, reason = await self.engine.get_permission_handler().check_guild_permissions_for_user(ctx, self.command_prefix + ":repeat", permissions_level=PermissionLevel.GAME_MASTER, elevated_roles=["Bard"])
                if not permission:
                    return await send_message(ctx, reason)

            else:
                return await send_message(ctx, reason)

        # Check that there is an audio player and that they are playing something
        audio_player = self.get_audio_player_for_context(ctx)
        if not audio_player.is_playing() or not audio_player.is_playing:
            return await send_message(ctx, "The " + self.audio_bot_type + " is not playing anything right now.")

        # Invert the current loop state
        current_state = audio_player.loop
        audio_player.loop = not audio_player.loop
        if current_state:
            return await send_message(ctx, "We have stopped repeating the same track for the " + self.audio_bot_type)
        else:
            return await send_message(ctx, "We have enabled repeating of the same track for " + self.audio_bot_type)

    @commands.command(name="audio_player:now")
    async def now_command(self, ctx: commands.Context):
        """

        :param ctx:
        :return:
        """
        # Check if we the caller is a game master
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, self.command_prefix + ":now", permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:

            # Handle the special case where a game was not actually running - if that's the case check for a couple of special roles
            if reason == "You cannot do this as there is no game running in your guild.":
                permission, reason = await self.engine.get_permission_handler().check_guild_permissions_for_user(ctx, self.command_prefix + ":now", permissions_level=PermissionLevel.GAME_MASTER, elevated_roles=["Bard"])
                if not permission:
                    return await send_message(ctx, reason)

            else:
                return await send_message(ctx, reason)

        # Check that there is an audio player and that they are playing something
        audio_player = self.get_audio_player_for_context(ctx)
        if not audio_player.is_playing() or not audio_player.is_playing:
            return await send_message(ctx, "The " + self.audio_bot_type + " is not playing anything right now.")

        # Send the current song
        if audio_player.current_track:
            return await send_message(ctx, "The current track playing for " + self.audio_bot_type + " is: ", embed=audio_player.current_track.create_enbed())
        else:
            return await send_message(ctx, "There is no current track playing for " + self.audio_bot_type)


    @commands.command(name="audio_player:list")
    async def list_command(self, ctx: commands.Context, page: int = 1):
        """

        :param ctx:
        :param page:
        :return:
        """
        # Check if we the caller is a game master
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, self.command_prefix + ":list", permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:

            # Handle the special case where a game was not actually running - if that's the case check for a couple of special roles
            if reason == "You cannot do this as there is no game running in your guild.":
                permission, reason = await self.engine.get_permission_handler().check_guild_permissions_for_user(ctx, self.command_prefix + ":list", permissions_level=PermissionLevel.GAME_MASTER, elevated_roles=["Bard"])
                if not permission:
                    return await send_message(ctx, reason)

            else:
                return await send_message(ctx, reason)

        # Check that there is an audio player and that they are playing something
        audio_player = self.get_audio_player_for_context(ctx)
        if len(audio_player.playlist) == 0:
            return await send_message(ctx, "The " + self.audio_bot_type + " does not have anything in the playlist right now.")

        # Page handling
        items_per_page = 10
        pages = math.ceil(len(audio_player.playlist) / items_per_page)
        start = (page - 1) * items_per_page
        end = start + items_per_page

        # Format the embed
        queue = ""
        for i, track in enumerate(audio_player.playlist[start:end], start=start):
            queue += "`{0}.` [**{1.source.title}**]({1.source.url})\n".format(i + 1, track)
        embed = (discord.Embed(description="`**{} tracks: **\n\n`".format(len(audio_player.playlist), queue)).set_footer(text="`Viewing page {}/{}`".format(page, pages)))
        return ctx.send(embed=embed)
