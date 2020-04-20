import math

import discord
from discord.ext import commands

from module_properties import Module
from modules.music import data
from modules.music.data import Music
from modules.music.music_properties.music import VoiceError, Song, VoiceState
from modules.music.music_properties.ytdl_source import YTDLSource, YTDLError

from utils.errors import CommandRunError
from utils.strings import find_urls

"""
Permissions:
    All command permissions follow the basic premise
        1) If ADMIN then yes
        2) If OWNER then yes
        3) If perms_type == open then yes
        4) if perms_type == member & if member then yes

    except summon which follows the below:
        1) If ADMIN then yes
        2) If role is GM then yes
        3) If role is DJ then yes           

All commands:
    summon - moves the bot to a channel (your's or specified)
    kick - kicks the bot out of your channel IF you are not in a game and are the owner or admin
    next - skips the current song (starts vote if low permission)
    volume - sets the volume of the bot
    pause - pauses the currently playing song
    resume - resumes the currently playing song
    stop_and_clear - stops the bot playing and clears the current queue
    shuffle - shuffle's the current queue 
    remove - removes a song at a given index 
    loop - repeats the current song 
    queue - shows the queue 
    now - shows the currently playing song
    tag - tags a url song with metadata tags
    tag_current - tags the currently playing song with metadata tags 
    list_tagged - list all of your currently tagged urls 
    forget_tagged - remove a tag from a url, if all tags are removed, url is forgotten 
    add - add a song to the queue 
    add_tagged - add a tagged url to the queue 
    everybody_dj - set permissions to open
    channel_dj - set permissions to channel
    owner_dj - set permissions to owner

TODO: Queue and now can be opened up if we can ensure privacy, but its not worth the feature creep
TODO: Investigate bug where bot is technically playing a tune, is removed, and then when it attempts to rejoin it cannot (delete based perhaps?) MAY BE FIXED
TODO: Perhaps add_tagged (and equivalent) should add all songs that contain the tags provided? (i.e. they must contain all tags, but they may also have others - proposed tags must be a subset of owned tags)?
TODO: This does not work if the bot is a member of multiple guilds
TODO: Better information output on ALL commands
TODO: Add did not output an indication that a track has been added in latest test
"""


class MusicPlayer(Module):
    def __init__(self, manager):
        super().__init__("MusicPlayer", manager)

        self.voice_states = dict()
        self.owner = None
        self.permissions = 1

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

    def is_owner(self, ctx):
        game_manager = self.manager.get_module("GameManager")
        if game_manager and game_manager.get_game():
            if ctx.author.id != game_manager.get_gm():
                return False

        elif self.owner != ctx.author.id:
            return False

        return True

    def is_member(self, ctx):
        game_manager = self.manager.get_module("GameManager")
        if game_manager and game_manager.get_game():
            return game_manager.is_adventurer(ctx.author.id)
        elif ctx.voice_state.voice:
            return ctx.author.id in ctx.voice_state.voice.members
        else:
            return False

    def can_run(self, ctx, requires_voice):
        # Early fail if we require voice
        if not ctx.voice_state.voice:
            return False

        # Admins can always!
        if ctx.author.guild_permissions.administrator:
            return True

        if self.permissions == 1:
            return self.is_owner(ctx)

        elif self.permissions == 2:
            return self.is_owner(ctx) or self.is_member(ctx)

        else:
            return True



    @commands.command(name='summon')
    @commands.has_any_role("DJ", "GM", "@admin")
    async def _summon(self, ctx: commands.Context, *, channel: discord.VoiceChannel = None):
        """Summons the bot to a voice channel.
        If no channel was specified, it joins your channel.
        """
        if len(self.bot.voice_clients) != 0:
            await ctx.send("Sorry, I am currently in: " + self.bot.voice_clients[
                0].channel.name + " - Kick me if you want me to move!")
            return

        if not channel and not ctx.author.voice:
            raise VoiceError('You are neither connected to a voice channel nor specified a channel to join.')

        # Set the owner
        self.owner = ctx.author.id

        # Move the bot to the channel
        destination = channel or ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            await ctx.message("I am now active in: " + destination.name)
            return

        ctx.voice_state.voice = await destination.connect()

    @commands.command(name='kick', aliases=['leave', 'disconnect'])
    async def _kick(self, ctx: commands.Context):
        """Clears the queue and leaves the voice channel."""
        if not self.can_run(ctx, True):
            return await ctx.send("You do not have sufficient privileges, or the bot is not the correct state to run this command!")

        if not ctx.voice_state.voice:
            return await ctx.send('Not connected to any voice channel.')

        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild.id]
        self.owner = None

    @commands.command(name='next')
    async def _next(self, ctx: commands.Context):
        """Vote to skip a song. The requester can automatically skip.
        3 skip votes are needed for the song to be skipped.
        """
        if not self.can_run(ctx, True):
            return await ctx.send("You do not have sufficient privileges, or the bot is not the correct state to run this command!")

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
    async def _volume(self, ctx: commands.Context, *, volume: int):
        """Sets the volume of the player."""
        if not self.can_run(ctx, True):
            return await ctx.send("You do not have sufficient privileges, or the bot is not the correct state to run this command!")

        if not ctx.voice_state.is_playing:
            return await ctx.send('Nothing being played at the moment.')

        if 0 > volume > 100:
            return await ctx.send('Volume must be between 0 and 100')

        ctx.voice_state.volume = volume / 100
        await ctx.send('Volume of the player set to {}%'.format(volume))

    @commands.command(name='pause')
    async def _pause(self, ctx: commands.Context):
        """Pauses the currently playing song."""
        if not self.can_run(ctx, True):
            return await ctx.send("You do not have sufficient privileges, or the bot is not the correct state to run this command!")

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.pause()
            await ctx.message.add_reaction('⏯')

    @commands.command(name='resume')
    async def _resume(self, ctx: commands.Context):
        """Resumes a currently paused song."""
        if not self.can_run(ctx, True):
            return await ctx.send("You do not have sufficient privileges, or the bot is not the correct state to run this command!")

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_paused():
            ctx.voice_state.voice.resume()
            await ctx.message.add_reaction('⏯')

    @commands.command(name='stop_and_clear')
    async def _stop_and_clear(self, ctx: commands.Context):
        """Stops playing song and clears the queue."""
        if not self.can_run(ctx, True):
            return await ctx.send("You do not have sufficient privileges, or the bot is not the correct state to run this command!")

        ctx.voice_state.songs.clear()

        if not ctx.voice_state.is_playing:
            ctx.voice_state.voice.stop()
            await ctx.message.add_reaction('⏹')

    @commands.command(name='shuffle')
    async def _shuffle(self, ctx: commands.Context):
        """Shuffles the queue."""
        if not self.can_run(ctx, True):
            return await ctx.send("You do not have sufficient privileges, or the bot is not the correct state to run this command!")

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        ctx.voice_state.songs.shuffle()
        await ctx.message.add_reaction('✅')

    @commands.command(name='remove')
    async def _remove(self, ctx: commands.Context, index: int):
        """Removes a song from the queue at a given index."""
        if not self.can_run(ctx, True):
            return await ctx.send("You do not have sufficient privileges, or the bot is not the correct state to run this command!")

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        ctx.voice_state.songs.remove(index - 1)
        await ctx.message.add_reaction('✅')

    @commands.command(name='loop')
    async def _loop(self, ctx: commands.Context):
        """Loops the currently playing song.
        Invoke this command again to unloop the song.
        """
        if not self.can_run(ctx, True):
            return await ctx.send("You do not have sufficient privileges, or the bot is not the correct state to run this command!")

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
        if not self.can_run(ctx, True):
            return await ctx.send("You do not have sufficient privileges, or the bot is not the correct state to run this command!")

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
        if not self.can_run(ctx, True):
            return await ctx.send("You do not have sufficient privileges, or the bot is not the correct state to run this command!")

        if ctx.voice_state or ctx.voice_state.current:
            await ctx.send("No music playing!")
            return

        await ctx.send(embed=ctx.voice_state.current.create_embed())

    @commands.command(name='tag')
    async def _tag(self, ctx: commands.Context, *, terms: str):
        if not self.can_run(ctx, True):
            return await ctx.send("You do not have sufficient privileges, or the bot is not the correct state to run this command!")

        urls = find_urls(terms)
        if len(urls) != 1:
            raise CommandRunError(
                "The format for the tag command is: !tag tag1 tag2 tag3 url - the url must start with an http!")

        # Load existing
        user_songs = await self.manager.load_data_for_user_in_context(ctx, "music")
        if user_songs is None:
            user_songs = Music()

        # Append entry if applicable
        tags = terms.replace(urls[0], "").split()
        found_entry = None
        for entry in user_songs.music:
            if entry.url == urls[0]:
                entry.append_tags(tags)
                found_entry = entry
                break

        # Save out to userdata
        if not found_entry:
            entry = data.MusicEntry(tags, urls[0])
            user_songs.add_music(entry)
            await ctx.send("Tagged: " + str(entry))
        else:
            await ctx.send("Modified tags to: " + str(found_entry))

        await self.manager.save_data_for_user_in_context(ctx, "music", user_songs)

    @commands.command(name="tag_current")
    async def _tag_current(self, ctx: commands.Context, *, terms: str):
        if not self.can_run(ctx, True):
            return await ctx.send("You do not have sufficient privileges, or the bot is not the correct state to run this command!")

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

    @commands.command(name="list_tagged")
    async def _list_tagged(self, ctx: commands.Context):
        if not self.can_run(ctx, True):
            return await ctx.send("You do not have sufficient privileges, or the bot is not the correct state to run this command!")

        # Load existing
        user_songs = await self.manager.load_data_for_user_in_context(ctx, "music")
        if user_songs is None or len(user_songs.music) == 0:
            raise CommandRunError("You have not tagged any songs yet!")

        # We could be typing a lot here!
        async with ctx.typing():
            for entry in user_songs.music:
                await ctx.send(str(entry))

    @commands.command(name="forget_tag")
    async def _forget_tag(self, ctx: commands.Context, *, terms: str):
        if not self.can_run(ctx, True):
            return await ctx.send("You do not have sufficient privileges, or the bot is not the correct state to run this command!")

        urls = find_urls(terms)
        if len(urls) != 1:
            raise CommandRunError(
                "The format for the forget_tag command is: !forget_tag url <optional tags> - the url must start with an http!")

        # Load existing
        user_songs = await self.manager.load_data_for_user_in_context(ctx, "music")
        if user_songs is None or len(user_songs.music) == 0:
            raise CommandRunError("You have not tagged any songs yet!")

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
            await ctx.send("Removing entry: " + str(entry_to_remove))
        else:
            await ctx.send("Ammended entry to: " + str(entry))

        await self.manager.save_data_for_user_in_context(ctx, "music", user_songs)

    @commands.command(name="add_tagged")
    async def _add_tagged(self, ctx: commands.Context, *, terms: str):
        """
        Add a tagged song to the current queue

        :param ctx:
        :param terms:
        :return:
        """
        if not self.can_run(ctx, True):
            return await ctx.send("You do not have sufficient privileges, or the bot is not the correct state to run this command!")

        tags = terms.split()

        # Load existing
        user_songs = await self.manager.load_data_for_user_in_context(ctx, "music")
        if user_songs is None or len(user_songs.music) == 0:
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

    @commands.command(name="add")
    async def _add(self, ctx: commands.Context, *, info: str):
        """
        Add a song to the current queue.

        If there is no songs in the queue we can play it.

        :param ctx:
        :param terms:
        :return:
        """
        if not self.can_run(ctx, True):
            return await ctx.send("You do not have sufficient privileges, or the bot is not the correct state to run this command!")

        if not ctx.voice_state.voice:
            await ctx.send("I am not currently sitting in a channel, please summon me or start a game first!")

        async with ctx.typing():

            try:
                source = await YTDLSource.create_source(ctx, info, loop=self.bot.loop)

            except YTDLError as e:
                await ctx.send('An error occurred while processing this request: {}'.format(str(e)))

            else:
                song = Song(source)

                await ctx.voice_state.songs.put(song)

    @commands.command(name="everybody_dj")
    async def _everybody_can_dj(self, ctx):
        if self.is_owner(ctx):
            self.permissions = 3

        else:
            await ctx.send("Only an admin or the bot owner can use this command.")

    @commands.command(name="channel_dj")
    async def _channel_can_dj(self, ctx):
        if self.is_owner(ctx):
            self.permissions = 2

        else:
            await ctx.send("Only an admin or the bot owner can use this command.")

    @commands.command(name="owner_dj")
    async def _owner_can_dj(self, ctx):
        if self.is_owner(ctx):
            self.permissions = 1

        else:
            await ctx.send("Only an admin or the bot owner can use this command.")
