"""Combines Wikipedia's scraped data with TMDB's movie metadata."""
from functools import lru_cache
import tmdb


@lru_cache(maxsize=128)
def match_title_to_tmdb(title):
    results = tmdb.search_movies(title).get("results", [])
    return results[0] if results else None


def enrich_scraped_movies(scraped_movies):
    enriched, had_tmdb_error = [], False
    for scraped in scraped_movies:
        movie = dict(scraped)
        try: match = match_title_to_tmdb(scraped["title"])
        except tmdb.TMDBError: had_tmdb_error, match = True, None
        if match: movie.update({"tmdb_id": match.get("id"), "rating": match.get("vote_average"), "poster_path": match.get("poster_path"), "overview": match.get("overview"), "release_date": match.get("release_date")})
        enriched.append(movie)
    return enriched, "Some TMDB details could not be loaded." if had_tmdb_error else None
