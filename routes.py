# routes.py
import os
import json
import threading
import re
import glob
import sqlite3
from whoosh.highlight import ContextFragmenter, PinpointFragmenter
from whoosh.qparser import QueryParser
import jwt
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import traceback # Import traceback for error logging
from flask import (
    Blueprint, jsonify, request, abort, g, send_from_directory, render_template_string
)
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, timezone

# Import services and helpers
import state
import schedule # For the meet scheduler
from database import get_db
from config import (
    UPLOAD_FOLDER, MEET_RECORDING_DIR, SAVE_DIR, ALLOWED_EXTENSIONS,
    MAX_TEXT_LENGTH_FOR_SUMMARY, SECRET_KEY
)
from scraper_service import (
    perform_full_scrape, read_pdf, read_docx, read_pptx, read_txt
)
from ai_service import (
    ai_client, analyze_document_with_ai, generate_multiple_choice_ai,
    generate_hint_with_ai
)
from meeting_service import join_meet_automated_and_record
from search_service import (
    SimpleFormatter, open_dir, exists_in, INDEX_DIR
)

# --- Create the Blueprint ---
bp = Blueprint('api', __name__)

# --- [NEW] Helper Function for Routes ---
# This is used by multiple endpoints to find the correct data folder
def find_course_folder(course_id):
    """Helper to find the course folder based on ID."""
    # Use glob to find the folder matching the ID prefix
    # Relies on SAVE_DIR being an absolute path from config.py
    pattern = os.path.join(SAVE_DIR, f"{course_id}_*")
    print(f"   [API Debug] find_course_folder searching for pattern: {pattern}")
    try:
        matches = glob.glob(pattern)
        if matches and os.path.isdir(matches[0]):
            print(f"   [API Debug] find_course_folder found: {matches[0]}")
            return matches[0] # Return the first match
    except Exception as e:
        print(f"   [API Debug] Error in find_course_folder: {e}")
    print("   [API Debug] find_course_folder found nothing.")
    return None
# ----------------------------------------
# --- [NEW] Authentication Decorator (The "Gatekeeper") ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]

        if not token:
            return jsonify({"error": "Token is missing."}), 401

        try:
            db = get_db()
            
            # 1. Decode the token
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            
            # --- [NEW] Check if token is in the blocklist ---
            jti = data.get('jti') # 'jti' is the unique token ID
            if not jti:
                return jsonify({"error": "Token is invalid (missing jti)."}), 401
                
            is_blocked = db.execute("SELECT 1 FROM jwt_blocklist WHERE jti = ?", (jti,)).fetchone()
            if is_blocked:
                return jsonify({"error": "Token has been logged out."}), 401
            # --- [END NEW] ---

            # 2. Find the user
            current_user = db.execute("SELECT * FROM user WHERE id = ?", (data['user_id'],)).fetchone()
            if not current_user:
                 return jsonify({"error": "User not found."}), 401
            
            # 3. Make the user and token available to the route
            g.current_user = dict(current_user)
            g.token_jti = jti # Store the jti in 'g' for the logout function
            
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Token is invalid."}), 401
        
        return f(*args, **kwargs)
    return decorated

# --- API Endpoints ---
@bp.route('/')
def home():
    """Serves the main API endpoint list."""
    status = "Scraping in progress..." if state.IS_SCRAPING else "Idle"
    return render_template_string("""
    <h1>LMS Scraper Backend</h1>
    <p>Status: <strong>{{ status }}</strong></p>
    <p>Data Path: {{ save_dir }}</p>
    <h3>API Endpoints:</h3>
    <ul>
        <li><b>POST /api/scrape</b> - Trigger a new background scrape.</li>
        <li><b>GET /api/scrape/status</b> - Check if scrape is running.</li>
        <li><b>GET /api/courses</b> - Get all courses from DB.</li>
        <li><b>GET /api/deadlines/&lt;course_id&gt;</b> - Get deadlines for a course.</li>
        <li><b>GET /api/course/&lt;course_id&gt;/content</b> - Get all AI content for a course.</li>
        <li><b>GET /api/course/&lt;course_id&gt;/files</b> - Get all scraped files for a course.</li>
        <li><b>GET /api/get_file/&lt;course_id&gt;/&lt;filename&gt;</b> - Download a specific file.</li>
        <li><b>GET /api/search?q=&lt;query&gt;</b> - Search indexed files.</li>
        <li><b>POST /api/summarize_upload</b> - Upload file+ID for summary.</li>
        <li><b>POST /api/generate_questions</b> - Upload file+ID for quiz.</li>
        <li><b>POST /api/get_hint</b> - Upload file+ID+question for hint.</li>
        <li><b>POST /api/schedule_meet</b> - Schedule a Meet recording.</li>
    </ul>
    """, status=status, save_dir=os.path.abspath(SAVE_DIR))

@bp.route('/api/register', methods=['POST'])
def register_user():
    """Creates a new user in the database."""
    data = request.json
    lms_user = data.get('username')
    lms_pass = data.get('password')

    if not lms_user or not lms_pass:
        return jsonify({"error": "Username and password are required."}), 400

    hashed_password = generate_password_hash(lms_pass, method='pbkdf2:sha256')

    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO user (lms_username, hashed_password) VALUES (?, ?)",
            (lms_user, hashed_password)
        )
        db.commit()
        
        # Return the newly created user
        return jsonify({
            "id": cursor.lastrowid,
            "lms_username": lms_user
        }), 201
        
    except sqlite3.IntegrityError:
        # This triggers if the username is NOT UNIQUE
        return jsonify({"error": "This LMS Username is already registered."}), 409
    except Exception as e:
        db.rollback()
        print(f"API Error: /api/register: {e}"); traceback.print_exc()
        return jsonify({"error": f"An internal server error occurred: {e}"}), 500

@bp.route('/api/login', methods=['POST'])
def login_user():
    """Finds a user by username, checks their hashed password, and returns a JWT."""
    data = request.json
    lms_user = data.get('username')
    lms_pass = data.get('password')

    if not lms_user or not lms_pass:
        return jsonify({"error": "Username and password are required."}), 400

    db = get_db()
    # Find the user by their username
    user_row = db.execute(
        "SELECT * FROM user WHERE lms_username = ?", (lms_user,)
    ).fetchone()

    # --- [FIXED LOGIC] ---
    
    # 1. Check if user exists AND if the password is correct
    if user_row and check_password_hash(user_row['hashed_password'], lms_pass):
        
        user = dict(user_row) # Convert row to dictionary
        
        # 2. Passwords match! Create a token.
        print(f"API: Login successful for user {user['lms_username']} (ID: {user['id']})")
        jti = f"{user['id']}:{datetime.now(timezone.utc).timestamp()}"
        token = jwt.encode(
            {
                'user_id': user['id'],
                'jti': jti,
                'exp': datetime.utcnow() + timedelta(days=7) # Token expires in 7 days
            },
            SECRET_KEY,
            algorithm="HS256"
        )
        
        return jsonify({
            "token": token,
            "user": {
                "id": user['id'],
                "lms_username": user['lms_username']
            }
        }), 200
    
    # 3. If user not found OR password was wrong, return the same generic error
    else:
        print(f"API: Failed login attempt for username: {lms_user}")
        return jsonify({"error": "Invalid username or password."}), 401
    
    # --- [END FIXED LOGIC] ---



@bp.route('/api/logout', methods=['POST'])
@token_required # Use the decorator to verify the token first
def logout_user():
    """Logs the user out by adding their token's jti to the blocklist."""
    try:
        # 1. Get the 'jti' from the 'g' object (set by the @token_required decorator)
        jti = g.token_jti
        user_id = g.current_user['id']
        
        db = get_db()
        
        # 2. Add the token's unique ID to the blocklist
        db.execute("INSERT INTO jwt_blocklist (jti) VALUES (?)", (jti,))
        db.commit()
        
        print(f"API: User {user_id} successfully logged out.")
        return jsonify({"status": "Logout successful."}), 200
        
    except Exception as e:
        print(f"API Error: /api/logout: {e}"); traceback.print_exc()
        db.rollback()
        return jsonify({"error": f"An internal server error occurred: {e}"}), 500


@bp.route('/api/scrape', methods=['POST'])
@token_required  # <--- 1. Get the app user from the token
def trigger_scrape():
    """
    Triggers the full scraping process.
    - Gets the 'user_id' (who to save to) from the auth token.
    - Gets the 'lms_username' and 'lms_password' (what to scrape) from the JSON body.
    """
    if state.IS_SCRAPING:
        return jsonify({"status": "Scrape already in progress."}), 409

    # --- [THE FIX] ---
    
    # 2. Get the logged-in user's ID from the token
    user_id = g.current_user['id'] 

    # 3. Get the credentials for the account TO BE SCRAPED from the JSON body
    data = request.json
    if not data:
        return jsonify({"error": "Request body must be JSON."}), 400
    
    lms_user = data.get('username')
    lms_pass = data.get('password')
    
    if not lms_user or not lms_pass:
        return jsonify({"error": "LMS 'username' and 'password' are required in the JSON body."}), 400
    
    # --- [END FIX] ---

    print(f"API: Received scrape request for user_id {user_id} (scraping account: {lms_user})...")

    # 4. Pass all 3 arguments to the scrape thread
    scraping_thread = threading.Thread(
        target=perform_full_scrape, 
        args=(user_id, lms_user, lms_pass), # (who to save for, what to scrape)
        daemon=True
    )
    scraping_thread.start()
    
    return jsonify({"status": "Scrape initiated in background."}), 202

@bp.route('/api/scrape/status', methods=['GET'])
def get_scrape_status():
    """Checks the global 'is_scraping' flag."""
    status_str = "scraping" if state.IS_SCRAPING else "idle"
    return jsonify({"status": status_str})

@bp.route('/api/courses', methods=['GET']) # <-- [FIX] Removed <user_id> from URL
@token_required                          # <-- 1. Add decorator
def get_courses():
    """Returns the list of courses from the database for the logged-in user."""
    
    # --- [THE FIX] ---
    # 2. Get the user_id securely from the token
    user_id = g.current_user['id'] 
    # --- [END FIX] ---

    print(f"API: Received request for /api/courses for user_id {user_id}")
    try:
        db = get_db()
        # 3. The SQL query now correctly uses the user_id from the token
        courses_rows = db.execute(
            'SELECT * FROM courses WHERE user_id = ? ORDER BY name', (user_id,)
        ).fetchall()
        
        # Convert rows to dicts. 
        # IMPORTANT: The key will be 'id' (the local DB ID), not 'lms_course_id'
        courses = [dict(row) for row in courses_rows]
        print(f"API: Found {len(courses)} courses for user {user_id}.")
        return jsonify(courses)
    except Exception as e:
        print(f"API Error: /api/courses: {e}"); traceback.print_exc()
        return jsonify({"error": f"Failed to read courses: {e}"}), 500

# ---

# [MODIFIED] This endpoint now uses the local database ID for the course
@bp.route('/api/deadlines/<course_db_id>', methods=['GET']) 
@token_required # <-- 1. Add decorator
def get_course_deadlines(course_db_id):
    """Returns deadlines for a specific course, verifying the user owns it."""
    
    # --- [THE FIX] ---
    # 2. Get the user_id securely from the token
    user_id = g.current_user['id']
    # --- [END FIX] ---

    print(f"API: Received request for deadlines for course_db_id {course_db_id} by user {user_id}")
    try:
        db = get_db()
        
        # --- [THE FIX] ---
        # 3. Modify SQL to check BOTH course_db_id AND user_id
        # This prevents a user from seeing another user's deadlines
        deadlines_rows = db.execute(
            'SELECT * FROM deadlines WHERE course_db_id = ? AND user_id = ? ORDER BY parsed_iso_date ASC',
            (course_db_id, user_id)
        ).fetchall()
        # --- [END FIX] ---

        deadlines = [dict(row) for row in deadlines_rows]
        return jsonify(deadlines)
    except Exception as e:
        print(f"API Error: /api/deadlines/{course_db_id}: {e}"); traceback.print_exc()
        return jsonify({"error": f"Failed to read deadlines from database: {e}"}), 500

@bp.route('/api/course/<course_db_id>/content', methods=['GET'])
@token_required
def get_course_user_content(course_db_id):
    """Gets all user-generated content (summaries, etc.) from the database."""
    user_id = g.current_user['id']
    try:
        db = get_db()
        content_rows = db.execute(
            'SELECT * FROM user_content WHERE course_db_id = ? AND user_id = ? ORDER BY created_at DESC',
            (course_db_id, user_id)
        ).fetchall()
        # Parse the content_json string back into an object for the frontend
        content_list = []
        for row in content_rows:
            item = dict(row)
            try:
                item['content_json'] = json.loads(item['content_json'])
            except json.JSONDecodeError:
                item['content_json'] = {"error": "Failed to parse stored JSON."}
            content_list.append(item)
        return jsonify(content_list)
    except Exception as e:
        print(f"API Error: /api/course/{course_db_id}/content: {e}"); traceback.print_exc()
        return jsonify({"error": f"Failed to read content from database: {e}"}), 500

@bp.route('/api/course/<int:course_db_id>/files', methods=['GET'])
@token_required
def get_course_files(course_db_id):
    """
    Finds the course data folder FOR THE LOGGED-IN USER
    and lists all relevant scraped files.
    """
    
    # 1. Get the authenticated user's ID from the token
    user_id = g.current_user['id']
    
    try:
        # 2. Find the course in the DB, verifying this user owns it
        db = get_db()
        course = db.execute(
            "SELECT lms_course_id, name FROM courses WHERE id = ? AND user_id = ?",
            (course_db_id, user_id)
        ).fetchone()

        if not course:
            # This is a security block: either the course doesn't exist,
            # or this user doesn't own it.
            return jsonify({"error": "Course not found or you do not have permission to access it."}), 404

        # 3. Build the correct, user-specific path
        lms_course_id = course['lms_course_id']
        safe_course_name = re.sub(r'[\\/*?:"<>|]', "_", course['name']).strip()[:150]
        course_folder = os.path.join(SAVE_DIR, f"user_{user_id}", f"{lms_course_id}_{safe_course_name}")

        if not os.path.exists(course_folder):
             print(f"API: Verified user {user_id} owns course, but folder not found at {course_folder}")
             return jsonify({"error": f"Data folder for course {lms_course_id} not found."}), 404
        
        # 4. List the files
        all_files = os.listdir(course_folder)
        relevant_extensions = ('.pdf', '.pptx', '.docx', '.txt', '.zip', '.rar')
        scraped_files = [f for f in all_files if f.lower().endswith(relevant_extensions)]
        
        return jsonify(scraped_files)
        
    except Exception as e:
        print(f"API Error: /api/course/{course_db_id}/files: {e}"); traceback.print_exc()
        return jsonify({"error": f"Failed to list files: {e}"}), 500

@bp.route('/api/get_file/<int:course_db_id>/<path:filename>', methods=['GET'])
@token_required  # <-- 1. Add decorator to get the user
def get_scraped_file(course_db_id, filename):
    """
    Securely finds and serves a specific file for the logged-in user.
    """
    
    # 2. Get the authenticated user's ID from the token
    user_id = g.current_user['id']
    
    try:
        # 3. Find the course in the DB, verifying this user owns it
        db = get_db()
        course = db.execute(
            "SELECT lms_course_id, name FROM courses WHERE id = ? AND user_id = ?",
            (course_db_id, user_id)
        ).fetchone()

        if not course:
            # This is a security block: either the course doesn't exist,
            # or this user doesn't own it.
            return jsonify({"error": "Course not found or you do not have permission to access it."}), 404

        # 4. Build the correct, user-specific path
        lms_course_id = course['lms_course_id']
        safe_course_name = re.sub(r'[\\/*?:"<>|]', "_", course['name']).strip()[:150]
        course_folder = os.path.join(SAVE_DIR, f"user_{user_id}", f"{lms_course_id}_{safe_course_name}")

        # 5. Use the secure file sending logic
        directory_path = os.path.abspath(course_folder)
        file_path = os.path.abspath(os.path.join(directory_path, filename))

        # Security check: ensure the resolved path is still inside the intended directory
        if not file_path.startswith(directory_path):
            print(f"API: [SECURITY] Blocked path traversal attempt: {filename}")
            return jsonify({"error": "Invalid filename."}), 400

        if not os.path.exists(file_path):
            print(f"API: File not found at {file_path} (Original: {filename})")
            return jsonify({"error": f"File '{filename}' not found."}), 404

        try:
            # as_attachment=False tries to open in browser (PDF, TXT)
            # Browsers will auto-download what they can't open (DOCX, PPTX, ZIP)
            return send_from_directory(directory_path, filename, as_attachment=False)
        except Exception as e:
            print(f"API: Error sending file {filename}: {e}"); traceback.print_exc()
            return jsonify({"error": "Could not send file."}), 500
            
    except Exception as e:
        print(f"API Error: /api/get_file: {e}"); traceback.print_exc()
        return jsonify({"error": f"Failed to send file: {e}"}), 500

@bp.route('/api/search', methods=['GET'])
@token_required
def search_index():
    """Searches the Whoosh index for the query parameter 'q'."""
    query_str = request.args.get('q')
    if not query_str:
        return jsonify({"error": "Missing query parameter 'q'."}), 400
    if not exists_in(INDEX_DIR):
        return jsonify({"error": "Search index not found. Run a scrape first."}), 404

    try:
        ix = open_dir(INDEX_DIR)
        if ix.doc_count() == 0:
            return jsonify({"error": "Search index is empty."}), 404
        
        results_list = []
        with ix.searcher() as searcher:
            parser = QueryParser("content", ix.schema)
            try: query = parser.parse(query_str)
            except Exception as qp_e: return jsonify({"error": f"Error parsing query: {qp_e}"}), 400

            results = searcher.search(query, limit=10)
            results.formatter = SimpleFormatter()
            results.fragmenter = PinpointFragmenter(surround=50, maxchars=200) # Use Pinpoint

            print(f"API: Search for '{query_str}' found {len(results)} hit(s).")
            for hit in results:
                snippet = hit.highlights("content")
                if not snippet: snippet = (hit.get("content", "")[:200] + "...") if hit.get("content") else ""
                results_list.append({
                    "course_id": hit.get("course_id"), "course_name": hit.get("course_name"),
                    "file_name": hit.get("file_name"), "file_type": hit.get("file_type"),
                    "score": hit.score, "snippet": snippet
                })
        return jsonify(results_list)
    except Exception as e:
        print(f"API: Error during search: {e}"); traceback.print_exc()
        return jsonify({"error": f"An internal server error occurred: {e}"}), 500

@bp.route('/api/summarize_upload', methods=['POST'])
@token_required
def summarize_uploaded_file():
    """
    Accepts a 'file', 'course_db_id', and 'user_id'.
    Saves the summary to the 'user_content' table.
    """
    if not ai_client: return jsonify({"error": "AI client not initialized."}), 503

    user_id = g.current_user['id']
    
    # --- [MODIFIED] Check for new multi-user keys ---
    if 'file' not in request.files: return jsonify({"error": "No 'file' part."}), 400
    if 'course_db_id' not in request.form: return jsonify({"error": "No 'course_db_id' field."}), 400

    file = request.files['file']
    course_db_id = request.form.get('course_db_id')
  
    # --- [END MODIFIED] ---

    if file.filename == '': return jsonify({"error": "No file selected."}), 400

    filename = secure_filename(file.filename); _, file_ext = os.path.splitext(filename)
    if not filename or file_ext.lower() not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"File type not allowed. Allowed: {list(ALLOWED_EXTENSIONS)}"}), 400
    
    temp_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
    upload_path = os.path.join(UPLOAD_FOLDER, temp_filename)
    local_path = None; extracted_text = ""; file_type = "File"

    try:
        file.save(upload_path); local_path = upload_path
        print(f"API: Temp saved upload to {upload_path} for summary.")
        
        if file_ext.lower() == '.pdf': file_type="PDF"; extracted_text=read_pdf(upload_path)
        elif file_ext.lower() == '.docx': file_type="Word"; extracted_text=read_docx(upload_path)
        elif file_ext.lower() == '.pptx': file_type="PowerPoint"; extracted_text=read_pptx(upload_path)
        elif file_ext.lower() == '.txt': file_type="Text"; extracted_text=read_txt(upload_path)

        if not extracted_text: return jsonify({"error": f"Failed to extract text from '{filename}'."}), 500
        if len(extracted_text) > MAX_TEXT_LENGTH_FOR_SUMMARY:
            return jsonify({"error": f"File content too long (>{MAX_TEXT_LENGTH_FOR_SUMMARY} chars)."}), 413
            
        summary_data = analyze_document_with_ai(extracted_text, file_type)
        if summary_data:
            summary_data["source_file"] = filename
            try:
                db = get_db(); cursor = db.cursor()
                # --- [MODIFIED] Insert with user_id and course_db_id ---
                cursor.execute(
                    'INSERT INTO user_content (user_id, course_db_id, source_file, type, content_json) VALUES (?, ?, ?, ?, ?)',
                    (user_id, course_db_id, filename, 'summary', json.dumps(summary_data))
                )
                # --- [END MODIFIED] ---
                db.commit()
                print(f"API: Saved summary for {filename} (User {user_id}, CourseDB {course_db_id}) to DB.")
                summary_data["saved_to_db"] = True
            except Exception as save_e:
                print(f"API: ⚠️ Failed to save summary to DB: {save_e}"); db.rollback()
            return jsonify(summary_data), 200
        else:
            return jsonify({"error": "AI analysis failed."}), 500
    except Exception as e:
        print(f"API: Error in summarize_upload: {e}"); traceback.print_exc()
        return jsonify({"error": f"Internal server error: {e}"}), 500
    finally:
        if local_path and os.path.exists(local_path):
            try: os.remove(local_path); print(f"API: Cleaned up temp file {local_path}")
            except Exception as del_e: print(f"API: ⚠️ Failed to delete temp file: {del_e}")

@bp.route('/api/generate_questions', methods=['POST'])
@token_required # <-- 1. Add decorator
def generate_questions_endpoint():
    """
    Accepts 'file', 'course_db_id', and 'user_id' (from token). Saves questions to DB.
    """
    if not ai_client: return jsonify({"error": "AI client not initialized."}), 503
    
    # --- [THE FIX] ---
    user_id = g.current_user['id'] # 2. Get user_id from token
    if 'file' not in request.files: return jsonify({"error": "No 'file' part."}), 400
    if 'course_db_id' not in request.form: return jsonify({"error": "No 'course_db_id' field."}), 400

    file = request.files['file']
    course_db_id = request.form.get('course_db_id')
    # --- [END FIX] ---

    if file.filename == '': return jsonify({"error": "No file selected."}), 400

    filename = secure_filename(file.filename); _, file_ext = os.path.splitext(filename)
    if not filename or file_ext.lower() not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"File type not allowed. Allowed: {list(ALLOWED_EXTENSIONS)}"}), 400
    
    temp_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
    upload_path = os.path.join(UPLOAD_FOLDER, temp_filename)
    local_path = None; extracted_text = ""; file_type = "File"

    try:
        file.save(upload_path); local_path = upload_path
        print(f"API: Temp saved upload to {upload_path} for questions.")
        
        if file_ext.lower() == '.pdf': file_type="PDF"; extracted_text=read_pdf(upload_path)
        elif file_ext.lower() == '.docx': file_type="Word"; extracted_text=read_docx(upload_path)
        elif file_ext.lower() == '.pptx': file_type="PowerPoint"; extracted_text=read_pptx(upload_path)
        elif file_ext.lower() == '.txt': file_type="Text"; extracted_text=read_txt(upload_path)

        if not extracted_text: return jsonify({"error": f"Failed to extract text from '{filename}'."}), 500
        if len(extracted_text) > MAX_TEXT_LENGTH_FOR_SUMMARY:
            return jsonify({"error": f"File content too long (>{MAX_TEXT_LENGTH_FOR_SUMMARY} chars)."}), 413
            
        question_data = generate_multiple_choice_ai(extracted_text, file_type)
        if question_data:
            question_data["source_file"] = filename
            try:
                db = get_db(); cursor = db.cursor()
                # --- [THE FIX] ---
                # 3. Insert with user_id and course_db_id
                cursor.execute(
                    'INSERT INTO user_content (user_id, course_db_id, source_file, type, content_json) VALUES (?, ?, ?, ?, ?)',
                    (user_id, course_db_id, filename, 'questions', json.dumps(question_data))
                )
                # --- [END FIX] ---
                db.commit()
                print(f"API: Saved questions for {filename} (User {user_id}, CourseDB {course_db_id}) to DB.")
                question_data["saved_to_db"] = True
            except Exception as save_e:
                print(f"API: ⚠️ Failed to save questions to DB: {save_e}"); db.rollback()
            return jsonify(question_data), 200
        else:
            return jsonify({"error": "AI analysis failed."}), 500
    except Exception as e:
        print(f"API: Error in generate_questions: {e}"); traceback.print_exc()
        return jsonify({"error": f"Internal server error: {e}"}), 500
    finally:
        if local_path and os.path.exists(local_path):
            try: os.remove(local_path); print(f"API: Cleaned up temp file {local_path}")
            except Exception as del_e: print(f"API: ⚠️ Failed to delete temp file: {del_e}")

@bp.route('/api/get_hint', methods=['POST'])
@token_required
def get_hint_endpoint():
    """Accepts 'file', 'question', 'course_db_id', 'user_id', saves hint to DB."""
    if not ai_client: return jsonify({"error": "AI client not initialized."}), 503
    user_id = g.current_user['id']
    
    # --- [MODIFIED] Check for new multi-user keys ---
    if 'file' not in request.files: return jsonify({"error": "No 'file' part."}), 400
    if 'question' not in request.form: return jsonify({"error": "No 'question' field."}), 400
    if 'course_db_id' not in request.form: return jsonify({"error": "No 'course_db_id' field."}), 400

    file = request.files['file']
    user_question = request.form.get('question')
    course_db_id = request.form.get('course_db_id')
    # --- [END MODIFIED] ---
    
    if file.filename == '': return jsonify({"error": "No file selected."}), 400
    if not user_question: return jsonify({"error": "No 'question' provided."}), 400

    filename = secure_filename(file.filename); _, file_ext = os.path.splitext(filename)
    if not filename or file_ext.lower() not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"File type not allowed. Allowed: {list(ALLOWED_EXTENSIONS)}"}), 400
    
    temp_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
    upload_path = os.path.join(UPLOAD_FOLDER, temp_filename)
    local_path = None; extracted_text = ""; file_type = "File"

    try:
        file.save(upload_path); local_path = upload_path
        print(f"API: Temp saved upload to {upload_path} for hint.")
        
        if file_ext.lower() == '.pdf': file_type="PDF"; extracted_text=read_pdf(upload_path)
        elif file_ext.lower() == '.docx': file_type="Word"; extracted_text=read_docx(upload_path)
        elif file_ext.lower() == '.pptx': file_type="PowerPoint"; extracted_text=read_pptx(upload_path)
        elif file_ext.lower() == '.txt': file_type="Text"; extracted_text=read_txt(upload_path)
        
        if not extracted_text: return jsonify({"error": f"Failed to extract text from '{filename}'."}), 500
        if len(extracted_text) > MAX_TEXT_LENGTH_FOR_SUMMARY:
            return jsonify({"error": f"File content too long (>{MAX_TEXT_LENGTH_FOR_SUMMARY} chars)."}), 413
            
        hint_data = generate_hint_with_ai(extracted_text, file_type, user_question)
        if hint_data:
            hint_data["source_file"] = filename; hint_data["user_question"] = user_question
            try:
                db = get_db(); cursor = db.cursor()
                # --- [MODIFIED] Insert with user_id and course_db_id ---
                cursor.execute(
                    'INSERT INTO user_content (user_id, course_db_id, source_file, type, user_question, content_json) VALUES (?, ?, ?, ?, ?, ?)',
                    (user_id, course_db_id, filename, 'hint', user_question, json.dumps(hint_data))
                )
                # --- [END MODIFIED] ---
                db.commit()
                print(f"API: Saved hint for {filename} (User {user_id}, CourseDB {course_db_id}) to DB.")
                hint_data["saved_to_db"] = True
            except Exception as save_e:
                print(f"API: ⚠️ Failed to save hint to DB: {save_e}"); db.rollback()
            return jsonify(hint_data), 200
        else:
            return jsonify({"error": "AI analysis failed."}), 500
    except Exception as e:
        print(f"API: Error in get_hint: {e}"); traceback.print_exc()
        return jsonify({"error": f"Internal server error: {e}"}), 500
    finally:
        if local_path and os.path.exists(local_path):
            try: os.remove(local_path); print(f"API: Cleaned up temp file {local_path}")
            except Exception as del_e: print(f"API: ⚠️ Failed to delete temp file: {del_e}")

@bp.route('/api/schedule_meet', methods=['POST'])
@token_required
def schedule_meet_endpoint():
    """Schedules an AUTOMATED Google Meet join & record task."""
    data = request.json
    meet_link = data.get('meet_link')
    
    # --- [MODIFIED] Use the new 'join_datetime_str' ---
    join_datetime_str = data.get('join_datetime_str')
    duration_min_str = data.get('duration_minutes')
    
    # --- [NEW] Get user_name, default to "Assistant" ---
    user_name = data.get('user_name', 'Assistant') 
    # --------------------------------------------------

    if not all([meet_link, join_datetime_str, duration_min_str]):
        return jsonify({"error": "Missing: meet_link, join_datetime_str (YYYY-MM-DDTHH:MM), duration_minutes"}), 400

    try:
        # --- [MODIFIED] Use threading.Timer logic ---
        join_datetime = datetime.fromisoformat(join_datetime_str)
        now = datetime.now()
        delay_seconds = (join_datetime - now).total_seconds()
        
        if delay_seconds < 0:
            return jsonify({"error": "Cannot schedule a meeting in the past."}), 400
        
        duration_minutes = int(duration_min_str)
        if duration_minutes <= 0: raise ValueError("Duration must be positive.")

        print(f"API: Task received. Scheduling join for {join_datetime} (in {delay_seconds:.0f} seconds).")
        timer = threading.Timer(
            delay_seconds,
            join_meet_automated_and_record,
            args=[ # Arguments for the function
                meet_link,
                duration_minutes,
                MEET_RECORDING_DIR,
                user_name  # <-- Pass the user_name
            ]
        )
        timer.start() 
        # --- [END MODIFIED] ---
        
        print(f"API: Scheduled AUTOMATED Google Meet join for {join_datetime_str} ({duration_minutes} min) as '{user_name}'")
        return jsonify({"status": f"Automated Google Meet join scheduled for {join_datetime_str}."}), 200

    except ValueError as ve:
        return jsonify({"error": f"Invalid format: {ve}. Use YYYY-MM-DDTHH:MM and a positive duration."}), 400
    except Exception as e:
        print(f"API: Error scheduling automated Google Meet: {e}"); traceback.print_exc()
        return jsonify({"error": f"Failed to schedule automated Meet task: {e}"}), 500