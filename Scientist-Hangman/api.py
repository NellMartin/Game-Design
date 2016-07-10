import logging
import endpoints
from protorpc import remote, messages
from google.appengine.api import memcache
from google.appengine.api import taskqueue
from decimal import Decimal

from models import User, Game, Score
from models import StringMessage, NewGameForm, GameForm, MakeMoveForm,\
    ScoreForms, GameForms, RankForms
from utils import get_by_urlsafe, set_score_at

# ---- Requests ----
NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
GET_GAME_REQUEST = endpoints.ResourceContainer(
        urlsafe_game_key=messages.StringField(1),)
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(
    MakeMoveForm,
    urlsafe_game_key=messages.StringField(1),)
USER_REQUEST = endpoints.ResourceContainer(user_name=messages.StringField(1),
                                           email=messages.StringField(2))
GET_HIGH_SCORE_REQUEST = endpoints.ResourceContainer(
        number_of_results=messages.IntegerField(1),)

MEMCACHE_MOVES_REMAINING = 'MOVES_REMAINING'

@endpoints.api(name='scientific_hangman', version='v1')
class HangmanPlayAPI(remote.Service):

    """Scientific Hangman API"""
    @endpoints.method(request_message=USER_REQUEST,
                      response_message=StringMessage,
                      path='user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """Create a User. Requires a unique username"""
        if User.query(User.name == request.user_name).get():
            raise endpoints.ConflictException(
                    'A User with that name already exists!')
        user = User(name=request.user_name, email=request.email)
        user.put()
        return StringMessage(message='User {} created!'.format(
                request.user_name))

    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='game',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        """Creates new game"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
        try:
            game = Game.new_game(user.key, request.min,
            request.max, request.attempts)
        except ValueError:
            raise endpoints.BadRequestException('Maximum must be greater '
                                                'than minimum!')

        # Use a task queue to update the average attempts remaining.
        # This operation is not needed to complete the creation of a new game
        # so it is performed out of sequence.
        taskqueue.add(url='/tasks/cache_average_attempts')
        return game.to_form('Good luck playing Hangman!')

    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='make_move',
                      http_method='PUT')
    def make_move(self,request):
      """Makes a move. Returns a game state with a message, and analyze guesses"""
      game = get_by_urlsafe(request.urlsafe_game_key, Game)
      user = game.user.get()
      if game.game_over:
        return game.to_form('Game has ended!')
      guess_Word = list(game.target)
      score = []
      [score.append('*') for i in range(len(guess_Word))]
      guess = request.guess.upper()
      # Validation of user entries
      if len(guess) != 1:
        msg = 'Please enter only one character.'
      elif guess.isalpha() == False:
        msg = 'Please dont enter a number.'
      # If user didn't get the correct answer. Substract 1.
      else:
        if guess not in guess_Word:
          game.attempts_remaining -=1
          if game.attempts_remaining > 0:
            [set_score_at(score,guess_Word,i) for i in game.correct]
            msg = "Incorrect, you have %i attempts remaining. %s " % (game.attempts_remaining, ''.join(score))
            game.add_game_history(msg,guess)
          else:
            msg = "Game Over!. The answer was %s. Game Over " % ''.join(guess_Word)
            user.loss +=1
            user.win_ratio = self.analyze_guess(user.win, user.loss)
            user.put()
            game.add_game_history(msg,guess)
            game.end_game()
        elif guess in guess_Word:
            [game.correct.append(i) for i in range(len(guess_Word)) if guess_Word[i] == guess and i not in game.correct]
            game.put()
            [set_score_at(score,guess_Word,i) for i in game.correct]
            msg = ''.join(score)
        if len(game.correct) == len(guess_Word):
          user.win +=1
          user.win_ratio = self.analyze_guess(user.win, user.loss)
          user.put()
          game.end_game(True)
          msg = "You've won. The word was %s " % ''.join(game.target)
          game.add_game_history(msg,guess)
      return game.to_form(msg)

    def analyze_guess(self, user_win, user_loss):
        "Retrieves score of user win/loss ratio."
        step = Decimal(user_win)/(Decimal(user_loss + user_win))
        step = round(step,3)
        return step

    @endpoints.method(response_message=ScoreForms,
                      path='scores',
                      name='get_scores',
                      http_method='GET')
    def get_scores(self, request):
        """Return all scores"""
        return ScoreForms(items=[score.to_form() for score in Score.query()])

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=ScoreForms,
                      path='scores/user/{user_name}',
                      name='get_user_scores',
                      http_method='GET')
    def get_user_scores(self, request):
        """Returns all of an individual User's scores"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
        scores = Score.query(Score.user == user.key)
        return ScoreForms(items=[score.to_form() for score in scores])

    # History - User games.
    @endpoints.method(request_message=USER_REQUEST,
                  response_message=GameForms,
                  path='games/user/{user_name}',
                  name='get_user_games',
                  http_method='GET')
    def get_user_games(self, request):
        """Returns all of an individual User's games not completed."""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
        games = Game.query(Game.user == user.key).filter(Game.game_over == False)
        return GameForms(items=[game.to_form('Active games for this user are...!') for game in games])

    # Cancel games.
    @endpoints.method(request_message=GET_GAME_REQUEST,
                  response_message=StringMessage,
                  path='game/{urlsafe_game_key}/cancel',
                  name='cancel_game',
                  http_method='DELETE')
    def cancel_game(self, request):
        """Cancel an active game."""
        game = get_by_urlsafe(request.urlsafe_game_key,Game)
        if not game:
            raise endpoints.NotFoundException(
                    'A Game with that key does not exist!')
        if game.game_over:
          return game.to_form('This game has ended.')
        game.key.delete()
        return StringMessage(message = 'Game Cancelled!')

    # Get High Scores
    @endpoints.method(request_message = GET_HIGH_SCORE_REQUEST,
                      response_message = ScoreForms,
                      path = 'scores/high_scores',
                      name ='get_high_scores',
                      http_method='GET')
    def get_high_scores(self,request):
      """Return all scores ordered by total points"""
      if request.number_of_results:
        scores = Score.query(Score.won == True).order(Score.attempts_allowed,Score.guesses).fetch(request.number_of_results)
      else:
        scores = Score.query(Score.won == True).order(Score.attempts_allowed,Score.guesses).fetch()
      return ScoreForms(items=[score.to_form() for score in scores])

    # Ranking Users.
    @endpoints.method(response_message=RankForms,
                      path='scores/user_rankings',
                      name='get_user_rankings',
                      http_method='GET')
    def get_user_rankings(self, request):
        """Return all users ordered by win ratio"""
        users = User.query().order(-User.win_ratio)
        return RankForms(items=[user.rank_form() for user in users])

    # Get game history
    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=StringMessage,
                      path='game/{urlsafe_game_key}/get_game_history',
                      name='get_game_history',
                      http_method='GET')
    def get_game_history(self, request):
        """Return summary of each single game guesses."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if not game:
            raise endpoints.NotFoundException('Game not found')
        return StringMessage(message=str(game.history))

    @endpoints.method(response_message=StringMessage,
                      path='games/average_attempts',
                      name='get_average_attempts_remaining',
                      http_method='GET')
    def get_average_attempts(self, request):
        """Get the cached average moves remaining"""
        return StringMessage(message=memcache.get(MEMCACHE_MOVES_REMAINING) or '')

    @staticmethod
    def _cache_average_attempts():
        """Populates memcache with the average moves remaining of Games"""
        games = Game.query(Game.game_over == False).fetch()
        if games:
            count = len(games)
            total_attempts_remaining = sum([game.attempts_remaining
                                        for game in games])
            average = float(total_attempts_remaining)/count
            memcache.set(MEMCACHE_MOVES_REMAINING,
                         'The average moves remaining is {:.2f}'.format(average))


api = endpoints.api_server([HangmanPlayAPI])
