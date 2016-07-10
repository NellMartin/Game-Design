#Full Stack Nanodegree Project 4 Scientific Hangman

## Set-Up Instructions:
1.  Update the value of application in app.yaml to the app ID you have registered
 in the App Engine admin console and would like to use to host your instance of this sample.
2.  Run the app with the devserver using dev_appserver.py DIR, and ensure it's
 running by visiting the API Explorer - by default localhost:8080/_ah/api/explorer.
3.  (Optional) Generate your client library(ies) with the endpoints tool.
 Deploy your application.

 ---

##Game Description:
Scientific Hangman is a single-player scientific word guessing game, exactly as the traditional Hangman game. Ready for some udacious science word game?. Each game begins with a random chosen word, a word that is related to a traditional day-to day scienctific world.  The user will have the option to choose the minimum and maximum values of permitted attempts per each game.

Once the user has entered these values, the game will give a special key the `url_safe_key`. Through using the `Make_move` endpoint the user will be able to guess the words letter. Each time the execution takes place, the user, will know if the word contains that letter or if he/she needs to try again. Upon the successfull whole entry of the world has been guessed, or upon the attempts remaining is 0, the user will know the receive a message of the whole secret word.  After each attempt, the user will know how many attempts remains, and also how the word is being discovered. Will the Scientific Hangman survive?

*Scoring*
This game provides a way of cancelling an non-completed game, track of the user win/losses ratio, and keep a history high scores for each user.

This game will let a user with the lowest attempts win,s to be the highest score. In other words, if you guess the word right without losing any point of attempts remaining, you'll be likely to be in one of the tops position in the leader board.

##Files Included:
 - api.py: Contains endpoints and game playing logic.
 - app.yaml: App configuration.
 - cron.yaml: Cronjob configuration.
 - main.py: Handler for taskqueue handler.
 - models.py: Entity and message definitions including helper methods.
 - utils.py: Helper function for retrieving ndb.Models by urlsafe Key string.
 - index.py:  Automatic generated file that provides the indexing for the Kinds.
 - scientificWords.txt:  A static file filled with scientific words that are randomly selected by the game.

 ---
##Endpoints Included:
*Defaults*
 - **create_user**
    - Path: 'user'
    - Method: POST
    - Parameters: user_name, email (optional)
    - Returns: Message confirming creation of the User.
    - Description: Creates a new User. user_name provided must be unique. Will
    raise a ConflictException if a User with that user_name already exists.

 - **new_game**
    - Path: 'game'
    - Method: POST
    - Parameters: user_name, min, max, attempts
    - Returns: GameForm with initial game state.
    - Description: Creates a new Game. user_name provided must correspond to an
    existing user - will raise a NotFoundException if not. Min must be less than
    max. Min stands for minimum attempts, and max stand for maximum attempts permitted.
    Also adds a task to a task queue to update the average moves remaining
    for active games.

 - **get_game**
    - Path: 'game/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameForm with current game state.
    - Description: Returns the current state of a game.

 - **make_move**
    - Path: 'game/{urlsafe_game_key}'
    - Method: PUT
    - Parameters: urlsafe_game_key, guess
    - Returns: GameForm with new game state.
    - Description: Accepts a 'guess' and returns the updated state of the game.
    If this causes a game to end, a corresponding Score entity will be created.

 - **get_scores**
    - Path: 'scores'
    - Method: GET
    - Parameters: None
    - Returns: ScoreForms.
    - Description: Returns all Scores in the database.

 - **get_user_scores**
    - Path: 'scores/user/{user_name}'
    - Method: GET
    - Parameters: user_name
    - Returns: ScoreForms.
    - Description: Returns all Scores recorded by the provided player (unordered).
    Will raise a NotFoundException if the User does not exist.

 - get_average_attempts
    - Path: 'games/average_attempts'
    - Method: GET
    - Parameters: None
    - Returns: StringMessage
    - Description: Get the cached average moves remaining.

*Expanded*
 - **get_user_games**
    - Path: 'games/user/{user_name}'
    - Method: GET
    - Parameters: user_name
    - Returns: GameForms
    - Description: Returns all Active Games recorded by the username of the player.

 - **cancel_game**
    - Path: 'game/{urlsafe_game_key}/cancel'
    - Method: DELETE
    - Parameters: urlsafe_game_key
    - Returns: StringMessage.
    - Description: Returns a message confirming the cancellation of the game. Canceling a completed game will raise "This game has ended" error or will raice a 'A Game with that key does not exist! ' exception.

 - *get_high_scores*
    - Path: 'scores/high_scores'
    - Method: GET
    - Parameters: number_of_results
    - Returns: ScoreForms
    - Description: Returns number of Scores in the database limited by number_of_results and ordered by attempts_allowed, and guesses in ascending order.

 - *get_user_rankings*
    - Path: 'scores/user_rankings'
    - Method: GET
    - Parameters: None
    - Returns: RankForms
    - Description: Returns all winning Scores in the database ordered by win_ratio in descending order.

 - *get_game_history*
    - Path: 'game/{urlsafe_game_key}/get_game_history'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: StringMessage
    - Description: Returns a list of dictionary-pairs of messages and guesses recorded in make_move.


##Models Included:
 - **User**
    - Stores unique user_name and (optional) email address.

 - **Game**
    - Stores unique game states. Associated with User model via KeyProperty.

 - **Score**
    - Records completed games. Associated with Users model via KeyProperty.

##Forms Included:
 - **GameForm**
    - Representation of a Game's state (urlsafe_key, attempts_remaining,
    game_over flag, message, user_name).
 - **GameForms**
    - Representation of a Game's state (urlsafe_key, attempts_remaining,
    game_over flag, message, user_name) as an iterative item.
 - **NewGameForm**
    - Used to create a new game (user_name, min, max, attempts)
 - **MakeMoveForm**
    - Inbound make move form (guess).
 - **ScoreForm**
    - Representation of a completed game's Score (user_name, date, won flag,
    guesses, target, attemps_allowed).
 - **ScoreForms**
    - Multiple ScoreForm container.
 - **StringMessage**
    - General purpose String container.
 - **RankForm**
    - Representation of a user ranking along with game history (user_name, email, win, loss, win_ratio).
 - **StringMessage**
    - General purpose String container.
