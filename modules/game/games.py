class Game:
    def __init__(self, owning_guild, game_name, gm_id, gm_name, players=None, permissions=None):
        self.owning_guild = owning_guild
        self.game_name = game_name
        self.gm_id = gm_id
        self.gm_name = gm_name

        if not players:
            players = dict()
        self.players = players

        if permissions is None:
            permissions = dict()
        self.permissions = permissions

    def get_name(self):
        return self.game_name

    def is_gm(self, gm_id):
        return gm_id == self.gm_id

    def is_player(self, player_id):
        return player_id in self.players

    def get_permission_level(self, permissions_name):
        if permissions_name is self.permissions:
            return self.permissions[permissions_name]

    def set_permissions_level(self, permissions_name, level):
        self.permissions[permissions_name] = level


class GuildData:
    def __init__(self, guild_id, permissions=None, games=None):
        self.guild_id = guild_id

        if permissions is None:
            permissions = dict()
        self.permissions = permissions

        if games is None:
            games = dict()
        self.games = games

    def get_permission_level(self, permissions_name):
        if permissions_name is self.permissions:
            return self.permissions[permissions_name]

    def set_permissions_level(self, permissions_name, level):
        self.permissions[permissions_name] = level

    def get_game(self, game_name):
        if game_name in self.games:
            return self.games[game_name]

        return None

    def add_game(self, game: Game):
        if game.game_name in self.games:
            raise RuntimeError("You tried to overwrite a game called: " + game.game_name)

        self.games[game.game_name] = game

    def remove_game(self, game: Game):
        if game.game_name not in self.games:
            return

        del self.games[game.game_name]
