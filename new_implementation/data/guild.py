from discord import Role

from new_implementation.data.data import PermissionHolder


class GuildData(PermissionHolder):
    def __init__(self, guild_id, log_channel_name="dndiscord-logging", game_category_prefix="[DnDiscord] ", game_channel_prefix="dndiscord-", game_channel_suffix="", game_gm_channel_prefix="dndiscord-", game_gm_channel_suffix="-gm", administrator_roles=None, games=None, permissions=None):
        self.guild_id = guild_id
        self.log_channel_name = log_channel_name
        self.game_category_prefix = game_category_prefix
        self.game_channel_prefix = game_channel_prefix
        self.game_channel_suffix = game_channel_suffix
        self.game_gm_channel_prefix = game_gm_channel_prefix
        self.game_gm_channel_suffix = game_gm_channel_suffix

        if not administrator_roles:
            administrator_roles = list()
        self.administrator_roles = administrator_roles

        if not games:
            games = list()
        self.games = games

        if permissions is None:
            permissions = dict()
        self.permissions = permissions

    def get_administrator_roles(self):
        return self.administrator_roles

    def add_administrative_role(self, role: Role):
        self.administrator_roles.append(role.name)

    def remove_administrative_role(self, role: Role):
        self.administrator_roles.remove(role.name)

    def get_log_channel_name(self):
        return self.log_channel_name

    def set_log_channel_name(self, log_channel_name):
        self.log_channel_name = log_channel_name

    def get_game_category_prefix(self):
        return self.game_channel_prefix

    def get_game_channel_prefix(self):
        return self.game_channel_prefix

    def get_game_channel_suffix(self):
        return self.game_channel_suffix

    def get_game_gm_channel_prefix(self):
        return self.game_gm_channel_prefix

    def get_game_gm_channel_suffix(self):
        return self.game_gm_channel_suffix

    def set_logging_channel(self, channel_name):
        self.log_channel_name = channel_name

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

    def set_permissions_level(self, permission_name, level):
        self.permissions[permission_name] = level
