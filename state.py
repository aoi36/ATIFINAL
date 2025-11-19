# state.py

# Tracks if the process is running
IS_SCRAPING = False

# Tracks the result of the LAST run
# Structure: { "success": bool, "message": str } or None
LAST_SCRAPE_RESULT = None