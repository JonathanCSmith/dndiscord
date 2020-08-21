from new_implementation.core.engine import EditMessageReceiveBot


# This is the ancillary bot
from new_implementation.modules.music.music import AmbianceCog


class SecondaryBot(EditMessageReceiveBot):
    def __init__(self, application, **kwargs):
        super().__init__(**kwargs)

        if application.is_ambiance_enabled():
            self.ambiance_cog = AmbianceCog(self, application)
            self.add_cog(self.ambiance_cog)
