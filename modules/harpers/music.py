import asyncio
import itertools
from asyncio import QueueFull
from random import random

import discord
from async_timeout import timeout
from discord.ext import commands

from modules.harpers.sources.ytdl_source import YTDLSource


class VoiceError(Exception):
    pass


class Song:
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


class SongRequests(asyncio.Queue):
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
