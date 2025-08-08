import requests

MDBLIST_BASE_URL = "https://mdblist.com/api"
USER = "hd-movie-lists"


def get_all_lists():
    res = requests.get(f"{MDBLIST_BASE_URL}/user/{USER}")
    res.raise_for_status()
    return res.json()["lists"]


def get_items_from_list(slug):
    res = requests.get(f"{MDBLIST_BASE_URL}/?list={USER}/{slug}")
    res.raise_for_status()
    return res.json()["items"]


def get_all_items_from_all_lists():
    lists = get_all_lists()
    for lst in lists:
        slug = lst["slug"]
        title = lst["title"]
        try:
            items = get_items_from_list(slug)
            for item in items:
                yield {
                    "id": item.get("imdb_id") or item.get("tvdb_id"),
                    "type": "movie" if item.get("type") == "movie" else "show",
                    "title": item.get("title"),
                    "slug": slug,
                    "list_title": title,
                }
        except Exception as e:
            print(f"⚠️ Failed to fetch list '{title}': {e}")
