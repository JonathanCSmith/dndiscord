import math

import discord
from discord.ext import commands

from module_properties import Module
from modules.harpers.bard import Bard, BardError
from modules.harpers.favourties import Favourites, MusicEntry
from modules.harpers.music import Song
from modules.harpers.sources.source import SourceError, Source
from modules.harpers.sources.ytdl_source import YTDLSource
from utils import constants
from utils.errors import CommandRunError
from utils.strings import find_urls

"""
TODO: Queue and now can be opened up if we can ensure privacy, but its not worth the feature creep
TODO: Investigate bug where bot is technically playing a tune, is removed, and then when it attempts to rejoin it cannot (delete based perhaps?) MAY BE FIXED
TODO: Perhaps add_tagged (and equivalent) should add all songs that contain the tags provided? (i.e. they must contain all tags, but they may also have others - proposed tags must be a subset of owned tags)?
TODO: Documentation on functions
TODO: Local music
TODO: We should have a play now option
TODO: Playlist support
TODO: Configurable DJ roles
"""


class Harpers(Module):
    def __init__(self, manager):
        super().__init__("harpers", manager)

        self.bards = dict()
        self.game_master = self.manager.get_module("game_master")
        if not self.game_master:
            raise RuntimeError("Cannot use the tavern simulator without the Game Master module.")

        # Add some special roles for bard management - TODO: this should be configurable in the future
        self.bard_roles = ["GM"]

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('`This command can\'t be used in DM channels.`')

        return True

    async def cog_before_invoke(self, ctx: commands.Context):
        ctx.bard = self.get_bard_for_context(ctx)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, CommandRunError):
            await ctx.send(error.detail)
            return

        await ctx.send('`An error occurred: {}`'.format(str(error)))

    def cog_unload(self):
        for state in self.bards.values():
            self.bot.loop.create_task(state.stop())

    def get_bard_for_context(self, ctx: commands.Context):
        bard = self.bards.get(ctx.guild.id)
        if not bard:
            bard = Bard(self.bot)
            self.bards[ctx.guild.id] = bard

        return bard

    @commands.command(name="harpers:summon")
    async def _summon(self, ctx: commands.Context):
        # Do we have permission to run this command. If a game is running we should enforce only the GM (unless there are permission overwrites going on)
        if self.game_master.is_game_running_for_context(ctx):
            if not await self.game_master.check_active_game_permissions_for_user(ctx, "harpers:summon", permissions_level=constants.gm):
                return await ctx.send("`You do not have permission to run that command.`")

        else:
            if not await self.game_master.check_guild_permissions_for_user(ctx, "harpers:summon", special_roles=[self.bard_roles]):
                return await ctx.send("`You do not have permission to run that command.`")

        # Check if we are in a channel
        if not ctx.author.voice:
            raise BardError('`You must be in a room for me to play!`')

        # Move the bard into the room if it is already playing
        if ctx.bard.voice:
            await ctx.bard.voice.move_to(ctx.author.voice.channel)

        # Otherwise the bard can begin his performance
        else:
            ctx.bard.voice = await ctx.author.voice.channel.connect()

        return await ctx.send("`I am now playing in: " + ctx.author.voice.channel.name + "`")

    @commands.command(name="harpers:close")
    async def _close(self, ctx: commands.Context):
        # Do we have permission to run this command. If a game is running we should enforce only the GM (unless there are permission overwrites going on)
        if self.game_master.is_game_running_for_context(ctx):
            if not await self.game_master.check_active_game_permissions_for_user(ctx, "harpers:close", permissions_level=constants.gm):
                return await ctx.send("`You do not have permission to run that command.`")

        else:
            if not await self.game_master.check_guild_permissions_for_user(ctx, "harpers:close", special_roles=[self.bard_roles]):
                return await ctx.send("`You do not have permission to run that command.`")

        await ctx.bard.stop()
        del self.bards[ctx.guild.id]
        return await ctx.send("`I have finished performing.`")

    @commands.command(name='harpers:volume')
    async def _volume(self, ctx: commands.Context, *, volume: int):
        # Do we have permission to run this command. If a game is running we should enforce only the GM (unless there are permission overwrites going on)
        if self.game_master.is_game_running_for_context(ctx):
            if not await self.game_master.check_active_game_permissions_for_user(ctx, "harpers:volume", permissions_level=constants.gm):
                return await ctx.send("`You do not have permission to run that command.`")

        else:
            if not await self.game_master.check_guild_permissions_for_user(ctx, "harpers:volume", special_roles=[self.bard_roles]):
                return await ctx.send("`You do not have permission to run that command.`")

        if not ctx.bard.is_playing:
            return await ctx.send('`I am not playing anything at the moment.`')

        if 0 > volume > 100:
            return await ctx.send("`Your request for me to adjust the loudness of my performance must lie between 0 and 100 percent`")

        ctx.bard.volume = volume / 100
        return await ctx.send("`I am now playing with {}% of my effort`".format(volume))

    @commands.command(name="harpers:play")
    async def _play(self, ctx: commands.Context, *, info: str):
        # Do we have permission to run this command. If a game is running we should enforce only the GM (unless there are permission overwrites going on)
        if self.game_master.is_game_running_for_context(ctx):
            if not await self.game_master.check_active_game_permissions_for_user(ctx, "harpers:play", permissions_level=constants.gm):
                return await ctx.send("`You do not have permission to run that command.`")

        else:
            if not await self.game_master.check_guild_permissions_for_user(ctx, "harpers:play", special_roles=[self.bard_roles]):
                return await ctx.send("`You do not have permission to run that command.`")

        if not ctx.bard.voice:
            await ctx.send("`There is no bard - please summon one first!`")

        async with ctx.typing():
            try:
                # Create a ytdl source, later this may have more functionality
                source = await YTDLSource.create_source(ctx, info, loop=self.bot.loop)

            except SourceError as e:
                await ctx.send('`I encountered the following issue : {} when trying to play your request`'.format(str(e)))

            else:
                song = Song(source)

                await ctx.bard.set_list.put(song)
                return await ctx.send("`Okay, I will play that song in a bit.`")

    @commands.command(name='pause')
    async def _pause(self, ctx: commands.Context):
        # Do we have permission to run this command. If a game is running we should enforce only the GM (unless there are permission overwrites going on)
        if self.game_master.is_game_running_for_context(ctx):
            if not await self.game_master.check_active_game_permissions_for_user(ctx, "harpers:pause", permissions_level=constants.gm):
                return await ctx.send("`You do not have permission to run that command.`")

        else:
            if not await self.game_master.check_guild_permissions_for_user(ctx, "harpers:pause", special_roles=[self.bard_roles]):
                return await ctx.send("`You do not have permission to run that command.`")

        if ctx.bard.is_playing and ctx.bard.voice.is_playing():
            ctx.bard.voice.pause()
            return await ctx.message.add_reaction('⏯')

    @commands.command(name='harpers:resume')
    async def _resume(self, ctx: commands.Context):
        # Do we have permission to run this command. If a game is running we should enforce only the GM (unless there are permission overwrites going on)
        if self.game_master.is_game_running_for_context(ctx):
            if not await self.game_master.check_active_game_permissions_for_user(ctx, "harpers:resume", permissions_level=constants.gm):
                return await ctx.send("`You do not have permission to run that command.`")

        else:
            if not await self.game_master.check_guild_permissions_for_user(ctx, "harpers:resume", special_roles=[self.bard_roles]):
                return await ctx.send("`You do not have permission to run that command.`")

        # If the bard is on break, let him resume
        if ctx.bard.is_playing and ctx.bard.voice.is_paused():
            ctx.bard.voice.resume()
            return await ctx.message.add_reaction('⏯')

    @commands.command(name='harpers:stop_and_clear')
    async def _stop_and_clear(self, ctx: commands.Context):
        # Do we have permission to run this command. If a game is running we should enforce only the GM (unless there are permission overwrites going on)
        if self.game_master.is_game_running_for_context(ctx):
            if not await self.game_master.check_active_game_permissions_for_user(ctx, "harpers:stop_and_clear", permissions_level=constants.gm):
                return await ctx.send("`You do not have permission to run that command.`")

        else:
            if not await self.game_master.check_guild_permissions_for_user(ctx, "harpers:stop_and_clear", special_roles=[self.bard_roles]):
                return await ctx.send("`You do not have permission to run that command.`")

        ctx.bard.set_list.clear()
        if not ctx.bard.is_playing():
            ctx.bard.voice.stop()
            return await ctx.message.add_reaction('⏹')

    @commands.command(name='harpers:next')
    async def _next(self, ctx: commands.Context):
        # Do we have permission to run this command. If a game is running we should enforce only the GM (unless there are permission overwrites going on)
        if self.game_master.is_game_running_for_context(ctx):
            if not await self.game_master.check_active_game_permissions_for_user(ctx, "harpers:next", permissions_level=constants.gm):
                return await ctx.send("`You do not have permission to run that command.`")

        else:
            if not await self.game_master.check_guild_permissions_for_user(ctx, "harpers:next", special_roles=[self.bard_roles]):
                return await ctx.send("`You do not have permission to run that command.`")

        # If the bard is playing we cannot move to the next song
        if not ctx.bard.is_playing:
            return await ctx.send('`I am not playing any harpers right now.`')

        # Skip the song
        await ctx.message.add_reaction('⏭')
        ctx.bard.skip()
        return await ctx.send("`Fine, I will skip that song. Heathen!`")

    @commands.command(name='harpers:loop')
    async def _loop(self, ctx: commands.Context):
        # Do we have permission to run this command. If a game is running we should enforce only the GM (unless there are permission overwrites going on)
        if self.game_master.is_game_running_for_context(ctx):
            if not await self.game_master.check_active_game_permissions_for_user(ctx, "harpers:loop", permissions_level=constants.gm):
                return await ctx.send("`You do not have permission to run that command.`")

        else:
            if not await self.game_master.check_guild_permissions_for_user(ctx, "harpers:loop", special_roles=[self.bard_roles]):
                return await ctx.send("`You do not have permission to run that command.`")

        if not ctx.bard.is_playing:
            return await ctx.send('`I am not playing any harpers right now.`')

        # Inverse boolean value to loop and unloop.
        ctx.bard.loop = not ctx.bard.loop
        await ctx.message.add_reaction('✅')

    @commands.command(name='harpers:shuffle_setlist')
    async def _shuffle(self, ctx: commands.Context):
        # Do we have permission to run this command. If a game is running we should enforce only the GM (unless there are permission overwrites going on)
        if self.game_master.is_game_running_for_context(ctx):
            if not await self.game_master.check_active_game_permissions_for_user(ctx, "harpers:shuffle", permissions_level=constants.gm):
                return await ctx.send("`You do not have permission to run that command.`")

        else:
            if not await self.game_master.check_guild_permissions_for_user(ctx, "harpers:shuffle", special_roles=[self.bard_roles]):
                return await ctx.send("`You do not have permission to run that command.`")

        if len(ctx.bard.set_list) == 0:
            return await ctx.send('Empty queue.')

        ctx.bard.set_list.shuffle()
        return await ctx.message.add_reaction('✅')

    @commands.command(name='harpers:remove_song_from_setlist')
    async def _remove(self, ctx: commands.Context, index: int):
        # Do we have permission to run this command. If a game is running we should enforce only the GM (unless there are permission overwrites going on)
        if self.game_master.is_game_running_for_context(ctx):
            if not await self.game_master.check_active_game_permissions_for_user(ctx, "harpers:remove_song_from_setlist", permissions_level=constants.gm):
                return await ctx.send("`You do not have permission to run that command.`")

        else:
            if not await self.game_master.check_guild_permissions_for_user(ctx, "harpers:remove_song_from_setlist", special_roles=[self.bard_roles]):
                return await ctx.send("`You do not have permission to run that command.`")

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        ctx.voice_state.songs.remove(index - 1)
        await ctx.message.add_reaction('✅')

    @commands.command(name='harpers:set_list')
    async def _queue(self, ctx: commands.Context, *, page: int = 1):
        # Do we have permission to run this command. If a game is running we should enforce only the GM (unless there are permission overwrites going on)
        if self.game_master.is_game_running_for_context(ctx):
            if not await self.game_master.check_active_game_permissions_for_user(ctx, "harpers:queue", permissions_level=constants.gm):
                return await ctx.send("`You do not have permission to run that command.`")

        else:
            if not await self.game_master.check_guild_permissions_for_user(ctx, "harpers:queue", special_roles=[self.bard_roles]):
                return await ctx.send("`You do not have permission to run that command.`")

        if len(ctx.bard.set_list) == 0:
            return await ctx.send('`Empty queue.`')

        items_per_page = 10
        pages = math.ceil(len(ctx.bard.set_list) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ''
        for i, song in enumerate(ctx.bard.set_list[start:end], start=start):
            queue += '`{0}.` [**{1.source.title}**]({1.source.url})\n'.format(i + 1, song)

        embed = (discord.Embed(description='`**{} tracks:**\n\n{}`'.format(len(ctx.bard.set_list), queue)).set_footer(text='`Viewing page {}/{}`'.format(page, pages)))
        return await ctx.send(embed=embed)

    @commands.command(name='harpers:now')
    async def _now(self, ctx: commands.Context):
        # Do we have permission to run this command. If a game is running we should enforce only the GM (unless there are permission overwrites going on)
        if self.game_master.is_game_running_for_context(ctx):
            if not await self.game_master.check_active_game_permissions_for_user(ctx, "harpers:now", permissions_level=constants.gm):
                return await ctx.send("`You do not have permission to run that command.`")

        else:
            if not await self.game_master.check_guild_permissions_for_user(ctx, "harpers:now", special_roles=[self.bard_roles]):
                return await ctx.send("`You do not have permission to run that command.`")

        if ctx.bard or ctx.bard.current:
            return await ctx.send("`No harpers playing!`")

        return await ctx.send(embed=ctx.bard.current.create_embed())

    @commands.command(name="harpers:play:favourite")
    async def _play_favourite(self, ctx: commands.Context, *, terms: str):
        # Do we have permission to run this command. If a game is running we should enforce only the GM (unless there are permission overwrites going on)
        if self.game_master.is_game_running_for_context(ctx):
            if not await self.game_master.check_active_game_permissions_for_user(ctx, "harpers:play:favourite", permissions_level=constants.gm):
                return await ctx.send("`You do not have permission to run that command.`")

        else:
            if not await self.game_master.check_guild_permissions_for_user(ctx, "harpers:play:favourite", special_roles=[self.bard_roles]):
                return await ctx.send("`You do not have permission to run that command.`")

        tags = terms.split()

        # Load existing
        user_songs = await self.manager.load_data_from_data_path_for_user(ctx, "harpers", "favourites.json")
        if user_songs is None or len(user_songs.music) == 0:
            return await ctx.send("`You have not tagged any songs yet!`")

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

        # Add the song to general player
        if current_best is not None:
            await ctx.send("`Hmmm, that song sounds like: " + current_best.url + ".`")
            return await self._play(ctx, info=current_best.url)

        else:
            return await ctx.send("`Unfortunately that song doesn't sound like any I know...`")

    @commands.command(name="harpers:favourite")
    async def _remember_favourite(self, ctx: commands.Context, *, terms: str):
        if not await self.game_master.check_guild_permissions_for_user(ctx, "harpers:favourite", permissions_level=constants.open):
            return await ctx.send("`You do not have permission to run that command.`")

        # Search the terms for a url
        urls = find_urls(terms)
        if len(urls) > 1:
            return ctx.send("`You have listed too many songs there for me to work though. Please do it one at a time.`")

        # If there are no urls provided then we need to be playing something
        if len(urls) == 0 and not ctx.bard.current:
            return await ctx.send("`I am not playing anything right now!`")
        elif len(urls) == 0:
            url = ctx.bard.current.source.url
        else:
            url = urls[0]

        # Get our properties
        tags = terms.replace(url, "").split()

        # Load existing
        user_songs = await self.manager.load_data_from_data_path_for_user(ctx, "harpers", "favourites.json")
        if user_songs is None:
            user_songs = Favourites()

        # Append entry if applicable
        found = False
        for entry in user_songs.music:
            if entry.url == url:
                entry.append_tags(tags)
                found = True
                break

        # Save out to userdata
        if found:
            await ctx.send("`I have modified your reference notes to: " + entry.get_tags() + "for the song: " + url + "`")
        else:
            entry = MusicEntry(tags, url)
            user_songs.add_music(entry)
            await ctx.send("`Added: " + url + " to your favourites with the following refernce notes: " + str(tags) + "`")

        return await self.manager.save_data_in_data_path_for_user(ctx, "harpers", "favourites.json", user_songs)

    @commands.command(name="harpers:forget:favourite")
    async def _forget_favourites(self, ctx: commands.Context, *, terms: str):
        if not await self.game_master.check_guild_permissions_for_user(ctx, "harpers:forget:favourite", permissions_level=constants.open):
            return await ctx.send("`You do not have permission to run that command.`")

        urls = find_urls(terms)
        if len(urls) != 1:
            return await ctx.send("`You did not provide me with the song that you wish me to forget your preferences for!`")

        # Load existing
        user_songs = await self.manager.load_data_from_data_path_for_user(ctx, "harpers", "favourites.json")
        if user_songs is None or len(user_songs.music) == 0:
            return await ctx.send("`I have no recorded preferences for any songs for you...`")

        # Obtain any tags
        tags = terms.replace(urls[0], "").split()

        # Modify the saved info for the url
        entry_to_remove = None
        entry = None
        for entry in user_songs.music:
            if entry.url == urls[0]:
                if len(tags) == 0:
                    entry_to_remove = entry
                else:
                    for tag in tags:
                        entry.tags.remove(tag)

                    if len(entry.tags) == 0:
                        entry_to_remove = entry

                break

        # Remove the entire entry if we were not removing tags or if we removed all the tags
        if entry_to_remove:
            user_songs.music.remove(entry_to_remove)
            await ctx.send("`I am forgetting your preferences for the song: " + str(entry_to_remove) + "`")
        else:
            await ctx.send("`Amended the your preferences for the song: " + str(entry) + " to: " + entry.get_tags() + "`")

        return await self.manager.save_data_in_data_path_for_user(ctx, "harpers", "favourites.json", user_songs)

    @commands.command(name="harpers:favourites")
    async def _list_favourites(self, ctx: commands.Context):
        if not await self.game_master.check_guild_permissions_for_user(ctx, "harpers:favourites", permissions_level=constants.open):
            return await ctx.send("`You do not have permission to run that command.`")

        # Load existing
        user_songs = await self.manager.load_data_from_data_path_for_user(ctx, "harpers", "favourites.json")
        if user_songs is None or len(user_songs.music) == 0:
            return await ctx.send("`I do not have any song preferences recorded for you.`")

        # We could be typing a lot here!
        await ctx.send("`I have the following song preferences recorded for you: `")
        async with ctx.typing():
            for entry in user_songs.music:
                await ctx.send(str(entry))

    # @commands.command(name="everybody_dj")
    # async def _everybody_can_dj(self, ctx):
    #     if self.is_owner(ctx):
    #         self.permissions = 3
    #         return await ctx.send("Set the permissions so everyone can DJ")
    #
    #     else:
    #         return await ctx.send("Only an admin or the bot owner can use this command.")

    # @commands.command(name="channel_dj")
    # async def _channel_can_dj(self, ctx):
    #     if await self.is_owner(ctx):
    #         self.permissions = 2
    #         return await ctx.send("Set the permissions so only members of the voice channel / game channel can DJ.")
    #
    #     else:
    #         return await ctx.send("Only an admin or the bot owner can use this command.")

    # @commands.command(name="owner_dj")
    # async def _owner_can_dj(self, ctx):
    #     if await self.is_owner(ctx):
    #         self.permissions = 1
    #         return await ctx.send("Set the permissions so only the bot owner / GM can DJ")
    #
    #     else:
    #         return await ctx.send("Only an admin or the bot owner can use this command.")
