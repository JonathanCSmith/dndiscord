class GuildData:
    def __init__(self, guild_id, games=None, permissions=None):
        self.guild_id = guild_id

        if not games:
            games = list()
        self.games = games

        if permissions is None:
            permissions = dict()
        self.permissions = permissions

    def get_games(self):
        return self.games

    def add_game(self, game):
        self.games.append(game)

    def remove_game(self, game):
        self.games.remove(game)

    def get_permission_level(self, permission_name):
        if permission_name is self.permissions:
            return self.permissions[permission_name]
        else:
            return -1
