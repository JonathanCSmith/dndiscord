class LanguagePack:
    def __init__(self, language):
        self.language = language
        self.data = dict()

    def add_data(self, prefix, data):
        for key, value in data.items():
            self.data[prefix + "." + key] = value

    def get_translation(self, key):
        if key in self.data:
            return self.data[key]

        return key


class TranslationIndex:
    def __init__(self, translation_sources=None):
        if translation_sources is None:
            translation_sources = dict()
        self.translation_sources = translation_sources


class TranslationSource:
    def __init__(self, key, relative_path, translations, is_guild_data):
        self.key = key
        self.relative_path = relative_path
        self.translations = translations.translation_sources
        self.is_guild_data = is_guild_data


class TranslationManager:
    def __init__(self):
        self.languages = dict()
        self.translation_sources = list()

    async def reload_translations(self, bot, ctx):
        for translation_source in self.translation_sources:
            # Generate a unique prefix
            if translation_source.is_guild_data:
                unique_prefix = str(ctx.guild.id) + "." + translation_source.key
            else:
                unique_prefix = translation_source.key

            # For each of our provided language packs
            for type, file in translation_source.translations.items():
                if type not in self.languages:
                    language = LanguagePack(type)
                    self.languages[type] = language
                else:
                    language = self.languages[type]

                if translation_source.is_guild_data:
                    data = await bot.load_data_from_data_path_for_guild(ctx, translation_source.relative_path, file)
                else:
                    data = await bot.load_data_from_data_path(translation_source.relative_path, file)

                if data:
                    language.add_data(unique_prefix, data)

    async def load_translations(self, bot, ctx, translation_source: TranslationSource):
        # Generate a unique prefix
        if translation_source.is_guild_data:
            unique_prefix = str(ctx.guild.id) + "." + translation_source.key
        else:
            unique_prefix = translation_source.key

        # For each of our provided language packs
        for type, file in translation_source.translations.items():
            if type not in self.languages:
                language = LanguagePack(type)
                self.languages[type] = language
            else:
                language = self.languages[type]

            if translation_source.is_guild_data:
                data = await bot.load_data_from_data_path_for_guild(ctx, translation_source.relative_path, file)
            else:
                data = await bot.load_data_from_data_path(translation_source.relative_path, file)

            if data:
                self.translation_sources.append(translation_source)
                language.add_data(unique_prefix, data)

    async def get_translation(self, current_language, ctx, key):
        # Get the relevant key
        guild_agnostic_key = key
        guild_speicifc_key = str(ctx.guild.id) + "." + guild_agnostic_key

        # Load a language or default
        if current_language in self.languages:
            language = self.languages[current_language]

        elif "default" in self.languages:
            language = self.languages["default"]

        # If we don't find anything we return the key
        else:
            return key

        # Try getting a guild specific implementation first, if not just grab some at our root
        value = language.get_translation(guild_speicifc_key)
        if value == guild_speicifc_key:
            value = language.get_translation(guild_agnostic_key)

        if value == guild_agnostic_key:
            print("untranslated: " + guild_agnostic_key)

        return value
