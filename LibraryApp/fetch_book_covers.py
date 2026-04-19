import sqlite3
import requests
import urllib.parse
import time
import sys

def get_cover_url_from_google(title, author, isbn, api_key):
    """Fetches the highest-resolution cover URL from Google Books API."""
    query = ""
    # Use ISBN if available because it's the most accurate
    if isbn and isbn.strip():
        query += f"isbn:{isbn.strip()}"
    else:
        # Fallback to Title and Author
        if title:
            query += f"intitle:{title.strip()} "
        if author:
            query += f"inauthor:{author.strip()}"
            
    query = query.strip()
    if not query:
        return None

    # Encode the search query
    encoded_query = urllib.parse.quote(query)
    url = f"https://www.googleapis.com/books/v1/volumes?q={encoded_query}&key={api_key}"

    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        if "items" in data and len(data["items"]) > 0:
            volume_info = data["items"][0].get("volumeInfo", {})
            image_links = volume_info.get("imageLinks", {})
            
            # Get the thumbnail URL
            cover_url = image_links.get("thumbnail") or image_links.get("smallThumbnail")
            
            if cover_url:
                # Upgrade the resolution! By default Google Books sets zoom=1.
                # zoom=5 usually provides a very high-quality cover.
                # Also ensure we use https.
                cover_url = cover_url.replace("zoom=1", "zoom=5").replace("http:", "https:")
                return cover_url
    except Exception as e:
        print(f"Error fetching {query}: {e}")
        
    return None

def main():
    print("=== Google Books Cover Fetcher ===")
    api_key = input("Paste your Google Books API Key: ").strip()
    
    if not api_key:
        print("API Key is required. Exiting...")
        return
        
    db_path = "library.db"
    
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
        cursor.execute("SELECT id, title, author, isbn FROM books WHERE cover_url IS NULL OR cover_url = ''")
        books = cursor.fetchall()
        
        total_books = len(books)
        print(f"Found {total_books} books missing covers. Starting fetch...\n")
        
        success_count = 0
        not_found_count = 0
        
        for i, (book_id, title, author, isbn) in enumerate(books, 1):
            sys.stdout.write(f"\rProcessing {i}/{total_books}: {title[:30]:<30}...")
            sys.stdout.flush()
            
            cover_url = get_cover_url_from_google(title, author, isbn, api_key)
            
            if cover_url:
                cursor.execute("UPDATE books SET cover_url = ? WHERE id = ?", (cover_url, book_id))
                conn.commit()
                success_count += 1
            else:
                # Store a placeholder so we don't keep searching for it later
                cursor.execute("UPDATE books SET cover_url = ? WHERE id = ?", ("NOT_FOUND", book_id))
                conn.commit()
                not_found_count += 1
                
            # Sleep slightly to be polite to the API, though limits are high
            time.sleep(0.1)

        print("\n\n=== Finished! ===")
        print(f"Successfully found covers: {success_count}")
        print(f"Covers not found: {not_found_count}")

if __name__ == "__main__":
    main()
