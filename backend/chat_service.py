# chat_service.py
import os
import json
import requests
import base64
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any

# AI Provider Imports
import google.generativeai as genai
import anthropic
from openai import OpenAI

# Import from your config
from config import (
    GOOGLE_API_KEY,
    DATABASE_FILE,
    SAVE_DIR,
    MAX_TEXT_LENGTH_FOR_SUMMARY
)
from scraper_service import read_pdf, read_docx, read_pptx, read_txt

# --- Environment Variables (Add to your .env file) ---
# ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...
# GOOGLE_API_KEY=AIza... (already exists)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# --- AI Client Initialization ---
print("[Chat] Initializing AI clients...")

# GitHub Models
github_client = None
if GITHUB_TOKEN:
    try:
        # Test the API
        test_response = requests.post(
            "https://models.inference.ai.azure.com/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {GITHUB_TOKEN}"
            },
            json={
                "messages": [{"role": "user", "content": "test"}],
                "model": "gpt-4o"
            },
            timeout=10
        )
        if test_response.status_code == 200:
            github_client = True  # Just a flag that it works
            print("  ✅ GitHub Models initialized")
        else:
            print(f"  ⚠️ GitHub Models failed: {test_response.status_code}")
    except Exception as e:
        print(f"  ⚠️ GitHub Models failed: {e}")
else:
    print("  ⚠️ GITHUB_TOKEN not found")
# Gemini
gemini_client = None
if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        gemini_client = genai.GenerativeModel("models/gemini-2.0-flash-exp")
        print("  ✅ Gemini initialized")
    except Exception as e:
        print(f"  ⚠️ Gemini failed: {e}")

# Claude
claude_client = None
if ANTHROPIC_API_KEY:
    try:
        claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        print("  ✅ Claude initialized")
    except Exception as e:
        print(f"  ⚠️ Claude failed: {e}")

# ChatGPT
openai_client = None
if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        print("  ✅ ChatGPT initialized")
    except Exception as e:
        print(f"  ⚠️ ChatGPT failed: {e}")



def get_course_context(user_id: int, course_db_id: int, max_chars: int = 15000) -> str:
    """
    Retrieves text content from a specific course's scraped files.
    Returns concatenated text up to max_chars.
    """
    print(f"[Chat] Loading course context for course_db_id {course_db_id}...")
    
    try:
        db = sqlite3.connect(DATABASE_FILE)
        db.row_factory = sqlite3.Row
        cursor = db.cursor()
        
        # Get course info
        course = cursor.execute(
            "SELECT lms_course_id, name FROM courses WHERE id = ? AND user_id = ?",
            (course_db_id, user_id)
        ).fetchone()
        db.close()
        
        if not course:
            return ""
        
        # Build the course folder path
        import re
        safe_name = re.sub(r'[\\/*?:"<>|]', "_", course['name']).strip()[:150]
        course_folder = os.path.join(SAVE_DIR, f"user_{user_id}", f"{course['lms_course_id']}_{safe_name}")
        
        if not os.path.exists(course_folder):
            return ""
        
        # Read all .txt files (which contain extracted text)
        all_text = f"=== COURSE: {course['name']} ===\n\n"
        
        for filename in os.listdir(course_folder):
            if filename.lower().endswith(".txt"):
                txt_path = os.path.join(course_folder, filename)
                try:
                    with open(txt_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        all_text += f"--- {filename} ---\n{content}\n\n"
                        
                        if len(all_text) > max_chars:
                            all_text = all_text[:max_chars] + "\n\n[Context truncated...]"
                            break
                except Exception as e:
                    print(f"  ⚠️ Failed to read {filename}: {e}")
        
        return all_text
        
    except Exception as e:
        print(f"[Chat] Error loading course context: {e}")
        return ""


def extract_file_content(user_id: int, course_db_id: int, filename: str) -> tuple[str, str]:
    """
    Extracts text from an uploaded/referenced file.
    Returns (file_type, extracted_text).
    """
    import re
    
    try:
        db = sqlite3.connect(DATABASE_FILE)
        db.row_factory = sqlite3.Row
        cursor = db.cursor()
        
        course = cursor.execute(
            "SELECT lms_course_id, name FROM courses WHERE id = ? AND user_id = ?",
            (course_db_id, user_id)
        ).fetchone()
        db.close()
        
        if not course:
            return "Unknown", ""
        
        safe_name = re.sub(r'[\\/*?:"<>|]', "_", course['name']).strip()[:150]
        course_folder = os.path.join(SAVE_DIR, f"user_{user_id}", f"{course['lms_course_id']}_{safe_name}")
        file_path = os.path.join(course_folder, filename)
        
        if not os.path.exists(file_path):
            return "Unknown", ""
        
        # Extract based on file type
        ext = os.path.splitext(filename)[1].lower()
        
        if ext == '.pdf':
            return "PDF", read_pdf(file_path)
        elif ext == '.docx':
            return "Word", read_docx(file_path)
        elif ext == '.pptx':
            return "PowerPoint", read_pptx(file_path)
        elif ext == '.txt':
            return "Text", read_txt(file_path)
        else:
            return "Unknown", ""
            
    except Exception as e:
        print(f"[Chat] Error extracting file {filename}: {e}")
        return "Unknown", ""


# ==============================================================================
# AI PROVIDER FUNCTIONS
# ==============================================================================

def chat_with_gemini(
    conversation_history: List[Dict[str, str]], 
    system_prompt: str = ""
) -> tuple[str, int]:
    """
    Sends conversation to Gemini and returns (response_text, token_count).
    """
    if not gemini_client:
        return "Gemini API is not configured.", 0
    
    try:
        # Build the full conversation
        full_messages = []
        
        if system_prompt:
            full_messages.append({
                "role": "user",
                "parts": [{"text": f"SYSTEM INSTRUCTIONS:\n{system_prompt}"}]
            })
            full_messages.append({
                "role": "model",
                "parts": [{"text": "Understood. I will follow these instructions."}]
            })
        
        # Add conversation history
        for msg in conversation_history:
            role = "model" if msg["role"] == "assistant" else "user"
            full_messages.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
        
        # Send to Gemini
        chat = gemini_client.start_chat(history=full_messages[:-1])
        response = chat.send_message(full_messages[-1]["parts"][0]["text"])
        
        response_text = response.text
        
        # Estimate tokens (Gemini doesn't provide exact count)
        token_count = len(response_text.split()) * 1.3  # Rough estimate
        
        return response_text, int(token_count)
        
    except Exception as e:
        print(f"[Chat] Gemini error: {e}")
        return f"Error communicating with Gemini: {str(e)}", 0


def chat_with_claude(
    conversation_history: List[Dict[str, str]], 
    system_prompt: str = ""
) -> tuple[str, int]:
    """
    Sends conversation to Claude and returns (response_text, token_count).
    """
    if not claude_client:
        return "Claude API is not configured.", 0
    
    try:
        # Build messages (Claude uses a specific format)
        messages = []
        for msg in conversation_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Send to Claude
        response = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt if system_prompt else "You are a helpful AI assistant for students.",
            messages=messages
        )
        
        response_text = response.content[0].text
        
        # Get token usage
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        total_tokens = input_tokens + output_tokens
        
        print(f"[Chat] Claude tokens: {input_tokens} in + {output_tokens} out = {total_tokens} total")
        
        return response_text, output_tokens
        
    except Exception as e:
        print(f"[Chat] Claude error: {e}")
        return f"Error communicating with Claude: {str(e)}", 0

def chat_with_github(
    conversation_history: List[Dict[str, str]], 
    system_prompt: str = "",
    model: str = "gpt-4o"  # Options: "gpt-4o", "gpt-4o-mini", "o1-preview", "o1-mini"
) -> tuple[str, int]:
    """
    Sends conversation to GitHub Models API and returns (response_text, token_count).
    
    Available models:
    - gpt-4o: Most capable, best for complex tasks
    - gpt-4o-mini: Faster and cheaper, good for simple tasks
    - o1-preview: Advanced reasoning (slower)
    - o1-mini: Faster reasoning model
    """
    if not github_client:
        return "GitHub Models API is not configured.", 0
    
    try:
        # Build messages in OpenAI format
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Add conversation history
        for msg in conversation_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Send to GitHub Models API
        response = requests.post(
            "https://models.inference.ai.azure.com/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {GITHUB_TOKEN}"
            },
            json={
                "messages": messages,
                "model": model,
                "temperature": 0.7,
                "max_tokens": 4096
            },
            timeout=60  # GitHub Models can be slower
        )
        
        if response.status_code != 200:
            error_msg = f"GitHub API error {response.status_code}: {response.text}"
            print(f"[Chat] {error_msg}")
            return error_msg, 0
        
        data = response.json()
        
        # Extract response text
        response_text = data["choices"][0]["message"]["content"]
        
        # Get token usage
        usage = data.get("usage", {})
        total_tokens = usage.get("total_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        
        print(f"[Chat] GitHub Models ({model}) tokens: {total_tokens} total ({completion_tokens} completion)")
        
        return response_text, completion_tokens
        
    except requests.exceptions.Timeout:
        return "GitHub Models API request timed out. Please try again.", 0
    except Exception as e:
        print(f"[Chat] GitHub Models error: {e}")
        return f"Error communicating with GitHub Models: {str(e)}", 0
    

def chat_with_openai(
    conversation_history: List[Dict[str, str]], 
    system_prompt: str = ""
) -> tuple[str, int]:
    """
    Sends conversation to ChatGPT and returns (response_text, token_count).
    """
    if not openai_client:
        return "OpenAI API is not configured.", 0
    
    try:
        # Build messages
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        for msg in conversation_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Send to OpenAI
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=4096,
            temperature=0.7
        )
        
        response_text = response.choices[0].message.content
        
        # Get token usage
        total_tokens = response.usage.total_tokens
        completion_tokens = response.usage.completion_tokens
        
        print(f"[Chat] OpenAI tokens: {total_tokens} total ({completion_tokens} completion)")
        
        return response_text, completion_tokens
        
    except Exception as e:
        print(f"[Chat] OpenAI error: {e}")
        return f"Error communicating with ChatGPT: {str(e)}", 0


# ==============================================================================
# MAIN CHAT FUNCTION
# ==============================================================================

def send_chat_message(
    user_id: int,
    message: str,
    conversation_id: Optional[int] = None,
    ai_provider: str = "gemini",
    course_db_id: Optional[int] = None,
    attachments: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Main function to handle chat messages.
    
    Args:
        user_id: The user sending the message
        message: The user's message text
        conversation_id: Existing conversation ID (or None to create new)
        ai_provider: "gemini", "claude", or "chatgpt"
        course_db_id: Optional course context
        attachments: List of filenames to include
    
    Returns:
        Dict with conversation_id, response, and metadata
    """
    print(f"\n[Chat] User {user_id} -> {ai_provider}: {message[:60]}...")
    
    db = None
    
    try:
        db = sqlite3.connect(DATABASE_FILE)
        db.row_factory = sqlite3.Row
        cursor = db.cursor()
        
        # --- 1. Create or Load Conversation ---
        if conversation_id:
            # Load existing conversation
            conv = cursor.execute(
                "SELECT * FROM chat_conversations WHERE id = ? AND user_id = ?",
                (conversation_id, user_id)
            ).fetchone()
            
            if not conv:
                db.close()
                return {"error": "Conversation not found or unauthorized"}
            
            # Update timestamp
            cursor.execute(
                "UPDATE chat_conversations SET updated_at = ? WHERE id = ?",
                (datetime.now(), conversation_id)
            )
        else:
            # Create new conversation
            title = message[:50] + "..." if len(message) > 50 else message
            
            cursor.execute(
                """INSERT INTO chat_conversations 
                   (user_id, title, ai_provider, course_db_id) 
                   VALUES (?, ?, ?, ?)""",
                (user_id, title, ai_provider, course_db_id)
            )
            conversation_id = cursor.lastrowid
            print(f"[Chat] Created new conversation {conversation_id}")
        
        # --- 2. Build Context ---
        context_parts = []
        
        # Add course context if specified
        if course_db_id:
            course_context = get_course_context(user_id, course_db_id)
            if course_context:
                context_parts.append(course_context)
        
        # Add attachment content
        if attachments:
            for filename in attachments:
                if course_db_id:
                    file_type, content = extract_file_content(user_id, course_db_id, filename)
                    if content:
                        context_parts.append(f"=== ATTACHMENT: {filename} ({file_type}) ===\n\n{content[:10000]}")
        
        # Build system prompt
        system_prompt = "You are a helpful AI study assistant for university students."
        
        if context_parts:
            combined_context = "\n\n".join(context_parts)
            system_prompt += f"\n\nRELEVANT COURSE MATERIALS:\n{combined_context[:25000]}"
        
        # --- 3. Load Conversation History ---
        history_rows = cursor.execute(
            """SELECT role, content FROM chat_messages 
               WHERE conversation_id = ? 
               ORDER BY created_at ASC""",
            (conversation_id,)
        ).fetchall()
        
        conversation_history = [
            {"role": row["role"], "content": row["content"]} 
            for row in history_rows
        ]
        
        # Add current user message
        conversation_history.append({
            "role": "user",
            "content": message
        })
        
        # --- 4. Save User Message ---
        cursor.execute(
            """INSERT INTO chat_messages 
               (conversation_id, role, content, attachments) 
               VALUES (?, ?, ?, ?)""",
            (conversation_id, "user", message, json.dumps(attachments) if attachments else None)
        )
        
        # --- 5. Send to AI Provider ---
        if ai_provider == "gemini":
            response_text, token_count = chat_with_gemini(conversation_history, system_prompt)
        elif ai_provider == "claude":
            response_text, token_count = chat_with_claude(conversation_history, system_prompt)
        elif ai_provider == "chatgpt":
            response_text, token_count = chat_with_openai(conversation_history, system_prompt)
        elif ai_provider == "github":  # ADD THIS
            response_text, token_count = chat_with_github(conversation_history, system_prompt)
        else:
            db.close()
            return {"error": f"Unknown AI provider: {ai_provider}"}
        
        # --- 6. Save Assistant Response ---
        cursor.execute(
            """INSERT INTO chat_messages 
               (conversation_id, role, content, token_count) 
               VALUES (?, ?, ?, ?)""",
            (conversation_id, "assistant", response_text, token_count)
        )
        
        db.commit()
        
        print(f"[Chat] Response saved ({token_count} tokens)")
        
        # --- 7. Return Result ---
        return {
            "conversation_id": conversation_id,
            "response": response_text,
            "ai_provider": ai_provider,
            "token_count": token_count,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"[Chat] Error: {e}")
        if db:
            db.rollback()
        return {"error": str(e)}
        
    finally:
        if db:
            db.close()


def get_conversation_history(user_id: int, conversation_id: int) -> Dict[str, Any]:
    """
    Retrieves full conversation history.
    """
    try:
        db = sqlite3.connect(DATABASE_FILE)
        db.row_factory = sqlite3.Row
        cursor = db.cursor()
        
        # Get conversation info
        conv = cursor.execute(
            "SELECT * FROM chat_conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user_id)
        ).fetchone()
        
        if not conv:
            db.close()
            return {"error": "Conversation not found"}
        
        # Get messages
        messages = cursor.execute(
            """SELECT role, content, attachments, token_count, created_at 
               FROM chat_messages 
               WHERE conversation_id = ? 
               ORDER BY created_at ASC""",
            (conversation_id,)
        ).fetchall()
        
        db.close()
        
        return {
            "conversation_id": conversation_id,
            "title": conv["title"],
            "ai_provider": conv["ai_provider"],
            "course_id": conv["course_db_id"],
            "created_at": conv["created_at"],
            "messages": [
                {
                    "role": msg["role"],
                    "content": msg["content"],
                    "attachments": json.loads(msg["attachments"]) if msg["attachments"] else [],
                    "token_count": msg["token_count"],
                    "timestamp": msg["created_at"]
                }
                for msg in messages
            ]
        }
        
    except Exception as e:
        print(f"[Chat] Error getting history: {e}")
        return {"error": str(e)}


def list_user_conversations(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Lists all conversations for a user.
    """
    try:
        db = sqlite3.connect(DATABASE_FILE)
        db.row_factory = sqlite3.Row
        cursor = db.cursor()
        
        conversations = cursor.execute(
            """SELECT c.*, 
                      COUNT(m.id) as message_count,
                      courses.name as course_name
               FROM chat_conversations c
               LEFT JOIN chat_messages m ON c.id = m.conversation_id
               LEFT JOIN courses ON c.course_db_id = courses.id
               WHERE c.user_id = ?
               GROUP BY c.id
               ORDER BY c.updated_at DESC
               LIMIT ?""",
            (user_id, limit)
        ).fetchall()
        
        db.close()
        
        return [
            {
                "conversation_id": conv["id"],
                "title": conv["title"],
                "ai_provider": conv["ai_provider"],
                "course_name": conv["course_name"],
                "message_count": conv["message_count"],
                "created_at": conv["created_at"],
                "updated_at": conv["updated_at"]
            }
            for conv in conversations
        ]
        
    except Exception as e:
        print(f"[Chat] Error listing conversations: {e}")
        return []


def delete_conversation(user_id: int, conversation_id: int) -> bool:
    """
    Deletes a conversation and all its messages.
    """
    try:
        db = sqlite3.connect(DATABASE_FILE)
        cursor = db.cursor()
        
        cursor.execute(
            "DELETE FROM chat_conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user_id)
        )
        
        deleted = cursor.rowcount > 0
        db.commit()
        db.close()
        
        return deleted
        
    except Exception as e:
        print(f"[Chat] Error deleting conversation: {e}")
        return False