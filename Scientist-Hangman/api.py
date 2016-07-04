# -*- coding: utf-8 -*-`
"""api.py - Create and configure the Game API exposing the resources.
This can also contain game logic. For more complex games it would be wise to
move game logic to another file. Ideally the API will be simple, concerned
primarily with communication to/from the API's users."""


import logging
import endpoints
from protorpc import remote, messages
from google.appengine.api import memcache
from google.appengine.api import taskqueue

from models import User, Game, Score
from models import StringMessage, NewGameForm, GameForm, MakeMoveForm,\
    ScoreForms
from utils import get_by_urlsafe

NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
GET_GAME_REQUEST = endpoints.ResourceContainer(
        urlsafe_game_key=messages.StringField(1),)
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(
    MakeMoveForm,
    urlsafe_game_key=messages.StringField(1),)
USER_REQUEST = endpoints.ResourceContainer(user_name=messages.StringField(1),
                                           email=messages.StringField(2))

MEMCACHE_MOVES_REMAINING = 'MOVES_REMAINING'

@endpoints.api(name='guess_a_number', version='v1')
class GuessANumberApi(remote.Service):

    """Game API"""
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
                                 request.max, request.attempts, request.target_word,
                                 request.correct_attempts, request.letters_discovered)

        except ValueError:
            raise endpoints.BadRequestException('Maximum must be greater '
                                                'than minimum!')

        # Use a task queue to update the average attempts remaining.
        # This operation is not needed to complete the creation of a new game
        # so it is performed out of sequence.
        taskqueue.add(url='/tasks/cache_average_attempts')
        return game.to_form('Good luck playing Guess a Number!')

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Return the current game state."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            game.letters_discovered = game.target_word
            return game.to_form('Time to make a move!')
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='make_move',
                      http_method='PUT')
    def make_move(self, request):
        """Makes a move. Returns a game state with message"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game.game_over:
            return game.to_form('Game already over!')

        len_correct_word = len(list(game.target_word))

        if len(request.guess) > 1 :
            raise endpoints.BadRequestException('Only one capitalized letter '
                                                'is allowed!')

        if request.guess in game.target_word:

            game.correct_attempts += self.analyze_guess(request.guess, game.target_word)

            game.letters_discovered = self.update_word(request.guess, game.target_word, game.letters_discovered)


            if self.guessedThemAll(game.letters_discovered, game.target_word):
                game.end_game(True)
                game.put()
                return game.to_form('You have won!')
            # Update letters discovered.
            game.put()
            return game.to_form('Correct guess!')

        if request.guess not in game.target_word:
            game.attempts_remaining -= 1
            msg = 'Wrong guess!'

        if game.attempts_remaining < 1:
            game.end_game(False)
            return game.to_form(msg + ' Word was: '+ game.target_word+' Game over!')
        else:
            game.put()
            return game.to_form(msg)

    def analyze_guess(self, request_guess_char, target_word):
        "Retrieves amount of matching chars in target_word from user input."
        count = 0
        word = list(target_word)
        for c in word:
            if  request_guess_char in c:
                count +=1
        return count

    def update_word(self, request_guess_char, target_word, current_word):
        "Give feedback to user on how he/she are discovering letters."
        letters = []
        letters.append(request_guess_char)
        word = ""
        currentWord = []

        if current_word == None or current_word == "":
            stars= []
            stars = list(len(target_word) * '*')
            for index,letter in enumerate(target_word):
                if request_guess_char == letter:
                    stars[index] = request_guess_char
        else:
            stars= []
            if len(current_word) > 0 :
                stars = list(current_word)
                for index,letter in enumerate(target_word):
                    if request_guess_char == letter:
                        stars[index] = request_guess_char

        word= ''.join(stars)
        return word

    def guessedThemAll(self, guessedWord, target_word):
        "Retrieves amount of matching chars in target_word from user input."
        if guessedWord == target_word:
            return True
        else:
            return False

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


api = endpoints.api_server([GuessANumberApi])
