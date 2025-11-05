// src/pages/AIToolsPage.jsx

import React, { useState, useEffect } from "react" // Ensure React is imported
import Card from "../components/Card"
import LoadingSpinner from "../components/LoadingSpinner"
import ErrorAlert from "../components/ErrorAlert"
import { apiCall } from "../utils/api"
import "./AIToolsPage.css" // Make sure this CSS file exists

function AIToolsPage() {
  const [activeTab, setActiveTab] = useState("summarize")
  const [file, setFile] = useState(null)
  const [question, setQuestion] = useState("")
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // State for courses and selected course ID
  const [courses, setCourses] = useState([])
  const [selectedCourseId, setSelectedCourseId] = useState("") // This will hold the ID (e.g., 473)
  const [loadingCourses, setLoadingCourses] = useState(true)

  // Fetch courses when the component loads
  useEffect(() => {
    const fetchCourses = async () => {
      try {
        setLoadingCourses(true)
        const data = await apiCall("/api/courses")
        setCourses(data || [])
        
        // By removing the setSelectedCourseId call here,
        // the state will remain "" (its initial value from useState)
        // which will cause the "-- Select a course --" option to be shown.
        
      } catch (err) {
        setError(err.message || "Failed to load courses list")
      } finally {
        setLoadingCourses(false)
      }
    }
    fetchCourses()
  }, [])

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

  // Centralized submit handler
  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!file) {
      setError("Please select a file")
      return
    }
    if (!selectedCourseId) {
      setError("Please select a course")
      return
    }

    let endpoint = ""
    if (activeTab === "summarize") endpoint = "/api/summarize_upload"
    else if (activeTab === "questions") endpoint = "/api/generate_questions"
    else if (activeTab === "hint") endpoint = "/api/get_hint"
    else return;

    // --- Build FormData ---
    const formData = new FormData()
    formData.append("file", file)
    
    // --- [CRITICAL LINE 2] ---
    // This line sends the ID (e.g., 473) from the state
    formData.append("course_id", selectedCourseId) 
    // -------------------------

    if (activeTab === "hint") {
      if (!question.trim()) {
        setError("Please enter a question")
        return
      }
      formData.append("question", question)
    }

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

      // Handle response structures
      if (activeTab === "summarize") {
        setResult({ type: "summary", data: data })
      } else if (activeTab === "questions") {
        setResult({ type: "questions", data: data.review_questions || [] })
      } else if (activeFtab === "hint") {
        setResult({ type: "hint", data: data.hint || "No hint available" })
      }

    } catch (err) {
      setError(err.message || "Failed to process file")
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="ai-tools-page">
      <h1 className="page-title">AI Learning Tools</h1>

      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      <div className="tools-container">
        <div className="tabs">
          <button
            className={`tab ${activeTab === "summarize" ? "active" : ""}`}
            onClick={() => { setActiveTab("summarize"); setResult(null); }}
          >
            Summarizer
          </button>
          <button
            className={`tab ${activeTab === "questions" ? "active" : ""}`}
            onClick={() => { setActiveTab("questions"); setResult(null); }}
          >
            Question Generator
          </button>
          <button
            className={`tab ${activeTab === "hint" ? "active" : ""}`}
            onClick={() => { setActiveTab("hint"); setResult(null); }}
          >
            Homework Hints
          </button>
        </div>

        <div className="tools-content">
          <div className="tool-panel">
            <Card>
              <form onSubmit={handleSubmit} className="tool-form">
                
                {/* --- Course Selection Dropdown --- */}
                <div className="form-group">
                  <label className="form-label">Select Course</label>
                  {loadingCourses ? (
                    <LoadingSpinner />
                  ) : (
                    <select
                      className="form-input"
                      value={selectedCourseId} // Binds to the state (which holds the ID)
                      onChange={(e) => setSelectedCourseId(e.target.value)} // Updates state with the ID
                      required
                    >
                      <option value="" disabled>-- Select a course --</option>
                      {courses.map((course) => (
                        // --- [CRITICAL LINE 3] ---
                        // The `value` attribute MUST be the ID
                        <option key={course.id} value={course.course_id}>
                          {course.name}
                        </option>
                        // -------------------------
                      ))}
                    </select>
                  )}
                  <p className="file-hint">Select the course this file belongs to.</p>
                </div>

                {/* --- File Upload Group --- */}
                <div className="form-group">
                  <label className="form-label">Upload Document</label>
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
                  <p className="file-hint">Supported: TXT, PDF, DOCX, PPTX</p>
                </div>

                {/* --- Hint Question Textarea --- */}
                {activeTab === "hint" && (
                  <div className="form-group">
                    <label className="form-label">Your Question</label>
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
                   activeTab === "questions" ? "Generate Questions" : "Get Hint"}
                </button>
              </form>
            </Card>
          </div>

          <div className="result-panel">
            {/* ... (Result display logic) ... */}
            {loading ? (
              <LoadingSpinner />
            ) : result ? (
              <Card title={
                  result.type === "summary" ? "Summary" 
                : result.type === "questions" ? "Review Questions" 
                : "Hint"
              }>
                <div className="result-content">
                  
                  {result.type === "summary" && (
                    <div className="summary-list">
                      <strong>Summary:</strong>
                      <ul>
                        {result.data.summary?.map((item, idx) => <li key={idx}>{item}</li>) || <li>No summary.</li>}
                      </ul>
                      <strong>Key Topics:</strong>
                      <ul>
                        {result.data.key_topics?.map((item, idx) => <li key={idx}>{item}</li>) || <li>No topics.</li>}
                      </ul>
                    </div>
                  )}

                  {result.type === "hint" && (
                    <p className="result-text">{result.data}</p>
                  )}
                  
                  {result.type === "questions" && Array.isArray(result.data) ? (
                    <div className="questions-list">
                      {result.data.map((q, idx) => (
                        <div key={idx} className="question-item">
                          <p className="question-text">
                            <strong>Q{idx + 1}:</strong> {q.question}
                          </p>
                          {q.options && (
                            <ul className="options-list">
                              {q.options.map((opt, optIdx) => (
                                <li 
                                  key={optIdx} 
                                  className={opt === q.correct_answer ? 'correct-answer' : ''}
                                >
                                  {opt}
                                </li>
                              ))}
                            </ul>
                          )}
                          <p className="explanation-text">
                            <strong>Explanation:</strong> {q.explanation}
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    result.type === "questions" && <p className="no-data">No questions were generated.</p>
                  )}
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