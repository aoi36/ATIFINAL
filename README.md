# 🎓 LMS AI Assistant

> An intelligent, proactive agent that automates your university life. Scrape course materials, sync deadlines to Google Calendar, generate AI study plans, record Google Meets, and interact with your course content using AI.

![Project Status](https://img.shields.io/badge/status-active-success.svg)
![Backend](https://img.shields.io/badge/backend-Flask%20%7C%20Python-blue)
![Frontend](https://img.shields.io/badge/frontend-React%20%7C%20Vite-61DAFB)
![Database](https://img.shields.io/badge/database-SQLite-lightgrey)

---

## ✨ Key Features

* **🔄 Automated LMS Scraping**: Logs into your university LMS, downloads course files (.pdf, .docx, .pptx), and extracts deadlines.
* **🧠 AI Study Tools**:
  * Summarizer: Generate instant summaries of lecture slides.
  * Quiz Generator: Create multiple-choice questions from course materials.
  * Homework Helper: Get Socratic hints without revealing the answer.
  * Auto-Grader: Upload your homework and let AI grade it.
  * Flashcards: Automatically generate study flashcards from documents.
* **📅 Smart Calendar**: Syncs LMS deadlines to your Google Calendar and generates AI-powered study blocks.
* **🔍 Full-Text Search**: Search through all downloaded files.
* **📹 Meet Automation**: Joins scheduled Google Meets, records screen & system audio, and transcribes meetings.
* **🔒 Secure & Multi-User**: JWT-based authentication supports multiple users with isolated data and encrypted credentials.

---

## 🛠️ Tech Stack

**Backend:** Python, Flask, Flask-CORS, SQLite, Selenium, Whoosh, OpenCV, MSS, MoviePy, OpenAI Whisper, SoundDevice  
**Frontend:** React, Vite, CSS Modules, FullCalendar  

---

## ⚙️ System Prerequisites

1. **FFmpeg** (for video recording & transcription)  
   * Windows: `choco install ffmpeg`  
   * Mac: `brew install ffmpeg`  
   * Linux: `sudo apt install ffmpeg`

2. **LibreOffice** (for converting .pptx/.docx to PDF)  
   * Add LibreOffice to your PATH.

3. **Stereo Mix** (Windows only) for system audio recording:  
   * Enable via **Sound Settings → Recording → Show Disabled Devices → Stereo Mix**.

---

## 🚀 Full Setup Instructions

Follow these steps to set up the **backend** and **frontend**. You can copy the entire block and execute step by step:

🚀 Backend Setup
1. Navigate to the backend folder
cd backend

2. Create a virtual environment

Windows:

python -m venv venv
.\venv\Scripts\activate


Mac/Linux:

python3 -m venv venv
source venv/bin/activate

3. Install dependencies
pip install -r requirements.txt

4. Create a .env file in backend/ with the following content
# LMS credentials
LMS_USERNAME=your_student_id
LMS_PASSWORD=your_password

# Email notifications
GMAIL_SENDER=your_email@gmail.com
GMAIL_APP_PASSWORD=your_16_char_app_password
GMAIL_RECEIVER=your_email@gmail.com

# Security
SECRET_KEY=random_string_for_jwt_tokens
ENCRYPTION_KEY=random_key_for_fernet

# Google Calendar
GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json

5. Google Calendar setup

Place service_account.json in the backend root folder.

Share your Google Calendar with the client_email from the JSON file.

6. Initialize the database (run once)
python migrate_chat_tables.py

7. Start the backend server
python app.py

🚀 Frontend Setup
1. Navigate to the frontend folder
cd ../frontend

2. Install dependencies
npm install

3. Create a .env file in frontend/ with the following content
VITE_API_URL=http://127.0.0.1:5000

4. Start the frontend development server
npm run dev

Run frontend development server

npm run dev
