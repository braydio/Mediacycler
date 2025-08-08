#!/usr/bin/env bash

JELLYFIN_URL="${JELLYFIN_URL:-http://192.168.1.198:8097}"
API_KEY="${JELLYFIN_API_KEY}"
MEDIA_ROOT="/mnt/netstorage/Media/TV"

# Check if API key is provided
if [[ -z "$API_KEY" ]]; then
  echo "ERROR: JELLYFIN_API_KEY environment variable is not set."
  echo "Please set it with: export JELLYFIN_API_KEY='your_jellyfin_api_key'"
  exit 1
fi

echo "Fetching library ID for 'TV'..."

LIBRARY_ID=$(curl -s -H "X-Emby-Token: $API_KEY" "$JELLYFIN_URL/Library/SelectableMediaFolders" | jq -r '.Items[] | select(.Name=="TV") | .Id')

if [[ -z "$LIBRARY_ID" ]]; then
  echo "ERROR: Could not find 'TV' library ID. Check Jellyfin."
  exit 1
fi

echo "TV Library ID: $LIBRARY_ID"
echo "Scanning folders under: $MEDIA_ROOT"
echo

# Loop over genre folders
find "$MEDIA_ROOT" -mindepth 2 -maxdepth 2 -type d | while read -r show_dir; do
  genre=$(basename "$(dirname "$show_dir")")
  title=$(basename "$show_dir")

  echo "--------------------------------------------"
  echo "Show: $title"
  echo "Genre (from folder): $genre"

  # Query Jellyfin for the item
  query_url="$JELLYFIN_URL/Items?IncludeItemTypes=Series&Recursive=true&Fields=Genres&ParentId=$LIBRARY_ID&SearchTerm=$(echo "$title" | jq -sRr @uri)"
  item_json=$(curl -s -H "X-Emby-Token: $API_KEY" "$query_url")
  item_id=$(echo "$item_json" | jq -r '.Items[0].Id')

  if [[ -n "$item_id" && "$item_id" != "null" ]]; then
    echo "Found in Jellyfin (Item ID: $item_id)"

    echo "Tagging with genre: $genre"
    curl -s -X POST "$JELLYFIN_URL/Items/$item_id" \
      -H "Content-Type: application/json" \
      -H "X-Emby-Token: $API_KEY" \
      -d "{\"Genres\": [\"$genre\"]}"

    collection_name="${genre} Documentaries"
    echo "Handling collection: $collection_name"

    # Check if collection exists
    collection_id=$(curl -s -H "X-Emby-Token: $API_KEY" "$JELLYFIN_URL/Collections?SearchTerm=$(echo "$collection_name" | jq -sRr @uri)" | jq -r '.Items[0].Id')

    if [[ -z "$collection_id" || "$collection_id" == "null" ]]; then
      echo "Creating new collection: $collection_name"
      curl -s -X POST "$JELLYFIN_URL/Collections?Name=$(echo "$collection_name" | jq -sRr @uri)" \
        -H "Content-Type: application/json" \
        -H "X-Emby-Token: $API_KEY" \
        -d "[\"$item_id\"]" >/dev/null
    else
      echo "Adding to existing collection (ID: $collection_id)"
      curl -s -X POST "$JELLYFIN_URL/Collections/$collection_id/Items?Ids=$item_id" \
        -H "X-Emby-Token: $API_KEY" >/dev/null
    fi
  else
    echo " WARNING: '$title' not found in Jellyfin library. Skipping."
  fi
done

echo
echo "Script complete."
