from discord.ext.commands import Bot

from new_implementation.modules.music.music import AmbianceCog


class EditMessageReceiveBot(Bot):
    def __init__(self, **options):
        super().__init__(**options)

    # Replay messages on edit
    async def on_message_edit(self, before, after):
        await self.on_message(after)


class SecondaryBot(EditMessageReceiveBot):
    def __init__(self, application, **kwargs):
        super().__init__(**kwargs)

        if application.is_ambiance_enabled():
            self.ambiance_cog = AmbianceCog(application)
            self.add_cog(self.ambiance_cog)