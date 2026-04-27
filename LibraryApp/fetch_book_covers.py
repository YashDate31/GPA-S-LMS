import sqlite3
import requests
import urllib.parse
import time
import sys
import os
import re


def _clean_text(value):
    return re.sub(r'[^a-z0-9]+', ' ', (value or '').lower()).strip()


def _catalogue_search_text(value):
    text = _clean_text(value)
    replacements = {
        "embdedded": "embedded",
        "microproessors": "microprocessors",
        "mrutyunjay": "mrityunjay",
        "shiwaji": "shivaji",
        "yashwant": "yashavant",
        "acyut": "achyut",
        "networking": "networking",
        "engg": "engineering",
    }
    words = [replacements.get(word, word) for word in text.split()]
    return " ".join(words)


def _safe_console(value):
    return str(value or "").encode("ascii", errors="replace").decode("ascii")


def _looks_like_isbn(value):
    digits = re.sub(r'[^0-9Xx]', '', value or '')
    return len(digits) in (10, 13)


def _candidate_score(volume_info, title, author, isbn):
    expected_title = _catalogue_search_text(title)
    expected_author = _catalogue_search_text(author)
    expected_isbn = re.sub(r'[^0-9Xx]', '', isbn or '').upper()

    score = 0
    reasons = []
    has_title_match = False
    has_author_match = False

    identifiers = volume_info.get("industryIdentifiers", []) or []
    candidate_isbns = {
        re.sub(r'[^0-9Xx]', '', ident.get("identifier", "")).upper()
        for ident in identifiers
        if ident.get("identifier")
    }
    if expected_isbn and expected_isbn in candidate_isbns:
        score += 100
        reasons.append("isbn")

    candidate_title = _clean_text(volume_info.get("title", ""))
    if expected_title and candidate_title:
        if candidate_title == expected_title:
            score += 45
            reasons.append("exact_title")
            has_title_match = True
        elif expected_title in candidate_title or candidate_title in expected_title:
            score += 30
            reasons.append("partial_title")
            has_title_match = True
        else:
            expected_words = set(expected_title.split())
            candidate_words = set(candidate_title.split())
            overlap = len(expected_words & candidate_words)
            if expected_words:
                ratio = overlap / len(expected_words)
                if ratio >= 0.6:
                    score += int(25 * ratio)
                    reasons.append("title_words")
                    has_title_match = True

    candidate_authors = _clean_text(" ".join(volume_info.get("authors", []) or []))
    if expected_author and candidate_authors:
        if expected_author in candidate_authors or candidate_authors in expected_author:
            score += 35
            reasons.append("author")
            has_author_match = True
        else:
            expected_words = set(expected_author.split())
            candidate_words = set(candidate_authors.split())
            if expected_words and len(expected_words & candidate_words) / len(expected_words) >= 0.5:
                score += 20
                reasons.append("author_words")
                has_author_match = True

    # If the catalogue has both title and author, require both to align.
    # This avoids accepting wrong books that only share a subject or only share an author.
    if expected_title and expected_author and (not has_title_match or not has_author_match):
        score = min(score, 34)

    return score, ",".join(reasons) or "weak"


def _build_queries(title, author, isbn):
    if _looks_like_isbn(isbn):
        return [f"isbn:{isbn.strip()}"]

    clean_title = _catalogue_search_text(title)
    clean_author = _catalogue_search_text(author)
    queries = []

    if clean_title and clean_author:
        queries.append(f"intitle:{clean_title} inauthor:{clean_author}")
        queries.append(f"{clean_title} {clean_author}")
    if clean_title:
        queries.append(clean_title)

    # A small set of catalogue-specific fallbacks for common spelling/import
    # variants that Google Books indexes under a different transliteration.
    if "mrityunjay" in clean_title:
        queries.append("mrityunjaya shivaji sawant")
    if "data communication" in clean_title and "networking" in clean_title:
        queries.append("data communications and networking achyut godbole")

    seen = set()
    deduped = []
    for query in queries:
        query = query.strip()
        if query and query not in seen:
            seen.add(query)
            deduped.append(query)
    return deduped

def get_cover_url_from_google(title, author, isbn, api_key):
    """Fetch the best matching Google Books cover URL and basic match metadata."""
    queries = _build_queries(title, author, isbn)
    if not queries:
        return None, None

    try:
        best = None
        for query in queries:
            params = {"q": query, "maxResults": 10, "printType": "books"}
            if api_key:
                params["key"] = api_key

            response = requests.get("https://www.googleapis.com/books/v1/volumes", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            for item in data.get("items", []) or []:
                volume_info = item.get("volumeInfo", {})
                score, reasons = _candidate_score(volume_info, title, author, isbn)
                image_links = volume_info.get("imageLinks", {})
                cover_url = image_links.get("thumbnail") or image_links.get("smallThumbnail")
                if cover_url and (best is None or score > best["score"]):
                    best = {
                        "score": score,
                        "reasons": reasons,
                        "volume_info": volume_info,
                        "cover_url": cover_url,
                        "query": query,
                    }

        if not best:
            return None, None

        if best["score"] < 35:
            return None, {
                "score": best["score"],
                "reasons": best["reasons"],
                "matched_title": best["volume_info"].get("title", ""),
                "matched_authors": ", ".join(best["volume_info"].get("authors", []) or []),
                "query": best["query"],
                "rejected": True,
            }

        volume_info = best["volume_info"]
        image_links = volume_info.get("imageLinks", {})
        cover_url = image_links.get("thumbnail") or image_links.get("smallThumbnail")

        if cover_url:
            # Upgrade the resolution! By default Google Books sets zoom=1.
            # zoom=5 usually provides a very high-quality cover.
            # Also ensure we use https.
            cover_url = cover_url.replace("zoom=1", "zoom=5").replace("http:", "https:")
            return cover_url, {
                "score": best["score"],
                "reasons": best["reasons"],
                "matched_title": volume_info.get("title", ""),
                "matched_authors": ", ".join(volume_info.get("authors", []) or []),
                "query": best["query"],
                "rejected": False,
            }
    except Exception as e:
        print(f"Error fetching {title}: {e}")
        
    return None, None

def main():
    print("=== Google Books Cover Fetcher ===")
    api_key = os.getenv("GOOGLE_BOOKS_API_KEY", "").strip()
    if not api_key and sys.stdin.isatty():
        try:
            api_key = input("Paste your Google Books API Key, or press Enter to use public API: ").strip()
        except EOFError:
            api_key = ""

    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "library.db")
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # 1. Add the column if it doesn't exist yet
        try:
            cursor.execute("ALTER TABLE books ADD COLUMN cover_url TEXT;")
            print("Added 'cover_url' column to the books table.")
        except sqlite3.OperationalError:
            # Column likely already exists
            print("'cover_url' column already exists.")
            
        # 2. Get all books that don't have a cover yet
        cursor.execute("SELECT id, title, author, isbn FROM books WHERE cover_url IS NULL OR cover_url = '' OR cover_url = 'NOT_FOUND'")
        books = cursor.fetchall()
        
        total_books = len(books)
        print(f"Found {total_books} books missing covers. Starting fetch...\n")
        
        success_count = 0
        not_found_count = 0
        
        for i, (book_id, title, author, isbn) in enumerate(books, 1):
            sys.stdout.write(f"\rProcessing {i}/{total_books}: {title[:30]:<30}...")
            sys.stdout.flush()
            
            cover_url, match = get_cover_url_from_google(title, author, isbn, api_key)
            
            if cover_url:
                cursor.execute("UPDATE books SET cover_url = ? WHERE id = ?", (cover_url, book_id))
                conn.commit()
                success_count += 1
                if match:
                    print(f"\n  OK: matched '{_safe_console(match['matched_title'])}' by {_safe_console(match['matched_authors'])} "
                          f"(score={match['score']}, {match['reasons']}, query={_safe_console(match.get('query'))})")
            else:
                # Store a placeholder so we don't keep searching for it later
                cursor.execute("UPDATE books SET cover_url = ? WHERE id = ?", ("NOT_FOUND", book_id))
                conn.commit()
                not_found_count += 1
                if match:
                    print(f"\n  Rejected weak match '{_safe_console(match['matched_title'])}' by {_safe_console(match['matched_authors'])} "
                          f"(score={match['score']}, {match['reasons']}, query={_safe_console(match.get('query'))})")
                
            # Sleep slightly to be polite to the API, though limits are high
            time.sleep(0.1)

        print("\n\n=== Finished! ===")
        print(f"Successfully found covers: {success_count}")
        print(f"Covers not found: {not_found_count}")

if __name__ == "__main__":
    main()
