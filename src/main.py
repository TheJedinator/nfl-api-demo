import datetime
from enum import Enum
from typing import List

import requests
import uvicorn
from fastapi import FastAPI, Response
from pydantic import BaseModel

app = FastAPI()


# This is more to showcase that if there were more options we could just use an enum for it
class LeagueModel(str, Enum):
    NFL = "NFL"
    # CFL = "CFL"
    # NHL = "NHL"


# Data formatted as specified by client
class ScrubbedData(BaseModel):
    event_id: int
    event_date: datetime.date
    event_time: datetime.time
    away_team_id: int
    away_nick_name: str
    away_city: str
    away_rank: int
    away_rank_points: float
    home_team_id: int
    home_nick_name: str
    home_city: str
    home_rank: int
    home_rank_points: float


# This wasn't specified in the request doc but the endpoint was, response are better with models.
class RankingsModel(BaseModel):
    team_id: int
    team: str
    rank: int
    last_week: int
    points: float
    modifier: float
    adjusted_points: float


# FastAPI has built in parsing/data validation using pydantic, specifying a model ensures it's one of our ENUMS,
# Specifying date time format ensures it's a date, I will not get into date time formats here
@app.get("/scoreboard/{league}/{start_date}/{end_date}", response_model=List[ScrubbedData])
def get_scoreboard(league: LeagueModel, start_date: datetime.date, end_date: datetime.date):
    return third_party_board(league, start_date, end_date)


# Endpoint to get all rankings, assumption is made that this data goes stale as it has last updated date
# Other assumption was that we only want the actual data objects
@app.get("/team_rankings/{league}", response_model=List[RankingsModel])
def get_rankings(league: LeagueModel):
    return get_rankings(league)


# This is the helper function to offload the processing from the main request function
# If this was cleaner data or I spent more time with the FastAPI/Pydantic Models I could serialize the json using a 
# model For now I am satisfied to just parse it and ensure it's validated before being sent back..
def third_party_board(league, start, end):
    try:
        # Get the results from the third party
        board = requests.get(
            f'https://delivery.chalk247.com/scoreboard/{league}/{start}/{end}.json?api_key=74db8efa2a6db279393b433d97c2bc843f8e32b0')
        
        # make sure the result is not the instance of an error, if it is, we'll return that instead.
        if board.ok:
            board = board.json().get('results')
            response_list = []
            
            # Each main level object is a date which could contain multiple entries/games
            for date in board:
                if board[date] is not None and len(board[date]) > 0:
                    games = board[date].get('data')
                    for game in games:
                        score = games[game]

                        # This will get the home and away rank data as we need it.
                        home_team_rank = get_ranking_for_team(league, score.get('home_team_id'))
                        away_team_rank = get_ranking_for_team(league, score.get('away_team_id'))

                        # Format the date as we want it.
                        evt_date = datetime.datetime.strptime(score.get('event_date'), "%Y-%m-%d %H:%M")

                        pretty_score = {
                            'event_id': score.get('event_id'),
                            'event_date': evt_date,
                            'event_time': evt_date.strftime("%H:%M"),
                            'away_team_id': score.get('away_team_id'),
                            'away_nick_name': score.get('away_nick_name'),
                            'away_city': score.get('away_city'),
                            'away_rank': away_team_rank.get('rank'),
                            'away_rank_points': round(float(away_team_rank.get('adjusted_points')), 2),
                            'home_team_id': score.get('home_team_id'),
                            'home_nick_name': score.get('home_nick_name'),
                            'home_city': score.get('home_city'),
                            'home_rank': home_team_rank.get('rank'),
                            'home_rank_points': round(float(home_team_rank.get('adjusted_points')), 2)
                        }
                        # Add the serialized JSON object which lines up with our data model to the list for returning
                        response_list.append(ScrubbedData.parse_obj(pretty_score))
            return response_list
        # This is that instance of an error bit we said we wanted to return earlier
        else:
            return Response(content=board.text, media_type="application/json", status_code=board.status_code)
    except Exception as e:
        print(e)
        raise e


# This is really just aliasing our call for rankings
def get_rankings(league):
    return requests.get(
        f'https://delivery.chalk247.com/team_rankings/{league}.json?api_key=74db8efa2a6db279393b433d97c2bc843f8e32b0').json().get(
        'results').get('data')


# Sets global variable for RANKS and their age which allows us to expire them dynamically
def set_ranks(league):
    global RANKS_AGE, RANK_RESULTS
    RANK_RESULTS = get_rankings(league)
    RANKS_AGE = datetime.datetime.now()


# Gets ranks for a given team in a given league, assuming the Third Party allows for other leagues.
# On first run/if the ranks are expired will update them this prevents calling each time we need to check a teams rank
def get_ranking_for_team(league, team_id):
    try:
        # If we have never set Ranks, do so now
        global RANK_RESULTS, RANKS_AGE
        if RANK_RESULTS is None:
            set_ranks(league)

        # This would normally be an environment variable or some other configurable parameter to allow for invalidating
        # if the ranks are older than our specified time out, get new ones.
        if RANK_RESULTS is not None and RANKS_AGE is not None:
            ranks_expired = (RANKS_AGE + datetime.timedelta(minutes=5)) < datetime.datetime.now()
            if ranks_expired:
                set_ranks(league)

        for result in RANK_RESULTS:
            if type(result) is dict and result.get('team_id') == team_id:
                return result
    except Exception as e:
        print(e)
        raise e


if __name__ == "__main__":
    RANK_RESULTS = None
    RANKS_AGE = None
    uvicorn.run(app, host="0.0.0.0", port=8000)
