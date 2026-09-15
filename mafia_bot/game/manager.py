from .models import Game


class GameManager:
    def __init__(self) -> None:
        self.games: dict[int, Game] = {}
        self.player_chat: dict[int, int] = {}

    def get_game(self, chat_id: int) -> Game | None:
        return self.games.get(chat_id)

    def get_game_by_player(self, user_id: int) -> Game | None:
        chat_id = self.player_chat.get(user_id)
        if chat_id is None:
            return None
        return self.games.get(chat_id)

    def create_game(self, chat_id: int, host_id: int) -> Game:
        game = Game(chat_id=chat_id, host_id=host_id)
        self.games[chat_id] = game
        return game

    def register_player(self, game: Game, user_id: int) -> None:
        self.player_chat[user_id] = game.chat_id

    def remove_game(self, chat_id: int) -> Game | None:
        game = self.games.pop(chat_id, None)
        if game:
            for user_id in list(game.players.keys()):
                if self.player_chat.get(user_id) == chat_id:
                    self.player_chat.pop(user_id, None)
            if game.task and not game.task.done():
                game.task.cancel()
        return game


manager = GameManager()
