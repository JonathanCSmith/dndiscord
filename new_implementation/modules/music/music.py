from new_implementation.audio.audio import AudioCog


class MusicCog(AudioCog):
    def __init__(self, bot, engine):
        super().__init__(bot, engine, "music_player", "music player")


class AmbianceCog(AudioCog):
    def __init__(self, bot, engine):
        super().__init__(bot, engine, "ambiance_player", "ambiance player")
