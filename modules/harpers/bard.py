import asyncio

from async_timeout import timeout
from discord.ext import commands

from modules.harpers.music import SongRequests


class BardError(Exception):
    pass


class Bard:
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.exists = True
        self.current = None
        self.voice = None
        self.next = asyncio.Event()
        self.set_list = SongRequests()

        self._loop = False
        self._volume = 0.5
        self.skip_votes = set()

        self.audio_player = bot.loop.create_task(self.audio_player_task())

        self.info = None

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
        try:
            while True:
                self.next.clear()

                if not self.loop:
                    try:
                        async with timeout(600):  # 10 minutes
                            self.current = await self.set_list.get()

                    except asyncio.TimeoutError:
                        self.bot.loop.create_task(self.stop())
                        self.exists = False
                        return

                self.current.source.volume = self._volume
                self.voice.play(self.current.source, after=self.play_next_song)
                await self.info.send(embed=self.current.create_embed())

                await self.next.wait()
        except:
            print("HMM")

    def play_next_song(self, error=None):
        if error:
            raise BardError(str(error))

        self.next.set()

    def skip(self):
        self.skip_votes.clear()

        if self.is_playing:
            self.voice.stop()

    async def stop(self):
        self.set_list.clear()

        if self.voice:
            await self.voice.disconnect()
            self.voice = None
