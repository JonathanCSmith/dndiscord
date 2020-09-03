import discord

from new_implementation.utils import utils


class LongMessageIterator:
    def __init__(self, message, max_length=2000):
        self._message = message
        self._max_length = max_length
        self._current_index = 0

    def __next__(self):
        if self._current_index == self._message.entries:
            raise StopIteration

        current_length = 2  # For formatting
        this_message = list()

        # Allow for extra newline allowing it to display better
        this_message.append(" ")
        current_length += 2  # + 1 for the new line that will be added

        for i in range(self._current_index, self._message.entries):
            message_content = self._message.message_contents[i]
            if message_content is None:
                self._current_index = i + 1
                return "`" + "\n".join(this_message) + "`"

            length = current_length + self._message.lengths[i] + 1  # For new lines
            if length < self._max_length:
                this_message.append(message_content)
                current_length = length

            else:
                if current_length == 0:
                    raise StopIteration

                else:
                    self._current_index = i
                    return "`" + "\n".join(this_message) + "`"

        self._current_index = self._message.entries
        return "`" + "\n".join(this_message) + "`"


class LongMessage:
    def __init__(self):
        self.message_contents = list()
        self.lengths = list()
        self.entries = 0

    def add(self, content):
        self.entries += 1
        if content is None:
            self.message_contents.append(None)
            self.lengths.append(0)
        else:
            self.message_contents.append(content)
            self.lengths.append(len(content))

    def __iter__(self):
        return LongMessageIterator(self)


# TODO: Translation handling!
async def send_message(ctx, message, is_dm=False, channel=None, embed=None):
    if isinstance(message, LongMessage):
        async with ctx.typing():
            for message_part in message:
                if is_dm:
                    await ctx.author.send(message_part)

                elif channel:
                    await channel.send(message_part)

                else:
                    await ctx.send(message_part)
        if is_dm:
            await ctx.author.send(embed=embed)
        elif channel:
            await channel.send(embed=embed)
        else:
            await ctx.send(embed=embed)
    else:
        if is_dm:
            await ctx.author.send("`" + message + "`")
            if embed:
                await ctx.author.send(embed=embed)
        elif channel:
            await channel.send("`" + message + "`")
            if embed:
                await channel.send(embed=embed)
        else:
            await ctx.send("`" + message + "`")
            if embed:
                await ctx.send(embed=embed)


async def log(engine, ctx, message):
    # Log to file

    # Try to get the log channel
    guild_data = await engine.get_guild_data_for_context(ctx)
    channel_name = guild_data.get_log_channel_name()

    # Category handling
    category = discord.utils.get(ctx.guild.categories, name="Bot Channels")
    if category is None:
        category = await ctx.guild.create_category("Bot Channels")

    # Admin role
    admin_role = discord.utils.get(ctx.guild.roles, name="@admin")
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
        admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    # Channel handling
    channel = discord.utils.get(ctx.guild.text_channels, name=channel_name)
    if channel is None:
        channel = await ctx.guild.create_text_channel(channel_name, category=category, overwrites=overwrites)

    # Ensure the name is saved correctly
    guild_data.set_log_channel_name(channel.name)
    await engine.save_guild_data_for_context(ctx)

    # Inform
    return await send_message(ctx, message, is_dm=False, channel=channel, embed=None)
