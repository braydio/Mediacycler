#!/usr/bin/env bash

JELLYFIN_URL="${JELLYFIN_URL:-http://192.168.1.198:8097}"
API_KEY="${JELLYFIN_API_KEY}"
# Allow overriding via env var; default to historical path
MEDIA_ROOT="${MEDIA_ROOT:-/mnt/netstorage/Media/TV}"
# Allow overriding the library name; many installs use "TV Shows"
LIBRARY_NAME="${LIBRARY_NAME:-TV}"
# Optional default genre to apply when none is derivable from path
DEFAULT_GENRE="${DEFAULT_GENRE:-}"

# Check if API key is provided
if [[ -z "$API_KEY" ]]; then
  echo "ERROR: JELLYFIN_API_KEY environment variable is not set."
  echo "Please set it with: export JELLYFIN_API_KEY='your_jellyfin_api_key'"
  exit 1
fi

echo "Discovering TV library (target name: '$LIBRARY_NAME')..."

# Try multiple endpoints and normalize to Name|Id pairs
libraries_json=$(curl -s -H "X-Emby-Token: $API_KEY" "$JELLYFIN_URL/Library/SelectableMediaFolders")
normalized_list=$(echo "$libraries_json" | jq -r 'if type=="object" and .Items then .Items[] | {Name: .Name, Id: (.Id // .ItemId)} elif type=="array" then .[] | {Name: .Name, Id: (.Id // .ItemId)} else empty end | select(.Name!=null and .Id!=null) | "\(.Name)|\(.Id)"' 2>/dev/null)

# Fallback to VirtualFolders if empty
if [[ -z "$normalized_list" ]]; then
  libraries_json=$(curl -s -H "X-Emby-Token: $API_KEY" "$JELLYFIN_URL/Library/VirtualFolders")
  normalized_list=$(echo "$libraries_json" | jq -r 'if type=="object" and .Items then .Items[] | {Name: .Name, Id: (.Id // .ItemId)} elif type=="array" then .[] | {Name: .Name, Id: (.Id // .ItemId)} else empty end | select(.Name!=null and .Id!=null) | "\(.Name)|\(.Id)"' 2>/dev/null)
fi

# Exact match or common variants
LIBRARY_ID=""
pick_from_list() {
  local want="$1"
  echo "$normalized_list" | awk -F'|' -v w="$want" 'tolower($1)==tolower(w){print $2; exit}'
}

for name in "$LIBRARY_NAME" "TV Shows" "Television" "TV"; do
  id=$(pick_from_list "$name")
  if [[ -n "$id" ]]; then
    LIBRARY_ID="$id"
    LIBRARY_NAME="$name"
    break
  fi
done

# Fuzzy match on "tv" if still not found
if [[ -z "$LIBRARY_ID" ]]; then
  id=$(echo "$normalized_list" | awk -F'|' 'tolower($1) ~ /(^|[^a-z])tv([^a-z]|$)/ {print $2; exit}')
  name=$(echo "$normalized_list" | awk -F'|' 'tolower($1) ~ /(^|[^a-z])tv([^a-z]|$)/ {print $1; exit}')
  if [[ -n "$id" ]]; then
    LIBRARY_ID="$id"; LIBRARY_NAME="$name"
  fi
fi

if [[ -z "$LIBRARY_ID" ]]; then
  echo "ERROR: Cannot find TV library. None matched '$LIBRARY_NAME'."
  echo "Available libraries:"
  if [[ -n "$normalized_list" ]]; then
    echo "$normalized_list" | awk -F'|' '{printf("- %s (Id: %s)\n", $1, $2)}'
  else
    # Show a snippet of the raw JSON to aid debugging
    echo "(No normalized libraries found. Raw response:)"
    echo "$libraries_json" | head -c 400 | sed 's/\n/ /g'
  fi
  echo "Hint: set LIBRARY_NAME to your Jellyfin TV library name, e.g.:"
  echo "  export LIBRARY_NAME=\"TV Shows\""
  exit 1
fi

echo "Using library '$LIBRARY_NAME' (ID: $LIBRARY_ID)"
echo "Scanning folders under: $MEDIA_ROOT"
echo

# Maintain a set of processed show titles to avoid duplicates
declare -A processed_titles

# Iterate 1-2 levels deep to support both layouts:
# 1) Genre/Show
# 2) Show/SeasonX
while IFS= read -r -d '' path; do
  # Determine relative depth
  rel="${path#${MEDIA_ROOT}/}"
  base="$(basename "$path")"
  parent="$(basename "$(dirname "$path")")"
  grandparent="$(basename "$(dirname "$(dirname "$path")")")"

  title=""
  genre=""

  # Heuristics:
  # - If basename looks like a season folder, use parent as title
  if [[ "$base" =~ ^(?i:season[[:space:]]*[0-9]+)$ || "$base" =~ ^(?i:s[0-9]{1,2})$ || "$base" =~ ^(?i:specials?)$ ]]; then
    title="$parent"
    # If three levels deep, treat grandparent as genre (Genre/Show/Season)
    if [[ "$grandparent" != "/" && "$grandparent" != "." && "$grandparent" != "$parent" ]]; then
      genre="$grandparent"
    fi
  else
    # Depth-based handling
    if [[ "$rel" == *"/"* ]]; then
      # Two levels deep: assume Genre/Show
      title="$base"
      genre="$parent"
    else
      # One level deep: assume Show
      title="$base"
    fi
  fi

  # Skip if we couldn't determine a title
  if [[ -z "$title" ]]; then
    continue
  fi

  # Avoid processing the same show multiple times
  if [[ -n "${processed_titles[$title]}" ]]; then
    continue
  fi
  processed_titles[$title]=1

  # If no genre derived, use DEFAULT_GENRE if provided, otherwise skip tagging
  if [[ -z "$genre" ]]; then
    if [[ -n "$DEFAULT_GENRE" ]]; then
      genre="$DEFAULT_GENRE"
    else
      echo "--------------------------------------------"
      echo "Show: $title"
      echo "No genre derived from path '$path'. Set DEFAULT_GENRE or use Genre/Show layout. Skipping genre tagging."
      continue
    fi
  fi

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

    collection_name="$genre"
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
done < <(find "$MEDIA_ROOT" -mindepth 1 -maxdepth 2 -type d -print0)

echo
echo "Script complete."
