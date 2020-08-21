class PlayerData:
    def __init__(self, player_id, player_name, character_name):
        self.player_id = player_id
        self.player_name = player_name
        self.character_name = character_name

    def get_player_id(self):
        return self.player_id

    def get_player_name(self):
        return self.player_name

    def get_character_name(self):
        return self.character_name

    def __str__(self):
        return "Player entry for: " + self.player_name + " - Their character is: " + self.character_name


class GameData:
    def __init__(self, guild_id, game_name, game_master_id, game_master_name, game_days=0, players=None, permissions=None):
        self.guild_id = guild_id
        self.game_name = game_name
        self.game_master_id = game_master_id
        self.game_master_name = game_master_name
        self.game_days = game_days

        if not players:
            players = dict()
        self.players = players

        if permissions is None:
            permissions = dict()
        self.permissions = permissions

    def get_name(self):
        return self.game_name

    def is_gm(self, gm_id):
        return gm_id == self.game_master_id

    def get_gm(self):
        return self.game_master_id

    def increment_day(self):
        self.game_days += 1

    def get_days_passed(self):
        return self.game_days

    def get_players(self):
        return self.players

    def get_player(self, player_id):
        return self.players[player_id]

    def is_player(self, player_id):
        return player_id in self.players

    def add_player(self, player):
        self.players[player.get_player_id()] = player

    def remove_player(self, player_id):
        if player_id in self.players:
            del self.players[player_id]

    def get_character(self, character_name):
        for player in self.players:
            if player.get_character_name() == character_name:
                return player

        return None

    def get_permission_level(self, permission_name):
        if permission_name is self.permissions:
            return self.permissions[permission_name]
        else:
            return -1
