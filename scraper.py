"""BeautifulSoup pipeline that extracts structured film data from Wikipedia."""
from urllib.parse import quote
import requests
from bs4 import BeautifulSoup

URL = "https://en.wikipedia.org/wiki/List_of_American_films_of_2026"
HEADERS = {"User-Agent": "MovieHubStudentProject/1.0 (educational project)"}


def fetch_page(url):
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()
    return response.text


def parse_page(html): return BeautifulSoup(html, "html.parser")
def _cell_text(cells, index): return cells[index].get_text(" ", strip=True) if index is not None and index < len(cells) else None


def _cell_link(cells, index):
    if index is None or index >= len(cells): return None
    link = cells[index].find("a", href=True)
    if not link: return None
    return f"https://en.wikipedia.org{link['href']}" if link["href"].startswith("/") else link["href"]


def extract_movies(soup):
    """Read Wikipedia film tables into structured dictionaries."""
    movies = []
    for table in soup.select("table.wikitable"):
        header_row = table.find("tr")
        headers = [header.get_text(" ", strip=True).lower() for header in header_row.find_all("th")] if header_row else []
        if "title" not in headers: continue
        columns = {name: position for position, name in enumerate(headers)}
        for row in table.find_all("tr")[1:]:
            cells = row.find_all(["th", "td"], recursive=False)
            title = _cell_text(cells, columns["title"])
            if title:
                movies.append({"title": title, "wikipedia_url": _cell_link(cells, columns["title"]), "director": _cell_text(cells, columns.get("director(s)")), "distributor": _cell_text(cells, columns.get("distributor")), "cast": _cell_text(cells, columns.get("cast"))})
    return movies


def scrape_movies(url=URL):
    """HTTP request → BeautifulSoup → structured Wikipedia movie data."""
    return extract_movies(parse_page(fetch_page(url)))


def scrape_wikipedia_title(title):
    """Scrape a single Wikipedia search result as a no-TMDB fallback."""
    direct_url = f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"
    page_soup = parse_page(fetch_page(direct_url))
    heading = page_soup.select_one("#firstHeading")
    is_article = heading and (not page_soup.title or "Special:Search" not in page_soup.title.get_text())
    if is_article:
        page_url = direct_url
        page_title = heading.get_text(" ", strip=True)
    else:
        search_html = fetch_page(f"https://en.wikipedia.org/w/index.php?search={quote(title)}")
        search_soup = parse_page(search_html)
        result = search_soup.select_one(".mw-search-result-heading a")
        if not result or not result.get("href"):
            return None
        page_url = f"https://en.wikipedia.org{result['href']}"
        page_soup = parse_page(fetch_page(page_url))
        page_title = result.get_text(" ", strip=True)
    overview = next((paragraph.get_text(" ", strip=True) for paragraph in page_soup.select("#mw-content-text > .mw-parser-output > p") if paragraph.get_text(" ", strip=True)), "")
    fields = {row.find("th").get_text(" ", strip=True).lower(): row.find("td").get_text(" ", strip=True) for row in page_soup.select("table.infobox tr") if row.find("th") and row.find("td")}
    poster = page_soup.select_one("table.infobox img")
    poster_url = poster.get("src") if poster else None
    if poster_url and poster_url.startswith("//"):
        poster_url = f"https:{poster_url}"
    return {"title": page_title, "wikipedia_url": page_url, "overview": overview, "director": fields.get("directed by"), "cast": fields.get("starring"), "poster_url": poster_url}
