import re, os

sp_path = "C:/Users/Yash/OneDrive/Desktop/GPA-S-LMS/LibraryApp/Web-Extension/student_portal.py"
with open(sp_path, "r", encoding="utf-8") as f:
    sp_data = f.read()

new_table = """    # Wishlist
    create_table_safe(cursor, 'book_wishlist', '''
        CREATE TABLE IF NOT EXISTS book_wishlist (
            id SERIAL PRIMARY KEY,
            book_id TEXT NOT NULL,
            enrollment_no TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(book_id, enrollment_no)
        )
    ''', '''
        CREATE TABLE IF NOT EXISTS book_wishlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id TEXT NOT NULL,
            enrollment_no TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(book_id, enrollment_no)
        )
    ''')

    # Ratings"""

if "book_wishlist" not in sp_data:
    sp_data = sp_data.replace("    # Ratings", new_table)

wishlist_sql = """            waitlist_entry = portal_cursor.fetchone()
            book_data['on_waitlist'] = waitlist_entry is not None

            # Wishlist check
            portal_cursor.execute(
                "SELECT id FROM book_wishlist WHERE enrollment_no = ? AND book_id = ?",
                (session['student_id'], str(book_id))
            )
            book_data['isWishlisted'] = portal_cursor.fetchone() is not None"""

if "SELECT id FROM book_wishlist WHERE enrollment_no = ? AND book_id = ?" not in sp_data:
    sp_data = sp_data.replace(
        "waitlist_entry = portal_cursor.fetchone()\n            book_data['on_waitlist'] = waitlist_entry is not None",
        wishlist_sql
    )

routes_code = """
@app.route('/api/books/<book_id>/rate', methods=['POST'])
def rate_book(book_id):
    if 'student_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        enrollment = session['student_id']
        rating = int(request.json.get('rating', 0))
        if rating < 1 or rating > 5:
            return jsonify({'error': 'Invalid rating'}), 400
        
        conn = get_portal_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM book_ratings WHERE book_id = ? AND enrollment_no = ?", (str(book_id), enrollment))
        if cursor.fetchone():
            cursor.execute("UPDATE book_ratings SET rating = ? WHERE book_id = ? AND enrollment_no = ?", (rating, str(book_id), enrollment))
        else:
            cursor.execute("INSERT INTO book_ratings (book_id, enrollment_no, rating) VALUES (?, ?, ?)", (str(book_id), enrollment, rating))
        
        conn.commit()
        
        cursor.execute("SELECT AVG(rating), COUNT(rating) FROM book_ratings WHERE book_id = ?", (str(book_id),))
        stats = cursor.fetchone()
        conn.close()
        
        return jsonify({'status': 'success', 'new_avg': round(stats[0], 1) if stats[0] else 0, 'new_count': stats[1] if stats[1] else 0})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/books/<book_id>/wishlist', methods=['POST'])
def toggle_wishlist_api(book_id):
    if 'student_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        enrollment = session['student_id']
        conn = get_portal_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM book_wishlist WHERE book_id = ? AND enrollment_no = ?", (str(book_id), enrollment))
        if cursor.fetchone():
            cursor.execute("DELETE FROM book_wishlist WHERE book_id = ? AND enrollment_no = ?", (str(book_id), enrollment))
            status = 'removed'
        else:
            cursor.execute("INSERT INTO book_wishlist (book_id, enrollment_no) VALUES (?, ?)", (str(book_id), enrollment))
            status = 'added'
            
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'action': status})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
"""

if "def rate_book" not in sp_data:
    sp_data = sp_data.replace("@app.route('/api/books/<book_id>/notify', methods=['POST'])", routes_code + "\n@app.route('/api/books/<book_id>/notify', methods=['POST'])")

if "FROM book_waitlist" in sp_data and "notified = 0" in sp_data:
    sp_data = sp_data.replace(
        "SELECT COUNT(*) as c FROM book_waitlist WHERE enrollment_no = ? AND notified = 0",
        "SELECT COUNT(*) as c FROM book_wishlist WHERE enrollment_no = ?"
    )

with open(sp_path, "w", encoding="utf-8") as f:
    f.write(sp_data)


jsx_path = "C:/Users/Yash/OneDrive/Desktop/GPA-S-LMS/LibraryApp/Web-Extension/frontend/src/components/BookDetailModal.jsx"
with open(jsx_path, "r", encoding="utf-8") as f:
    jsx_data = f.read()

fetch_patch = """        setUserRating(data.user_rating || 0);
        setIsWishlisted(data.isWishlisted || false);
"""
if "setIsWishlisted(data.isWishlisted" not in jsx_data:
    jsx_data = jsx_data.replace("        setUserRating(data.user_rating || 0);\n", fetch_patch)

if "setIsWishlisted(false); // Reset/Mock" in jsx_data:
    jsx_data = jsx_data.replace("setIsWishlisted(false); // Reset/Mock", "// Reset logic handled in fetchBookDetails")

toggle_patch = """  const toggleWishlist = async () => {
    if (!book) return;
    const oldWish = isWishlisted;
    setIsWishlisted(!isWishlisted); // Optimistic UI
    
    try {
      const { data } = await axios.post(`/api/books/${book.book_id}/wishlist`);
      if (data.action === 'added') {
        addToast('Added to wishlist', 'success');
        setIsWishlisted(true);
      } else {
        addToast('Removed from wishlist', 'info');
        setIsWishlisted(false);
      }
    } catch(err) {
      setIsWishlisted(oldWish); // revert on auth/api error
      addToast('Failed to update wishlist', 'error');
    }
  };"""

if "const { data } = await axios.post(`/api/books/${book.book_id}/wishlist`);" not in jsx_data:
    import re
    jsx_data = re.sub(
        r'const toggleWishlist = \(\) => \{\s*setIsWishlisted\(\!isWishlisted\);\s*if \(\!isWishlisted\) \{\s*addToast\(\'Added to wishlist\', \'success\'\);\s*\} else \{\s*addToast\(\'Removed from wishlist\', \'info\'\);\s*\}\s*// Future: API call to sync wishlist\s*\};',
        toggle_patch,
        jsx_data
    )

with open(jsx_path, "w", encoding="utf-8") as f:
    f.write(jsx_data)

print("All patches applied!")
