#!/usr/bin/env python3
"""
Add Demo Data to Library Management System
Creates sample students, books, and transactions for testing
"""

import sys
import os
from datetime import datetime, timedelta
import random

# Add path for database import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import Database

def add_demo_students(db):
    """Add demo students to database"""
    print("Adding demo students...")
    
    demo_students = [
        ('24210270228', 'Dalvi Tanvi Tatyasaheb', 'dalvitanvi553@gmail.com', '7666910952', 'CO', '2nd Year'),
        ('24210270229', 'Daphal Srushti Suresh', 'srushtidaphal9@gmail.com', '9226558055', 'CO', '2nd Year'),
        ('24210270246', 'Khaire Payal Santosh', 'khairepayal144@gmail.com', '9834242704', 'CO', '2nd Year'),
        ('24210270269', 'Sarje Shravani Vijay', 'shravanisarje30@gmail.com', '7709847609', 'CO', '2nd Year'),
        ('24210270239', 'Hande Monika Vishwanath', 'handemonika846@gmail.com', '8830131372', 'CO', '2nd Year'),
        ('24210270236', 'Gawade Tejal Shantaram', 'kavitagawade392@gmail.com', '9834906748', 'CO', '2nd Year'),
        ('24210270240', 'Hande Shravani Sharad', 'shravanihande298@gmail.com', '9699093199', 'CO', '2nd Year'),
        ('24210270295', 'Salunke Srushti Sidram', 'srushtisalunke41@gmail.com', '8623865041', 'CO', '2nd Year'),
        ('24210270251', 'Kokate Vishakha Dipak', 'vishakhakokate2008@gmail.com', '8983273393', 'CO', '2nd Year'),
        ('24210270226', 'Chavan Aishwarya Asharam', 'aishwaryachavan@gmail.com', '7498999792', 'CO', '2nd Year'),
        ('24210270267', 'Rokade Sayali Nitin', 'rokadesayali07@gmail.com', '9309706667', 'CO', '2nd Year'),
        ('24210270221', 'Bagul Limesh Krushana', 'limesh0092@gmail.com', '9172860181', 'CO', '2nd Year'),
        ('24210270257', 'Mulani Joya Nasir', 'mulanijoya3@gmail.com', '9860625633', 'CO', '2nd Year'),
        ('24210270244', 'Kedar Diksha Rajendra', 'drkedar80558055@gmail.com', '7620104290', 'CO', '2nd Year'),
        ('242103000000', 'Gaikawad Vedant Sunil', 'poweroftiger74@gmail.com', '8262874603', 'CO', '2nd Year'),
        ('24210270261', 'Pawde Samruddhi Namdev', 'samruddhipawde1@gmail.com', '8552840411', 'CO', '2nd Year'),
        ('24210270273', 'Shinde Sanika Manikrao', 'Sanikashinde53281@gmail.com', '9511899741', 'CO', '2nd Year'),
        ('24210270283', 'Sandbhor Renuka Sunil', 'dhanashrisandbhor@gmail.com', '9579756859', 'CO', '2nd Year'),
        ('24210270293', 'Khonde Anjali Bhagwan', 'anjalikhonde666@gmail.com', '9325510383', 'CO', '2nd Year'),
        ('24210270266', 'Rathod Pallavi Ganpat', 'pallavirathod7284@gmail.com', '7620380043', 'CO', '2nd Year'),
        ('24210270255', 'Matole Snehal Limbraj', 'Snehalmatole4@gmail.com', '9325773953', 'CO', '2nd Year'),
        ('24210270277', 'Sumbre Aditya Sandeep', 'adityasumbre@gmail.com', '9175098718', 'CO', '2nd Year'),
        ('24210270264', 'Ramane Vaibhavi Santosh', 'vaibhaviramane4@gmail.com', '7821022150', 'CO', '2nd Year'),
        ('24210270256', 'Mohanalkar Varad Mahesh', 'mohanalkarvarad@gmail.com', '9028903952', 'CO', '2nd Year'),
        ('24210270242', 'Jadhav Ganesh Anant', 'ganeshanantjadhav4@gmail.com', '7975256898', 'CO', '2nd Year'),
        ('24210270223', 'Bhagwat Bhagyashree Vinayak', 'ashabhagwat33@gmail.com', '7875032748', 'CO', '2nd Year'),
        ('24210270225', 'Bhor Samiksha Sachin', 'bhorsamiksha3@gmail.com', '9834024673', 'CO', '2nd Year'),
        ('24210270271', 'Sawant Sakshi Ramchandra', 'sakshirsawant009@gmail.com', '9209874266', 'CO', '2nd Year'),
        ('24210270250', 'Khurpe Samruddhi Santosh', 'samuddhikhurpe2903@gmail.com', '7498869775', 'CO', '2nd Year'),
        ('24210270252', 'Kothari Sanskruti Mayur', 'sanskrutikothari1824@gmail.com', '7219045351', 'CO', '2nd Year'),
        ('24210270237', 'Ghodke Tejas Dipak', 'tejasghodke542@gmail.com', '9000000000', 'CO', '2nd Year'),
        ('24210270238', 'Gundal Yash Santosh', 'yashgundal884@gmail.com', '9021828958', 'CO', '2nd Year'),
        ('24210270230', 'Date Yash Vijay', 'yashdate31@gmail.com', '9527266485', 'CO', '2nd Year'),
        ('24210270281', 'Wagh Vedant Vikas', 'vedant2109wagh@gmail.com', '8208293814', 'CO', '2nd Year'),
        ('24210270227', 'Dadge Sham Mukund', 'Shamdadge058@gmail.com', '9529232912', 'CO', '2nd Year'),
        ('24210270241', 'Jadhav Dnyaneshwar Nagesh', 'dnyaneshwarjadhav0808@gmail.com', '9226357537', 'CO', '2nd Year'),
        ('24210270275', 'Naikade Siddharth Nilesh', 'siddharthnaikade2278@gmail.com', '9673901695', 'CO', '2nd Year'),
        ('24210270222', 'Balghare Apurva Rajendra', 'apurvabalghare25@gmail.com', '8767692987', 'CO', '2nd Year'),
        ('24210270265', 'Randhwan Aditi Amol', 'aditirandhwan7799@gmail.com', '9404527799', 'CO', '2nd Year'),
        ('24210270254', 'Magar Yash Ajay', 'yashajaymagar10@gmail.com', '9579559257', 'CO', '2nd Year'),
        ('24210270258', 'Nampalle Pravin Balaji', 'nampallepravin@gmail.com', '8788851424', 'CO', '2nd Year'),
        ('24210270278', 'Supe Prathmesh Pundlik', 'prathmeshsupe9@gmail.com', '8432290612', 'CO', '2nd Year'),
        ('24210270268', 'Rokade Sharvari Sachin', 'sharvari.ssr@gmail.com', '9511775458', 'CO', '2nd Year'),
        ('24210270224', 'Bharmal Tejas Santosh', 'tejasbharmal2@gmail.com', '8805560218', 'CO', '2nd Year'),
        ('24210270249', 'Khedkar Ishwari Sudhir', 'ishwarikhedkar979@gmail.com', '7276468413', 'CO', '2nd Year'),
        ('24210270274', 'Shitole Trupti Ganesh', 'shitoletrupti6@gmail.com', '9325557234', 'CO', '2nd Year'),
        ('24210270298', 'Tribhuwan Sahil Rajendra', 'tribhuwanasha@gmail.com', '9529657471', 'CO', '2nd Year'),
        ('24210170247', 'Kjandait Shruti Vinod', 'shrutikhandait07@gmail.com', '7387961207', 'CO', '2nd Year'),
        ('24210270272', 'Shinde Anushka Keshavrao', 'anushkakeshavraoshinde@gmail.com', '9172851290', 'CO', '2nd Year'),
        ('24210270243', 'Jaitalkar Ishwari Dattatraya', 'Jaitalkarishwari@gmail.com', '7559494668', 'CO', '2nd Year'),
        ('24210270294', 'Pawar Krushna Sopan', 'krushnapawar0018@gmail.com', '8446554912', 'CO', '2nd Year'),
        ('24210270276', 'Sonawane Purva Manojkumar', 'purva17sonawane@gmail.com', '7498193972', 'CO', '2nd Year'),
        ('24210270259', 'Nangare Samruddhi Dasharath', 'samnangare28@gmail.com', '8180064191', 'CO', '2nd Year'),
        ('24210270260', 'Nehere Gauri Arun', 'gaurinehere2007@gmail.com', '7972895541', 'CO', '2nd Year'),
        ('24210270232', 'Dhumal Alwin Kisan', 'alwindhumal1312@gmail.com', '8275315100', 'CO', '2nd Year'),
        ('24210270262', 'Phapale Omkar Malhari', 'omkarphaple640@gmail.com', '9699185024', 'CO', '2nd Year'),
        ('24210270253', 'Madane Dakkhan Shahaji', 'dakkhanmadane@gmail.com', '8468802805', 'CO', '2nd Year'),
        ('24210270263', 'Pohakar Aryan Ramesh', 'pohakar.aryan20@gmail.com', '9767308669', 'CO', '2nd Year'),
        ('24210270235', 'Gaikwad Sujal Siddharth', '071sujalgaikwad@gmail.com', '9529625074', 'CO', '2nd Year'),
        ('24210270231', 'Dhobale Aditya Sandip', 'dhobaleaditya2007@gmail.com', '9322444332', 'CO', '2nd Year'),
        ('24210270248', 'Khankar Pranjal Rajendra', 'pranjalk0198@gmail.com', '8421631908', 'CO', '2nd Year'),
        ('24210270270', 'Sathe Pratiksha Balaji', 'Pratikshasathe552@gmail.com', '7972734938', 'CO', '2nd Year'),
        ('24210270282', 'Yewale Tanishka Nandu', 'yewaletanishka80@gmail.com', '9322118365', 'CO', '2nd Year'),
        ('24210270279', 'Suryawanshi Manjusha Balaji', 'icchasuryawanshi@gmail.com', '9145413095', 'CO', '2nd Year'),
        ('24210270292', 'Bhidave Tanvi Bhanudas', 'tanvibhidawe@gmail.com', '9272025575', 'CO', '2nd Year'),
        ('24210270233', 'Doke Sujal Eknath', 'Sujaldoke3112@gmail.com', '9579851261', 'CO', '2nd Year'),
        ('24210270280', 'Thorat Onkar Dnyaneshwar', 'odt0608@gmail.com', '9373010854', 'CO', '2nd Year'),
    ]
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    added_count = 0
    for student in demo_students:
        try:
            # Check if student already exists
            cursor.execute("SELECT enrollment_no FROM students WHERE enrollment_no = %s" if db.use_cloud else "SELECT enrollment_no FROM students WHERE enrollment_no = ?", (student[0],))
            if cursor.fetchone():
                print(f"  Student {student[0]} already exists, skipping...")
                continue
            
            placeholder = "%s" if db.use_cloud else "?"
            cursor.execute(f'''INSERT INTO students 
                (enrollment_no, name, email, phone, department, year) 
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})''', student)
            added_count += 1
            print(f"  Added: {student[1]} ({student[0]})")
        except Exception as e:
            print(f"  Error adding {student[0]}: {e}")
    
    conn.commit()
    conn.close()
    print(f"✓ Successfully added {added_count} demo students\n")
    return added_count

def add_demo_books(db):
    """Add demo books to database"""
    print("Adding demo books...")
    
    demo_books = [
        # Programming Books - only book_id, title, author, category, total_copies, available_copies
        ('PY001', 'Python Programming', 'Mark Lutz', 'Programming', 5, 5),
        ('PY002', 'Python Crash Course', 'Eric Matthes', 'Programming', 3, 3),
        ('JAVA001', 'Head First Java', 'Kathy Sierra', 'Programming', 4, 4),
        ('JAVA002', 'Effective Java', 'Joshua Bloch', 'Programming', 3, 3),
        ('CPP001', 'C++ Primer', 'Stanley Lippman', 'Programming', 4, 4),
        ('JS001', 'JavaScript: The Good Parts', 'Douglas Crockford', 'Programming', 3, 3),
        
        # Data Structures & Algorithms
        ('DSA001', 'Introduction to Algorithms', 'Thomas Cormen', 'Data Structures', 5, 5),
        ('DSA002', 'Data Structures and Algorithms', 'Aho Ullman', 'Data Structures', 4, 4),
        ('DSA003', 'Algorithm Design Manual', 'Steven Skiena', 'Data Structures', 3, 3),
        
        # Database Books
        ('DB001', 'Database System Concepts', 'Silberschatz', 'Database', 4, 4),
        ('DB002', 'SQL Performance Explained', 'Markus Winand', 'Database', 3, 3),
        ('DB003', 'MongoDB: The Definitive Guide', 'Shannon Bradshaw', 'Database', 3, 3),
        
        # Web Development
        ('WEB001', 'Learning Web Design', 'Jennifer Robbins', 'Web Development', 4, 4),
        ('WEB002', 'Django for Beginners', 'William Vincent', 'Web Development', 3, 3),
        ('WEB003', 'React in Action', 'Mark Thomas', 'Web Development', 3, 3),
        
        # Artificial Intelligence
        ('AI001', 'Artificial Intelligence', 'Stuart Russell', 'AI & ML', 4, 4),
        ('ML001', 'Pattern Recognition', 'Christopher Bishop', 'AI & ML', 3, 3),
        ('ML002', 'Deep Learning', 'Ian Goodfellow', 'AI & ML', 4, 4),
        
        # Networking
        ('NET001', 'Computer Networks', 'Andrew Tanenbaum', 'Networking', 5, 5),
        ('NET002', 'TCP/IP Illustrated', 'W. Richard Stevens', 'Networking', 3, 3),
        
        # Operating Systems
        ('OS001', 'Operating System Concepts', 'Silberschatz', 'Operating Systems', 5, 5),
        ('OS002', 'Modern Operating Systems', 'Andrew Tanenbaum', 'Operating Systems', 4, 4),
        
        # Software Engineering
        ('SE001', 'Clean Code', 'Robert Martin', 'Software Engineering', 4, 4),
        ('SE002', 'Design Patterns', 'Gang of Four', 'Software Engineering', 3, 3),
        ('SE003', 'The Pragmatic Programmer', 'Hunt & Thomas', 'Software Engineering', 3, 3),
    ]
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    added_count = 0
    for book in demo_books:
        try:
            # Check if book already exists
            cursor.execute("SELECT book_id FROM books WHERE book_id = ?", (book[0],))
            if cursor.fetchone():
                print(f"  Book {book[0]} already exists, skipping...")
                continue
            
            # Insert with only existing columns
            cursor.execute('''INSERT INTO books 
                (book_id, title, author, category, total_copies, available_copies) 
                VALUES (?, ?, ?, ?, ?, ?)''', book)
            conn.commit()
            added_count += 1
            print(f"  Added: {book[1]} by {book[2]}")
        except Exception as e:
            print(f"  Error adding {book[0]}: {e}")
    
    conn.close()
    print(f"✓ Successfully added {added_count} demo books\n")
    return added_count

def add_demo_transactions(db):
    """Add demo transactions (borrow records) to database"""
    print("Adding demo transactions...")
    
    # Get students and books for creating realistic transactions
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get all students
    cursor.execute("SELECT enrollment_no FROM students LIMIT 10")
    students = [row[0] for row in cursor.fetchall()]
    
    # Get all books
    cursor.execute("SELECT book_id FROM books WHERE available_copies > 0 LIMIT 15")
    books = [row[0] for row in cursor.fetchall()]
    
    if not students or not books:
        print("  No students or books available for transactions")
        conn.close()
        return 0
    
    added_count = 0
    today = datetime.now()
    
    # Create various transaction scenarios
    transaction_scenarios = [
        # Active loans (borrowed recently)
        {'days_ago': 1, 'status': 'active', 'count': 3},
        {'days_ago': 3, 'status': 'active', 'count': 2},
        {'days_ago': 5, 'status': 'active', 'count': 2},
        
        # Overdue loans
        {'days_ago': 10, 'status': 'overdue', 'count': 2},
        {'days_ago': 15, 'status': 'overdue', 'count': 1},
        
        # Returned books
        {'days_ago': 20, 'status': 'returned', 'return_days_ago': 13, 'count': 3},
        {'days_ago': 30, 'status': 'returned', 'return_days_ago': 23, 'count': 2},
    ]
    
    used_combinations = set()
    
    for scenario in transaction_scenarios:
        for _ in range(scenario['count']):
            # Get unique student-book combination
            attempts = 0
            while attempts < 50:
                student = random.choice(students)
                book = random.choice(books)
                combo = (student, book)
                
                if combo not in used_combinations:
                    used_combinations.add(combo)
                    break
                attempts += 1
            
            if attempts >= 50:
                continue
            
            borrow_date = (today - timedelta(days=scenario['days_ago'])).strftime('%Y-%m-%d')
            due_date = (today - timedelta(days=scenario['days_ago']) + timedelta(days=7)).strftime('%Y-%m-%d')
            
            return_date = None
            fine = 0
            status = 'borrowed'
            
            if scenario['status'] == 'returned':
                return_date = (today - timedelta(days=scenario['return_days_ago'])).strftime('%Y-%m-%d')
                # Calculate fine if returned late
                due = datetime.strptime(due_date, '%Y-%m-%d')
                ret = datetime.strptime(return_date, '%Y-%m-%d')
                if ret > due:
                    days_late = (ret - due).days
                    fine = days_late * 5  # 5 rupees per day
            elif scenario['status'] == 'overdue':
                # Calculate fine for overdue books
                due = datetime.strptime(due_date, '%Y-%m-%d')
                days_late = (today - due).days
                fine = days_late * 5
            
            try:
                # Check if transaction already exists
                cursor.execute('''SELECT id FROM borrow_records 
                    WHERE enrollment_no = ? AND book_id = ? AND borrow_date = ?''',
                    (student, book, borrow_date))
                
                if cursor.fetchone():
                    continue
                
                cursor.execute('''INSERT INTO borrow_records 
                    (enrollment_no, book_id, borrow_date, due_date, return_date, status, fine, academic_year) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    (student, book, borrow_date, due_date, return_date, status, fine, '2024-25'))
                
                # Update book availability if not returned
                if return_date is None:
                    cursor.execute('''UPDATE books SET available_copies = available_copies - 1 
                        WHERE book_id = ? AND available_copies > 0''', (book,))
                
                added_count += 1
                status_text = f"{scenario['status']} {'(Fine: ₹' + str(fine) + ')' if fine > 0 else ''}"
                print(f"  Added: {student} borrowed {book} on {borrow_date} - {status_text}")
                
            except Exception as e:
                print(f"  Error adding transaction: {e}")
    
    conn.commit()
    conn.close()
    print(f"✓ Successfully added {added_count} demo transactions\n")
    return added_count

def add_demo_admin_activity(db):
    """Add sample admin activity logs"""
    print("Adding demo admin activity logs...")
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Create table if it doesn't exist
    try:
        cursor.execute('''CREATE TABLE IF NOT EXISTS admin_activity (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            action TEXT NOT NULL,
            details TEXT,
            admin_user TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.commit()
    except:
        pass
    
    activities = [
        (datetime.now() - timedelta(days=1), 'System Login', 'Admin logged into the system', 'Admin'),
        (datetime.now() - timedelta(days=1, hours=2), 'Student Added', 'Added new student: Rajesh Kumar (220501001)', 'Admin'),
        (datetime.now() - timedelta(days=2), 'Book Added', 'Added new book: Python Programming (PY001)', 'Admin'),
        (datetime.now() - timedelta(days=3), 'Book Issued', 'Issued book PY001 to student 220501001', 'Admin'),
        (datetime.now() - timedelta(days=5), 'Book Returned', 'Book JAVA001 returned by student 210501003', 'Admin'),
        (datetime.now() - timedelta(days=7), 'Report Generated', 'Generated Students Report - Excel format', 'Admin'),
        (datetime.now() - timedelta(days=10), 'Settings Updated', 'Updated library fine settings', 'Admin'),
    ]
    
    added_count = 0
    for activity in activities:
        try:
            timestamp = activity[0].strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''INSERT INTO admin_activity (timestamp, action, details, admin_user)
                VALUES (?, ?, ?, ?)''', (timestamp, activity[1], activity[2], activity[3]))
            added_count += 1
        except Exception as e:
            print(f"  Error adding activity: {e}")
    
    conn.commit()
    conn.close()
    print(f"✓ Successfully added {added_count} admin activity logs\n")
    return added_count

def main():
    """Main function to add all demo data"""
    print("=" * 60)
    print("IARE Library Management System - Demo Data Generator")
    print("=" * 60)
    print()
    
    # Initialize database
    db = Database()
    
    # Add demo data
    students_added = add_demo_students(db)
    books_added = add_demo_books(db)
    transactions_added = add_demo_transactions(db)
    activities_added = add_demo_admin_activity(db)
    
    # Summary
    print("=" * 60)
    print("DEMO DATA SUMMARY")
    print("=" * 60)
    print(f"Students Added:      {students_added}")
    print(f"Books Added:         {books_added}")
    print(f"Transactions Added:  {transactions_added}")
    print(f"Activity Logs Added: {activities_added}")
    print("=" * 60)
    print("\n✓ Demo data has been successfully added to the database!")
    print("You can now test the Reports feature with this sample data.\n")

if __name__ == "__main__":
    main()
