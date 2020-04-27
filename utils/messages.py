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
            length = current_length + self._message.lengths[i] + 1  # For new lines
            if length < self._max_length:
                this_message.append(self._message.message_contents[i])
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
        self.message_contents.append(content)
        length = len(content)
        self.lengths.append(length)
        self.entries += 1

    def __iter__(self):
        return LongMessageIterator(self)
