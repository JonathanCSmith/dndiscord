class Favourites:
    def __init__(self, music=None):
        if music is None:
            music = list()

        self.music = music

    def add_music(self, music):
        for item in self.music:
            if item.url == music.url:
                return

        self.music.append(music)


class MusicEntry:
    def __init__(self, tags, url):
        self.tags = list()
        if isinstance(tags, list):
            self.tags.extend(tags)
        else:
            self.tags.append(tags)
        self.url = url

    def append_tags(self, new_tags):
        for tag in new_tags:
            if tag not in self.tags:
                self.tags.append(tag)

    def __str__(self):
        return "Entry for: " + self.url + " with tags: " + str(self.tags)
