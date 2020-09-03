from new_implementation.audio.audio import AudioCog


class MusicCog(AudioCog):
    def __init__(self, engine):
        super().__init__(engine, "music_player", "music player")


class AmbianceCog(AudioCog):
    def __init__(self, engine):
        super().__init__(engine, "ambiance_player", "ambiance player")
