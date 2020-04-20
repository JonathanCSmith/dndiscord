class Games:
    def __init__(self, games=None):
        if games is None:
            games = list()

        self.games = games

    def add_game(self, game):
        for item in self.games:
            if game.name == item.name:
                return

        self.games.append(game)

    def get_game(self, name):
        for item in self.games:
            if item.name == name:
                return item


class GameEntry:
    def __init__(self, name, gm, gm_real, players=None):
        self.name = name
        self.gm = gm
        self.gm_real = gm_real

        if not players:
            players = list()
        self.players = players

    def __str__(self):
        return "Game entry for: " + self.name + " with gm: " + str(self.gm_real)


class PlayerEntry:
    def __init__(self, player_id, player_name, character_name):
        self.player_id = player_id
        self.player_name = player_name
        self.character_name = character_name

    def __str__(self):
        return "Player entry for: " + self.player_name + " with character " + self.character_name
