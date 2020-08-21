class UserData:
    def __init__(self, user_id, games=None):
        self.user_id = user_id

        if not games:
            games = list()
        self.games = games

    def get_user_id(self):
        return self.user_id

    def get_games(self):
        return self.games

    def add_game(self, game):
        self.games.append(game)

    def remove_game(self, game):
        self.games.remove(game)
