class Adventurer:
    def __init__(self, player_id, player_name, character_name):
        self.player_id = player_id
        self.player_name = player_name
        self.character_name = character_name

    def __str__(self):
        return "Player entry for: " + self.player_name + " with character " + self.character_name


class Game:
    def __init__(self, owning_guild, game_name, gm_id, gm_name, game_days=0, adventurers=None, permissions=None):
        self.owning_guild = owning_guild
        self.game_name = game_name
        self.gm_id = gm_id
        self.gm_name = gm_name
        self.game_days = game_days

        if not adventurers:
            adventurers = dict()
        self.adventurers = adventurers

        if permissions is None:
            permissions = dict()
        self.permissions = permissions

    def get_name(self):
        return self.game_name

    def is_gm(self, gm_id):
        return str(gm_id) == self.gm_id

    def increment_day(self):
        self.game_days += 1

    def get_days_passed(self):
        return self.game_days

    def get_adventurers(self):
        return self.adventurers

    def is_adventurer(self, player_id):
        return str(player_id) in self.adventurers

    def add_player(self, adventurer_entry):
        self.adventurers[str(adventurer_entry.player_id)] = adventurer_entry

    def get_permission_level(self, permissions_name):
        if permissions_name is self.permissions:
            return self.permissions[permissions_name]
        else:
            return -1

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

    def update_game(self, game):
        self.games[game.game_name] = game

    def remove_game(self, game: Game):
        if game.game_name not in self.games:
            return

        del self.games[game.game_name]
