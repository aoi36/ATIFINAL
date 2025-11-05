# ai_service.py
import google.generativeai as genai
import re
import time
import json
from config import GOOGLE_API_KEY # Import from config

# --- AI Client Setup ---
print("Initializing Google Gemini client...")
ai_client = None
if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        generation_config = {"response_mime_type": "application/json", "temperature": 0.0}
        ai_client = genai.GenerativeModel("models/gemini-flash-latest", generation_config=generation_config)
        ai_client.generate_content("test", generation_config={"response_mime_type": "text/plain"})
        print("🤖 Google Gemini client initialized successfully.")
    except Exception as e:
        print(f"⚠️ Failed to initialize Gemini client: {e}. AI features will be disabled.")
        ai_client = None
else:
    print("⚠️ GOOGLE_API_KEY not found. AI features will be disabled.")
    ai_client = None

# --- AI Helper Functions ---
# (Paste your functions: analyze_document_with_ai, generate_multiple_choice_ai, 
#  and generate_hint_with_ai here, exactly as they were in app.py)
#
# Example (paste your full function):
def analyze_document_with_ai(file_text: str, file_type: str) -> dict | None:
    if not ai_client: return None
    if not file_text or file_text.isspace(): return None


    print(f"         [AI Analyze] Sending {file_type} text ({len(file_text)} chars) to Gemini...")
    if len(file_text) > 100000: file_text = file_text[:100000] + "...(truncated)"


    prompt = f"""You are a teaching assistant. Summarize the main topics (3 bullets) & extract key terms (max 5) from this '{file_type}' text.
Return ONLY JSON: {{"summary": [], "key_topics": []}}. If unusable, return null. TEXT: {file_text}"""


    max_retries = 3
    for attempt in range(max_retries):
        try:
            # --- API Call ---
            response = ai_client.generate_content(prompt)
            data_string = response.text
            if data_string.strip().lower() == "null":
                print("         [AI Analyze] AI indicated text was not useful.")
                return None # Successfully determined not useful
            data = json.loads(data_string)
            print(f"         [AI Analyze] AI summary received (Attempt {attempt+1}).")
            return data # Success! Exit the function.


        except Exception as e:
            error_str = str(e)
            is_rate_limit = "429" in error_str


            if is_rate_limit:
                wait_time = 60 # Default
                match = re.search(r'(?:retry(?:_delay)?|Please retry in)\s*(?:{\s*seconds:\s*|\s*)(\d+)', error_str, re.IGNORECASE)
                if match: wait_time = int(match.group(1)) + 2
                print(f"         [AI Analyze] Rate Limit (429). Waiting {wait_time}s (Attempt {attempt+1}/{max_retries})...")


                # Check if it's the last attempt BEFORE sleeping
                if attempt + 1 >= max_retries:
                    print("         [AI Analyze] Max retries reached after rate limit.")
                    break # Exit the loop, will return None below
                else:
                    time.sleep(wait_time)
                    # --- Use continue to go to the next iteration of the loop ---
                    continue


            else: # Handle other errors (like JSON parsing, etc.)
                print(f"         [AI Analyze] AI method failed (Attempt {attempt+1}/{max_retries}): {e}")
                if hasattr(response, 'text'): print(f"         [AI Analyze] Raw response: {response.text}")
                # Optional: Add a short delay before retrying non-rate-limit errors?
                # time.sleep(5)


                # Check if it's the last attempt
                if attempt + 1 >= max_retries:
                    print(f"         [AI Analyze] Max retries reached after error.")
                    break # Exit the loop
                else:
                     # Optionally add a small delay before the next attempt for non-429 errors
                     time.sleep(5)
                     continue # Go to the next iteration


    # This part is reached only if the loop finishes without returning (i.e., max retries hit)
    return None

def generate_multiple_choice_ai(file_text: str, file_type: str) -> dict | None:
    """Sends extracted text to Gemini to generate multiple-choice review questions."""
    if not ai_client: return None
    if not file_text or file_text.isspace(): return None

    print(f"         [AI MCQs] Sending {file_type} text ({len(file_text)} chars) to Gemini...")
    if len(file_text) > 100000: file_text = file_text[:100000] + "...(truncated)"

    # --- New Prompt for Multiple Choice ---
    prompt = f"""
    You are a helpful study assistant and quiz creator. Analyze the following text from a '{file_type}'.
    Generate 5 to 7 multiple-choice questions that cover the main topics in the text.
    For each question, provide:
    1.  The 'question' text.
    2.  A list of 4 'options'. The options should be strings (e.g., "A. Option 1", "B. Option 2").
    3.  The 'correct_answer', which MUST be one of the exact strings from the 'options' list.
    4.  A brief 'explanation' for why that answer is correct, based *only* on the provided text.

    Return ONLY a valid JSON object in this format:
    {{"review_questions": [
        {{
            "question": "What is the capital of France?",
            "options": ["A. London", "B. Berlin", "C. Paris", "D. Madrid"],
            "correct_answer": "C. Paris",
            "explanation": "The text states that Paris is the capital of France."
        }}
    ]}}

    If the text is unusable or you cannot generate questions, return null.
    
    TEXT:
    {file_text}
    """
    # --- End New Prompt ---

    max_retries = 3
    base_wait_time = 10

    for attempt in range(max_retries):
        response = None
        try:
            # --- API Call ---
            response = ai_client.generate_content(prompt)
            data_string = response.text
            if data_string.strip().lower() == "null":
                print("         [AI MCQs] AI indicated text was not useful.")
                return None
            data = json.loads(data_string)
            print(f"         [AI MCQs] AI multiple-choice questions received (Attempt {attempt+1}).")
            return data # Success!

        except Exception as e:
            # --- (Full retry logic, same as before) ---
            error_str = str(e); is_rate_limit = "429" in error_str; is_server_error = any(code in error_str for code in ["500", "502", "503", "504"])
            wait_time = 0
            if is_rate_limit:
                wait_time = 60; match = re.search(r'(?:retry(?:_delay)?|Please retry in)\s*(?:{\s*seconds:\s*|\s*)(\d+)', error_str, re.IGNORECASE);
                if match: wait_time = int(match.group(1)) + 2
                print(f"         [AI MCQs] Rate Limit (429). Waiting {wait_time}s...")
            elif is_server_error:
                wait_time = base_wait_time * (2 ** attempt); print(f"         [AI MCQs] Server Error. Waiting {wait_time}s...")
            else: wait_time = 5; print(f"         [AI MCQs] Failed: {e}")
            
            if response is not None and hasattr(response, 'text'):
                 print(f"         [AI MCQs] Raw response content: {response.text}")
            
            if attempt + 1 >= max_retries: print(f"         [AI MCQs] Max retries reached."); break
            else: time.sleep(wait_time); continue
            # --- (End Retry Logic) ---

    return None # Failed after retries

def generate_hint_with_ai(file_text: str, file_type: str, user_question: str) -> dict | None:
    """Sends extracted text and a user's question to Gemini to get a hint."""
    if not ai_client: return None
    if not file_text or file_text.isspace(): return None

    print(f"         [AI Hint] Sending {file_type} text ({len(file_text)} chars) to Gemini for a hint on: '{user_question}'")
    if len(file_text) > 100000: file_text = file_text[:100000] + "...(truncated)"

    # --- New Prompt for Getting a Hint ---
    prompt = f"""
    You are a Socratic teaching assistant. A student is working on a homework assignment (a '{file_type}') and is stuck.
    
    The student's specific question or problem is:
    "{user_question}"
    
    Here is the full text of the assignment file for context:
    ---
    {file_text}
    ---
    
    Your task is to provide a helpful HINT. 
    **DO NOT give the direct answer.**
    Instead, ask a guiding question, suggest a concept from the text to review, or provide a small first step.
    
    Return ONLY a valid JSON object in this format:
    {{"hint": "Your helpful hint or guiding question goes here."}}
    
    If the text is unusable or the question is unclear, return null.
    """
    # --- End New Prompt ---

    max_retries = 3
    base_wait_time = 10

    for attempt in range(max_retries):
        response = None
        try:
            response = ai_client.generate_content(prompt)
            data_string = response.text
            if data_string.strip().lower() == "null":
                print("         [AI Hint] AI indicated text/question was not useful.")
                return None
            data = json.loads(data_string)
            print(f"         [AI Hint] AI hint received (Attempt {attempt+1}).")
            return data # Success!

        except Exception as e:
            # --- (Full retry logic, same as before) ---
            error_str = str(e); is_rate_limit = "429" in error_str; is_server_error = any(code in error_str for code in ["500", "502", "503", "504"])
            wait_time = 0
            if is_rate_limit:
                wait_time = 60; match = re.search(r'(?:retry(?:_delay)?|Please retry in)\s*(?:{\s*seconds:\s*|\s*)(\d+)', error_str, re.IGNORECASE);
                if match: wait_time = int(match.group(1)) + 2
                print(f"         [AI Hint] Rate Limit (429). Waiting {wait_time}s...")
            elif is_server_error:
                wait_time = base_wait_time * (2 ** attempt); print(f"         [AI Hint] Server Error. Waiting {wait_time}s...")
            else: wait_time = 5; print(f"         [AI Hint] Failed: {e}")
            
            if response is not None and hasattr(response, 'text'):
                 print(f"         [AI Hint] Raw response content: {response.text}")
            
            if attempt + 1 >= max_retries: print(f"         [AI Hint] Max retries reached."); break
            else: time.sleep(wait_time); continue
            # --- (End Retry Logic) ---

    return None # Failed after retries