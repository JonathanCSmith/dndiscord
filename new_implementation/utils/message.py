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


async def send_message(ctx, message, is_dm=False, embed=None):
    if isinstance(message, LongMessage):
        async with ctx.typing():
            for message_part in message:
                if is_dm:
                    await ctx.author.send(message_part)
                    if embed:
                        await ctx.author.send(embed=embed)

                else:
                    await ctx.send(message_part)
                    if embed:
                        await ctx.author.send(embed=embed)
    else:
        if is_dm:
            await ctx.author.send("`" + message + "`")
            if embed:
                await ctx.author.send(embed=embed)

        else:
            await ctx.send("`" + message + "`")
            if embed:
                await ctx.author.send(embed=embed)
