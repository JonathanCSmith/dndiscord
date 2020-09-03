from new_implementation.data.data import ModuleDataHolder, PermissionHolder


class GameData(ModuleDataHolder, PermissionHolder):
    def __init__(self, guild_id, game_name, game_master_id, game_master_name, game_channel="", gm_channel="", players=None, permissions=None):
        super().__init__()

        self.guild_id = guild_id
        self.game_name = game_name
        self.game_master_id = game_master_id
        self.game_master_name = game_master_name

        if game_channel == "":
            game_channel = "[DNDiscord] " + game_name
        self.game_channel = game_channel

        if gm_channel == "":
            gm_channel = "[DNDiscord] " + game_name + " (GM)"
        self.gm_channel = gm_channel

        if not players:
            players = list()
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

    def get_game_channel(self):
        return self.game_channel

    def set_game_channel(self, game_channel):
        self.game_channel = game_channel

    def get_gm_channel(self):
        return self.gm_channel

    def set_gm_channel(self, gm_channel):
        self.gm_channel = gm_channel

    def get_players(self):
        return self.players

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

    def set_permission_level(self, permission_name, level):
        self.permissions[permission_name] = level
