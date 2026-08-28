"""Small, reusable client for The Movie Database API."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"


class TMDBError(RuntimeError):
    """Raised when TMDB cannot return usable movie data."""

    def __init__(self, message, status_code=503):
        super().__init__(message)
        self.status_code = status_code


def _request(endpoint, params=None):
    if not TMDB_API_KEY:
        raise TMDBError("TMDB_API_KEY is missing. Add it to your .env file.")
    try:
        response = requests.get(f"{TMDB_BASE_URL}{endpoint}", params={"api_key": TMDB_API_KEY, **(params or {})}, timeout=10)
        if response.status_code == 404:
            raise TMDBError("Movie not found.", status_code=404)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as error:
        raise TMDBError("TMDB is unavailable or the API key is invalid.") from error


def get_popular_movies(page=1): return _request("/movie/popular", {"language": "en-US", "page": page})
def get_trending_movies(): return _request("/trending/movie/day", {"language": "en-US"})
def search_movies(query, page=1): return _request("/search/movie", {"query": query, "language": "en-US", "page": page, "include_adult": False})
def get_movie_details(movie_id): return _request(f"/movie/{movie_id}", {"language": "en-US"})
def get_movie_credits(movie_id): return _request(f"/movie/{movie_id}/credits", {"language": "en-US"})
def get_similar_movies(movie_id): return _request(f"/movie/{movie_id}/similar", {"language": "en-US"})
def get_movie_genres(): return _request("/genre/movie/list", {"language": "en-US"})
def get_popular_shows(page=1): return _request("/tv/popular", {"language": "en-US", "page": page})
def search_tv_shows(query, page=1): return _request("/search/tv", {"query": query, "language": "en-US", "page": page, "include_adult": False})
def get_show_details(show_id): return _request(f"/tv/{show_id}", {"language": "en-US"})
def get_show_credits(show_id): return _request(f"/tv/{show_id}/credits", {"language": "en-US"})
def get_similar_shows(show_id): return _request(f"/tv/{show_id}/similar", {"language": "en-US"})
