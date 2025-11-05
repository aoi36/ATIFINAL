# app.py
import os
import threading
import time
from flask import Flask
from flask_cors import CORS

# Import from our new modules
import config
import database
import routes
import schedule # Assuming you still use this for the background scheduler
import state # To set stop flag

# --- Create App ---
app = Flask(__name__)
CORS(app) # Enable CORS
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER

# --- Register Blueprints ---
app.register_blueprint(routes.bp)

# --- Register Teardown Function ---
app.teardown_appcontext(database.close_connection)

# --- Background Scheduler Thread ---
stop_scheduler = threading.Event()
def run_background_schedule():
    """Runs the schedule loop in a separate thread."""
    print("[Scheduler] Background scheduler thread started.")
    while not stop_scheduler.is_set():
        schedule.run_pending()
        time.sleep(1) # Check every second
    print("[Scheduler] Background scheduler thread stopped.")

# ==============================================================================
# RUN FLASK APP & BACKGROUND SCHEDULER
# ==============================================================================
if __name__ == '__main__':
    # --- Setup Database on Start ---
    database.setup_database()
    
    # --- Start Background Scheduler ---
    print("[Scheduler] Starting background scheduler thread...")
    scheduler_thread = threading.Thread(target=run_background_schedule, daemon=True)
    scheduler_thread.start()

    # --- Run Flask App ---
    print(f"Starting Flask server on http://0.0.0.0:5000...")
    print("Press Ctrl+C to stop the server.")
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\nCtrl+C received. Shutting down...")
    finally:
        # --- Cleanup ---
        print("[Scheduler] Signaling scheduler thread to stop...")
        stop_scheduler.set()
        if scheduler_thread.is_alive():
            scheduler_thread.join(timeout=5)
        print("[Scheduler] Scheduler thread stopped.")
        print("Flask server stopped.")