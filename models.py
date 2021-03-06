"""models.py - This file contains the class definitions for the Datastore
entities used by the Game. Because these classes are also regular Python
classes they can include methods (such as 'to_form' and 'new_game')."""
from datetime import date
from protorpc import messages
from google.appengine.ext import ndb
from utils import word_selected


class User(ndb.Model):
    """User profile for game."""
    name = ndb.StringProperty(required=True)
    email =ndb.StringProperty()
    win = ndb.IntegerProperty(default = 0)
    loss = ndb.IntegerProperty(default = 0)
    win_ratio = ndb.FloatProperty()
    def rank_form(self):
        return RankForm(user_name = self.name,
                        email = self.email,
                        win_ratio = self.win_ratio,
                        win = self.win,
                        loss = self.loss)

class Game(ndb.Model):
    """Game object"""
    target = ndb.StringProperty(required=True)
    attempts_allowed = ndb.IntegerProperty(required=True)
    attempts_remaining = ndb.IntegerProperty(required=True)
    game_over = ndb.BooleanProperty(required=True, default=False)
    user = ndb.KeyProperty(required=True, kind='User')
    correct = ndb.IntegerProperty(repeated = True)
    history = ndb.PickleProperty(required=True, default=[])
    @classmethod
    def new_game(cls, user, min, max, attempts):
        """Creates and returns a new game"""
        game = Game(user=user,
                    target=word_selected(min,max),
                    attempts_allowed=attempts,
                    attempts_remaining=attempts,
                    game_over=False,
                    )
        game.history = []
        game.put()
        return game

    def to_form(self, message):
        """Returns a GameForm representation of the Game"""
        form = GameForm()
        form.urlsafe_key = self.key.urlsafe()
        form.user_name = self.user.get().name
        form.attempts_remaining = self.attempts_remaining
        form.game_over = self.game_over
        form.message = message
        return form

    def add_game_history(self, result, guess):
        self.history.append({'message': result, 'guess': guess})
        self.put()

    def end_game(self, won=False):
        """Ends the game - if won is True, the player won. - if won is False,
        the player lost."""
        self.game_over = True
        self.put()
        # Add the game to the score 'board'
        score = Score(user=self.user, date=date.today(), won=won,
                      guesses=self.attempts_allowed - self.attempts_remaining, target=self.target,
                      attempts_allowed=self.attempts_allowed)
        score.put()

class Score(ndb.Model):
    """Score object"""
    user = ndb.KeyProperty(required=True, kind='User')
    date = ndb.DateProperty(required=True)
    won = ndb.BooleanProperty(required=True)
    target= ndb.StringProperty()
    guesses = ndb.IntegerProperty(required=True)
    attempts_allowed = ndb.IntegerProperty(required = True)

    def to_form(self):
        return ScoreForm(user_name=self.user.get().name,
                         won=self.won,
                         date=str(self.date),
                         target=self.target,
                         attempts_allowed=self.attempts_allowed,
                         guesses=self.guesses)

class GameForm(messages.Message):
    """GameForm for outbound game state information"""
    urlsafe_key = messages.StringField(1, required=True)
    attempts_remaining = messages.IntegerField(2, required=True)
    game_over = messages.BooleanField(3, required=True)
    message = messages.StringField(4, required=True)
    user_name = messages.StringField(5, required=True)

class NewGameForm(messages.Message):
    """Used to create a new game"""
    user_name = messages.StringField(1, required=True)
    min = messages.IntegerField(2, default=1)
    max = messages.IntegerField(3, default=10)
    attempts = messages.IntegerField(4, default=10)

class MakeMoveForm(messages.Message):
    """Used to make a move in an existing game"""
    guess = messages.StringField(1, required=True)

class ScoreForm(messages.Message):
    """ScoreForm for outbound Score information"""
    user_name = messages.StringField(1, required=True)
    date = messages.StringField(2, required=True)
    won = messages.BooleanField(3, required=True)
    guesses = messages.IntegerField(4, required=True)
    target = messages.StringField(5)
    attempts_allowed =  messages.IntegerField(6)

class GameForms(messages.Message):
    items = messages.MessageField(GameForm,1,repeated = True)

class ScoreForms(messages.Message):
    """Return multiple ScoreForms"""
    items = messages.MessageField(ScoreForm, 1, repeated=True)

class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)

class RankForm(messages.Message):
    """Return a single RankForm"""
    user_name = messages.StringField(1,required = True)
    email = messages.StringField(2)
    win_ratio = messages.FloatField(3)
    win = messages.IntegerField(4)
    loss = messages.IntegerField(5)

class RankForms(messages.Message):
    """Return multiple RankForms"""
    items = messages.MessageField(RankForm,1,repeated = True)