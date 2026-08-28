from functools import lru_cache
from flask import Flask, render_template, request
import requests
import tmdb
from movie_service import enrich_scraped_movies
from scraper import scrape_movies, scrape_wikipedia_title

app = Flask(__name__)


def image_url(path, size="w500"):
    if not path:
        return "https://placehold.co/500x750/171925/e9ecff?text=MovieHub"
    return path if path.startswith(("http://", "https://")) else f"https://image.tmdb.org/t/p/{size}{path}"


@app.template_filter("year")
def year_filter(movie):
    return (movie.get("release_date") or "")[:4] or "—"


@app.context_processor
def utility_context():
    return {"image_url": image_url, "current_year": 2026}


@lru_cache(maxsize=1)
def genre_map():
    """Cache genre names so list cards can show a readable TMDB genre."""
    return {genre["id"]: genre["name"] for genre in tmdb.get_movie_genres().get("genres", [])}


def add_genre_names(movies):
    try:
        genres = genre_map()
    except tmdb.TMDBError:
        genres = {}
    for movie in movies:
        if "genres" in movie:
            movie["genre_names"] = [genre.get("name") for genre in movie.get("genres", [])]
        else:
            movie["genre_names"] = [genres[genre_id] for genre_id in movie.get("genre_ids", []) if genre_id in genres]
    return movies


def normalise_shows(shows):
    for show in shows:
        show["title"] = show.get("name", "Untitled show")
        show["release_date"] = show.get("first_air_date", "")
        show["media_type"] = "tv"
    return shows


def tmdb_results(call, default=None):
    try:
        return call(), None
    except tmdb.TMDBError as error:
        app.logger.warning("TMDB request failed: %s", error)
        return default if default is not None else {}, error


@app.get("/")
def home():
    popular_data, popular_error = tmdb_results(tmdb.get_popular_movies, {"results": []})
    trending_data, trending_error = tmdb_results(tmdb.get_trending_movies, {"results": []})
    popular = add_genre_names(popular_data.get("results", [])[:6])
    trending = add_genre_names(trending_data.get("results", [])[:6])
    return render_template("index.html", popular_movies=popular, trending_movies=trending, hero_movie=(trending or popular or [None])[0], error=popular_error or trending_error)


@app.get("/movies")
def movies():
    data, error = tmdb_results(tmdb.get_popular_movies, {"results": []})
    return render_template("search.html", movies=add_genre_names(data.get("results", [])), query="", error=error, page_title="Explore movies")


@app.get("/shows")
def shows():
    data, error = tmdb_results(tmdb.get_popular_shows, {"results": []})
    return render_template("search.html", movies=normalise_shows(data.get("results", [])), query="", error=error, page_title="Popular shows")


@app.get("/search")
def search():
    query = request.args.get("q", "", type=str).strip()
    if not query:
        return render_template("search.html", movies=[], query="", error=None, page_title="Search movies", message="Enter a movie title, genre, or keyword to start searching.")
    if len(query) > 100:
        return render_template("search.html", movies=[], query=query[:100], error="Please keep your search under 100 characters.", page_title="Search movies"), 400
    movie_data, movie_error = tmdb_results(lambda: tmdb.search_movies(query), {"results": []})
    show_data, show_error = tmdb_results(lambda: tmdb.search_tv_shows(query), {"results": []})
    results = add_genre_names(movie_data.get("results", [])) + normalise_shows(show_data.get("results", []))
    fallback = None
    if not results and not (movie_error or show_error):
        try:
            fallback = scrape_wikipedia_title(query)
        except requests.RequestException:
            fallback = None
    if fallback:
        fallback.update({
            "media_type": "wikipedia",
            "poster_path": fallback.get("poster_url"),
            "vote_average": None,
            "genre_names": ["Wikipedia"],
            "release_date": "",
        })
    return render_template("search.html", movies=results, query=query, error=movie_error or show_error, page_title="Search movies and shows", wikipedia_result=fallback)


@app.get("/movie/<int:movie_id>")
def movie_details(movie_id):
    details, error = tmdb_results(lambda: tmdb.get_movie_details(movie_id))
    if error:
        message = "This movie could not be found." if error.status_code == 404 else "Movie data is temporarily unavailable. Please try again shortly."
        return render_template("movie.html", movie=None, credits={}, similar_movies=[], error=message), error.status_code
    credits, credits_error = tmdb_results(lambda: tmdb.get_movie_credits(movie_id), {"cast": [], "crew": []})
    similar_data, similar_error = tmdb_results(lambda: tmdb.get_similar_movies(movie_id), {"results": []})
    director = next((person.get("name") for person in credits.get("crew", []) if person.get("job") == "Director"), None)
    return render_template("movie.html", movie=details, credits=credits, director=director, similar_movies=add_genre_names(similar_data.get("results", [])[:6]), error=credits_error or similar_error)


@app.get("/show/<int:show_id>")
def show_details(show_id):
    details, error = tmdb_results(lambda: tmdb.get_show_details(show_id))
    if error:
        return render_template("movie.html", movie=None, credits={}, similar_movies=[], error="This show could not be found."), error.status_code
    normalise_shows([details])
    credits, credits_error = tmdb_results(lambda: tmdb.get_show_credits(show_id), {"cast": [], "crew": []})
    similar_data, similar_error = tmdb_results(lambda: tmdb.get_similar_shows(show_id), {"results": []})
    director = next((person.get("name") for person in credits.get("crew", []) if person.get("job") in {"Director", "Executive Producer"}), None)
    return render_template("movie.html", movie=details, credits=credits, director=director, similar_movies=normalise_shows(similar_data.get("results", [])[:6]), error=credits_error or similar_error)


@app.get("/scraped")
def scraped_movies():
    try:
        scraped = scrape_movies()
        movies, enrichment_error = enrich_scraped_movies(scraped[:18])
        return render_template("scraped.html", movies=movies, error=enrichment_error)
    except requests.RequestException:
        return render_template("scraped.html", movies=[], error="Wikipedia could not be reached right now. Please try again later."), 503


@app.errorhandler(404)
def page_not_found(_error):
    return render_template("error.html", title="Page not found", message="The page you requested does not exist."), 404


if __name__ == "__main__":
    app.run(debug=True)
