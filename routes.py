# routes.py
import os
import json
import threading
import glob
import traceback # Import traceback for error logging
from flask import (
    Blueprint, jsonify, request, abort, g, send_from_directory, render_template_string
)
from werkzeug.utils import secure_filename
from datetime import datetime

# Import services and helpers
import state
import schedule # For the meet scheduler
from database import get_db
from config import (
    UPLOAD_FOLDER, MEET_RECORDING_DIR, SAVE_DIR, ALLOWED_EXTENSIONS,
    MAX_TEXT_LENGTH_FOR_SUMMARY
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
    SimpleFormatter, open_dir, exists_in, 
    ContextFragmenter, INDEX_DIR
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

@bp.route('/api/scrape', methods=['POST'])
def trigger_scrape():
    """Triggers the full scraping process in a background thread."""
    if state.IS_SCRAPING:
        return jsonify({"status": "Scrape already in progress."}), 409
    print("API: Received request to start scrape...")
    from config import LMS_USERNAME, LMS_PASSWORD # Import credentials just in time
    scraping_thread = threading.Thread(target=perform_full_scrape, args=(LMS_USERNAME, LMS_PASSWORD), daemon=True)
    scraping_thread.start()
    return jsonify({"status": "Scrape initiated in background."}), 202

@bp.route('/api/scrape/status', methods=['GET'])
def get_scrape_status():
    """Checks the global 'is_scraping' flag."""
    status_str = "scraping" if state.IS_SCRAPING else "idle"
    return jsonify({"status": status_str})

@bp.route('/api/courses', methods=['GET'])
def get_courses():
    """Returns the list of courses from the database."""
    print("API: Received request for /api/courses")
    try:
        db = get_db()
        courses_rows = db.execute('SELECT * FROM courses ORDER BY name').fetchall()
        courses = [dict(row) for row in courses_rows]
        print(f"API: Found {len(courses)} courses in database.")
        return jsonify(courses)
    except Exception as e:
        print(f"API Error: /api/courses: {e}"); traceback.print_exc()
        return jsonify({"error": f"Failed to read courses from database: {e}"}), 500

@bp.route('/api/deadlines/<course_id>', methods=['GET'])
def get_course_deadlines(course_id):
    """Returns deadlines for a specific course from the database."""
    try:
        db = get_db()
        deadlines_rows = db.execute(
            'SELECT * FROM deadlines WHERE course_id = ? ORDER BY parsed_iso_date ASC',
            (course_id,)
        ).fetchall()
        deadlines = [dict(row) for row in deadlines_rows]
        return jsonify(deadlines)
    except Exception as e:
        print(f"API Error: /api/deadlines/{course_id}: {e}"); traceback.print_exc()
        return jsonify({"error": f"Failed to read deadlines from database: {e}"}), 500

@bp.route('/api/course/<course_id>/content', methods=['GET'])
def get_course_user_content(course_id):
    """Gets all user-generated content (summaries, etc.) from the database."""
    try:
        db = get_db()
        content_rows = db.execute(
            'SELECT * FROM user_content WHERE course_id = ? ORDER BY created_at DESC',
            (course_id,)
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
        print(f"API Error: /api/course/{course_id}/content: {e}"); traceback.print_exc()
        return jsonify({"error": f"Failed to read content from database: {e}"}), 500

@bp.route('/api/course/<course_id>/files', methods=['GET'])
def get_course_files(course_id):
    """Finds the course data folder and lists all relevant scraped files."""
    course_folder = find_course_folder(course_id)
    if not course_folder:
        return jsonify({"error": f"Data folder for course {course_id} not found."}), 404
    try:
        all_files = os.listdir(course_folder)
        # Filter for file types you want to show the user
        relevant_extensions = ('.pdf', '.pptx', '.docx', '.txt', '.zip', '.rar')
        scraped_files = [f for f in all_files if f.lower().endswith(relevant_extensions)]
        return jsonify(scraped_files)
    except Exception as e:
        print(f"API Error: /api/course/{course_id}/files: {e}"); traceback.print_exc()
        return jsonify({"error": f"Failed to list files: {e}"}), 500

@bp.route('/api/get_file/<course_id>/<path:filename>', methods=['GET'])
def get_scraped_file(course_id, filename):
    """Securely finds and serves a specific file for download/viewing."""
    course_folder = find_course_folder(course_id)
    if not course_folder:
        return jsonify({"error": f"Data folder for course ID {course_id} not found."}), 404

    # Use os.path.abspath to prevent path traversal
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

@bp.route('/api/search', methods=['GET'])
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
def summarize_uploaded_file():
    """Accepts a 'file' + 'course_id', saves summary to DB."""
    if not ai_client: return jsonify({"error": "AI client not initialized."}), 503
    if 'file' not in request.files: return jsonify({"error": "No 'file' part."}), 400
    if 'course_id' not in request.form: return jsonify({"error": "No 'course_id' field."}), 400

    file = request.files['file']; course_id = request.form.get('course_id')
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
                cursor.execute(
                    'INSERT INTO user_content (course_id, source_file, type, content_json) VALUES (?, ?, ?, ?)',
                    (course_id, filename, 'summary', json.dumps(summary_data))
                )
                db.commit()
                print(f"API: Saved summary for {filename} (Course {course_id}) to DB.")
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
def generate_questions_endpoint():
    """Accepts a 'file' + 'course_id', saves questions to DB."""
    if not ai_client: return jsonify({"error": "AI client not initialized."}), 503
    if 'file' not in request.files: return jsonify({"error": "No 'file' part."}), 400
    if 'course_id' not in request.form: return jsonify({"error": "No 'course_id' field."}), 400

    file = request.files['file']; course_id = request.form.get('course_id')
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
                cursor.execute(
                    'INSERT INTO user_content (course_id, source_file, type, content_json) VALUES (?, ?, ?, ?)',
                    (course_id, filename, 'questions', json.dumps(question_data))
                )
                db.commit()
                print(f"API: Saved questions for {filename} (Course {course_id}) to DB.")
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
def get_hint_endpoint():
    """Accepts 'file', 'question', 'course_id', saves hint to DB."""
    if not ai_client: return jsonify({"error": "AI client not initialized."}), 503
    if 'file' not in request.files: return jsonify({"error": "No 'file' part."}), 400
    if 'question' not in request.form: return jsonify({"error": "No 'question' field."}), 400
    if 'course_id' not in request.form: return jsonify({"error": "No 'course_id' field."}), 400

    file = request.files['file']; user_question = request.form.get('question'); course_id = request.form.get('course_id')
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
                cursor.execute(
                    'INSERT INTO user_content (course_id, source_file, type, user_question, content_json) VALUES (?, ?, ?, ?, ?)',
                    (course_id, filename, 'hint', user_question, json.dumps(hint_data))
                )
                db.commit()
                print(f"API: Saved hint for {filename} (Course {course_id}) to DB.")
                hint_data["saved_to_db"] = True
            except Exception as save_e:
                print(f"API: ⚠️ Failed to save hint to DB: {save_e}"); db.rollback()
            return jsonify(hint_data), 200
        else:
            return jsonify({"error": "AI analysis failed."}), 500
    except Exception as e:
        print(f"API: Error in get_hint: {e}"); traceback.print_exc()
        return jsonify({"error": f"An internal server error occurred: {e}"}), 500
    finally:
        if local_path and os.path.exists(local_path):
            try: os.remove(local_path); print(f"API: Cleaned up temp file {local_path}")
            except Exception as del_e: print(f"API: ⚠️ Failed to delete temp file: {del_e}")

@bp.route('/api/schedule_meet', methods=['POST'])
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