// src/pages/AIToolsPage.jsx

import React, { useState, useEffect } from "react"
import Card from "../components/Card"
import LoadingSpinner from "../components/LoadingSpinner"
import ErrorAlert from "../components/ErrorAlert"
import { apiCall } from "../utils/api"
import ReactMarkdown from 'react-markdown';
import "./AIToolsPage.css"
import QuestionList from "../components/QuestionList" // Make sure this is imported

function AIToolsPage({ setCurrentPage, setHomeworkSubmitParams }) {
  const [activeTab, setActiveTab] = useState("summarize")
  const [file, setFile] = useState(null)
  const [question, setQuestion] = useState("")
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // State for homework grader
  const [answerText, setAnswerText] = useState('');
  const [answerFile, setAnswerFile] = useState(null);
  const [courseFiles, setCourseFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState('');
  const [loadingFiles, setLoadingFiles] = useState(false);

  // State for courses and selected course ID
  const [courses, setCourses] = useState([])
  const [selectedCourseId, setSelectedCourseId] = useState("")
  const [loadingCourses, setLoadingCourses] = useState(true)

  // Fetch courses when the component loads
  useEffect(() => {
    const fetchCourses = async () => {
      try {
        setLoadingCourses(true)
        const data = await apiCall("/api/courses")
        setCourses(data || [])
      } catch (err) {
        setError(err.message || "Failed to load courses list")
      } finally {
        setLoadingCourses(false)
      }
    }
    fetchCourses()
  }, [])

  // Fetch course files when 'Homework' tab is active and a course is selected
  useEffect(() => {
    if (activeTab === 'homework' && selectedCourseId) {
      const fetchFiles = async () => {
        try {
          setLoadingFiles(true);
          setCourseFiles([]);
          setSelectedFile('');
          // This call is correct. It uses the local course.id (e.g., 1, 2)
          const data = await apiCall(`/api/course/${selectedCourseId}/files`);
          setCourseFiles(data || []);
        } catch (err) {
          setError(err.message || 'Failed to load course files.');
        } finally {
          setLoadingFiles(false);
        }
      };
      fetchFiles();
    }
  }, [activeTab, selectedCourseId]);


const handleFileChange = (e) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      const validExtensions = [".txt", ".pdf", ".docx", ".pptx"]
      const fileExtension = "." + selectedFile.name.split(".").pop().toLowerCase()
      if (validExtensions.includes(fileExtension)) {
        setFile(selectedFile); setError(null)
      } else {
        setError("Invalid file type. Please upload: TXT, PDF, DOCX, or PPTX"); setFile(null)
      }
    }
  }

  const handleAnswerFileChange = (e) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setAnswerFile(selectedFile);
      setError(null);
    }

  };

  // Centralized submit handler
  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!selectedCourseId) {
      setError("Please select a course")
      return
    }

    let endpoint = ""
    const formData = new FormData()
    let sourceFileName = file?.name;

    if (activeTab === "summarize") {
        if (!file) { setError("Please select a file"); return; }
        endpoint = "/api/summarize_upload";
        formData.append("file", file);
    } else if (activeTab === "questions") {
        if (!file) { setError("Please select a file"); return; }
        endpoint = "/api/generate_questions";
        formData.append("file", file);
    } else if (activeTab === "hint") {
        if (!file) { setError("Please select a file"); return; }
        if (!question.trim()) { setError("Please enter a question"); return; }
        endpoint = "/api/get_hint";
        formData.append("file", file);
        formData.append("question", question);
    } else if (activeTab === "homework") {
        endpoint = "/api/homework/grade";
        if (!selectedFile) { setError("Please select the homework file"); return; }
        if (!answerText && !answerFile) { setError("Please provide an answer"); return; }
        
        formData.append('filename', selectedFile);
        sourceFileName = selectedFile;
        if (answerText) formData.append('answer_text', answerText);
        if (answerFile) formData.append('answer_file', answerFile);
    // --- [BUG #3 FIX] ---
    // Added the 'flashcards' tab logic
    } else if (activeTab === "flashcards") {
        if (!file) { setError("Please select a file"); return; }
        endpoint = "/api/generate_flashcards";
        formData.append("file", file);
    // --- [END BUG #3 FIX] ---
    } else {
      return;
    }

    // --- [BUG #1 FIX] ---
    // The backend API expects 'course_db_id', not 'course_id'
    formData.append("course_db_id", selectedCourseId)
    // --- [END BUG #1 FIX] ---

    // --- Make API Call ---
    try {
      setLoading(true)
      setError(null)
      setResult(null)
      
      const data = await apiCall(endpoint, {
        method: "POST",
        body: formData,
        isFormData: true,
      })

      // This sets the result to the data returned from the API
      // e.g., { summary: [...], review_questions: [...], score: "8/10", etc. }
      setResult({ ...data, source_file: sourceFileName });

    } catch (err) {
      setError(err.message || "Failed to process file")
      setResult(null)
    } finally {
      setLoading(false)
    }
  }
  
  // --- [NEW] Helper to clear state when changing tabs ---
  const changeTab = (tabName) => {
    setActiveTab(tabName);
    setResult(null);
    setError(null);
    setFile(null);
    setAnswerFile(null);
    setQuestion("");
    // Reset file input fields
    const fileInput = document.getElementById("file-input");
    if (fileInput) fileInput.value = "";
    const answerFileInput = document.getElementById("answer-file-input");
    if (answerFileInput) answerFileInput.value = "";
  }

  return (
    <div className="ai-tools-page">
      <h1 className="page-title">AI Learning Tools</h1>

      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      <div className="tools-container">
        <div className="tabs">
          <button
            className={`tab ${activeTab === "summarize" ? "active" : ""}`}
            onClick={() => changeTab("summarize")}
          >
            Summarizer
          </button>
          <button
            className={`tab ${activeTab === "questions" ? "active" : ""}`}
            onClick={() => changeTab("questions")}
          >
            Question Generator
          </button>
          <button
            className={`tab ${activeTab === "hint" ? "active" : ""}`}
            onClick={() => changeTab("hint")}
          >
            Homework Hints
          </button>
           <button
            className={`tab ${activeTab === "homework" ? "active" : ""}`}
            onClick={() => changeTab("homework")}
          >
            Homework Grader
          </button>
           {/* You were missing this from your posted code, but your collab file implies it */}
           <button
            className={`tab ${activeTab === "flashcards" ? "active" : ""}`}
            onClick={() => changeTab("flashcards")}
          >
            Flashcards
          </button>
        </div>

        <div className="tools-content">
          <div className="tool-panel">
            <Card>
              <form onSubmit={handleSubmit} className="tool-form">
                
                {/* --- Course Selection Dropdown --- */}
                <div className="form-group">
                  <label className="form-label">1. Select Course</label>
                  {loadingCourses ? ( <LoadingSpinner /> ) : (
                    <select
                      className="form-input"
                      value={selectedCourseId}
                      onChange={(e) => setSelectedCourseId(e.target.value)}
                      required
                    >
                      <option value="" disabled>-- Select a course --</option>
                      {courses.map((course) => (
                        // --- [BUG #2 FIX] ---
                        // 'key' and 'value' MUST be 'course.id'
                        // This was the bug causing you to send the course name
                        <option key={course.id} value={course.id}>
                          {course.name}
                        </option>
                        // --- [END BUG #2 FIX] ---
                      ))}
                    </select>
                  )}
                </div>

                {/* Show file upload for tabs that need it */}
                {activeTab !== 'homework' && (
                  <div className="form-group">
                    <label className="form-label">2. Upload Document</label>
                    <div className="file-input-wrapper">
                      <input
                        type="file"
                        id="file-input"
                        className="file-input"
                        onChange={handleFileChange}
                        accept=".txt,.pdf,.docx,.pptx"
                      />
                      <label htmlFor="file-input" className="file-label">
                        {file ? `📄 ${file.name}` : "📁 Choose File"}
                      </label>
                    </div>
                  </div>
                )}
                
                {/* Show homework-specific fields */}
                {activeTab === 'homework' && (
                  <>
                    <div className="form-group">
                      <label className="form-label">2. Select Homework File</label>
                      {loadingFiles ? <LoadingSpinner /> : (
                        <select
                          className="form-input"
                          value={selectedFile}
                          onChange={(e) => setSelectedFile(e.target.value)}
                          required
                          disabled={!selectedCourseId}
                        >
                          <option value="" disabled>-- Select a file --</option>
                          {courseFiles.map((fileName) => (
                            <option key={fileName} value={fileName}>
                              {decodeURIComponent(fileName)}
                            </option>
                          ))}
                        </select>
                      )}
                    </div>
                    <div className="form-group">
                      <label className="form-label">3. Your Answer (Text)</label>
                      <textarea
                        className="form-input"
                        value={answerText}
                        onChange={(e) => setAnswerText(e.target.value)}
                        placeholder="Type your answer here..."
                        rows="5"
                        disabled={!!answerFile}
                      ></textarea>
                    </div>
                    <div className="form-group">
                      <label className="form-label">Or Upload Your Answer (File)</label>
                      <div className="file-input-wrapper">
                        <input
                          type="file"
                          id="answer-file-input"
                          className="file-input"
                          onChange={handleAnswerFileChange}
                          disabled={!!answerText}
                        />
                        <label htmlFor="answer-file-input" className="file-label">
                          {answerFile ? `📄 ${answerFile.name}` : "📁 Choose Answer File"}
                        </label>
                      </div>
                    </div>
                  </>
                )}

                {/* --- Hint Question Textarea --- */}
                {activeTab === "hint" && (
                  <div className="form-group">
                    <label className="form-label">3. Your Question</label>
                    <textarea
                      className="form-input"
                      placeholder="Enter your homework question or what you're stuck on..."
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      rows="4"
                      required
                    />
                  </div>
                )}

                <button type="submit" className="submit-button" disabled={loading || loadingCourses}>
                  {loading ? "Processing..." : 
                   activeTab === "summarize" ? "Summarize" :
                   activeTab === "questions" ? "Generate Questions" :
                   activeTab === "hint" ? "Get Hint" :
                   activeTab === "homework" ? "Grade Homework" : 
                   activeTab === "flashcards" ? "Create Flashcards" : "Go"}
                </button>
              </form>
            </Card>
          </div>

          <div className="result-panel">
            {loading ? (
              <LoadingSpinner />
            ) : result ? (
              <Card title={`Result for "${decodeURIComponent(result.source_file)}"`}>
                <div className="result-content">
                  
                  {activeTab === "summarize" && result.summary && (
                    <div className="summary-list">
                      <strong>Summary:</strong>
                      <ul>
                        {result.summary?.map((item, idx) => <li key={idx}>{item}</li>) || <li>No summary.</li>}
                      </ul>
                      <strong>Key Topics:</strong>
                      <ul>
                        {result.key_topics?.map((item, idx) => <li key={idx}>{item}</li>) || <li>No topics.</li>}
                      </ul>
                    </div>
                  )}

                  {activeTab === "hint" && result.hint && (
                    <p className="result-text">{result.hint}</p>
                  )}
                  
                  {activeTab === "questions" && result.review_questions && (
                    <QuestionList questions={result.review_questions} />
                  )}
                  
                  {activeTab === 'homework' && result.score && (
                    <div className="grading-result">
                        <div className="result-section">
                            <h4>Score</h4>
                            <p>{result.score}</p>
                        </div>
                        <div className="result-section">
                            <h4>Feedback</h4>
                            <ReactMarkdown>{result.feedback}</ReactMarkdown>
                        </div>
                        <div className="result-section">
                            <h4>Explanation</h4>
                            <ReactMarkdown>{result.explanation}</ReactMarkdown>
                        </div>
                        
                        {result.saved_file_name && setHomeworkSubmitParams && setCurrentPage && (
                          <div className="result-section auto-submit-section">
                            <button
                              className="submit-button"
                              onClick={() => {
                                setHomeworkSubmitParams({
                                  prefilledFileName: result.saved_file_name
                                })
                                setCurrentPage('homework-submit')
                              }}
                            >
                              Auto-Submit to LMS
                            </button>
                          </div>
                        )}
                    </div>
                  )}

                  {/* --- [NEW] Render logic for flashcards --- */}
                  {activeTab === "flashcards" && result.flashcards && (
                    <div className="flashcards-list">
                      {result.flashcards.map((card, idx) => (
                        <div key={idx} className="flashcard-item">
                          <div className="flashcard-term"><strong>{card.term}</strong> ({card.category})</div>
                          <div className="flashcard-def">{card.definition}</div>
                        </div>
                      ))}
                    </div>
                  )}
                  {/* --- [END NEW] --- */}

                </div>
              </Card>
            ) : (
              <div className="placeholder">
                <p>Results will appear here</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default AIToolsPage