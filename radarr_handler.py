import os
import requests

RADARR_API_KEY = os.getenv("RADARR_API_KEY")
RADARR_URL = os.getenv("RADARR_URL", "http://localhost:7878")
MOVIE_ROOT_FOLDER = "/mnt/netstorage/Media/RotatingMovies"
QUALITY_PROFILE_ID = int(os.getenv("RADARR_QUALITY_PROFILE_ID", "1"))  # default profile

HEADERS = {"X-Api-Key": RADARR_API_KEY}


def lookup_movie(imdb_id):
    """Look up movie details by IMDb ID."""
    res = requests.get(
        f"{RADARR_URL}/api/v3/movie/lookup/imdb?imdbId={imdb_id}", headers=HEADERS
    )
    res.raise_for_status()
    return res.json()


def add_movie_to_radarr(movie_data):
    """Add a movie to Radarr and trigger a search."""
    payload = {
        "title": movie_data["title"],
        "qualityProfileId": QUALITY_PROFILE_ID,
        "titleSlug": movie_data["titleSlug"],
        "images": movie_data.get("images", []),
        "tmdbId": movie_data["tmdbId"],
        "year": movie_data.get("year"),
        "monitored": True,
        "rootFolderPath": MOVIE_ROOT_FOLDER,
        "addOptions": {"searchForMovie": True},
    }
    res = requests.post(f"{RADARR_URL}/api/v3/movie", headers=HEADERS, json=payload)
    if res.status_code == 201:
        print(f"✅ Added movie: {movie_data['title']} ({movie_data['year']})")
        return True
    elif res.status_code == 400 and "already exists" in res.text.lower():
        print(f"⚠️ Movie already exists in Radarr: {movie_data['title']}")
        return False
    else:
        print(f"❌ Failed to add movie: {res.status_code} - {res.text}")
        return False


def delete_movie_by_imdb(imdb_id, delete_files=True):
    """Remove a movie by IMDb ID."""
    res = requests.get(f"{RADARR_URL}/api/v3/movie", headers=HEADERS)
    res.raise_for_status()
    movies = res.json()
    for movie in movies:
        if movie.get("imdbId") == imdb_id:
            movie_id = movie["id"]
            delete_payload = {"deleteFiles": delete_files, "addImportExclusion": True}
            del_res = requests.delete(
                f"{RADARR_URL}/api/v3/movie/{movie_id}",
                headers=HEADERS,
                json=delete_payload,
            )
            if del_res.status_code == 200:
                print(f"🗑️ Deleted movie: {movie['title']}")
                return True
    print(f"⚠️ No matching movie found to delete with IMDb ID {imdb_id}")
    return False
