// src/pages/HomeworkSubmitPage.jsx

import React, { useState, useEffect } from "react";
// [FIX] Use your secure apiCall and the new file fetcher
import { apiCall, apiFetchFile } from "../utils/api"; 
import Card from "../components/Card";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorAlert from "../components/ErrorAlert";
import "./HomeworkSubmitPage.css"; 

function HomeworkSubmitPage({ prefilledFileName = null }) {
  const [selectedDeadlineId, setSelectedDeadlineId] = useState("");
  
  // Get username from localStorage to show the user
  const [lms_username] = useState(
    JSON.parse(localStorage.getItem('currentUser'))?.lms_username || ""
  );
  const [password, setPassword] = useState("");
  const [file, setFile] = useState(null); // This will hold the file object
  
  const [assignments, setAssignments] = useState([]);
  const [loadingAssignments, setLoadingAssignments] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  // Fetch assignments on mount
  useEffect(() => {
    const fetchAssignments = async () => {
      try {
        setLoadingAssignments(true);
        const data = await apiCall("/api/assignments/all"); // Calls secure endpoint
        setAssignments(data || []);
      } catch (err) {
        setError(err.message || "Failed to load assignments.");
      } finally {
        setLoadingAssignments(false);
      }
    };
    fetchAssignments();
  }, []);

  // --- [FIX] ---
  // This effect now securely fetches the pre-filled file
  useEffect(() => {
    if (prefilledFileName) {
      const fetchPrefilledFile = async () => {
        setLoading(true);
        setError(null);
        try {
          // 1. Call the new, secure endpoint
          const blobUrl = await apiFetchFile(
            `/api/homework/get_temp_file/${prefilledFileName}`
          );
          // 2. Convert the blob URL back into a File object
          const response = await fetch(blobUrl);
          const blob = await response.blob();
          const prefilledFile = new File([blob], prefilledFileName, { type: blob.type });
          setFile(prefilledFile); // 3. Set the file in state
          setResult({ success: true, message: "AI Graded file has been pre-filled!" });
        } catch (err) {
          setError(err.message || "Failed to load pre-filled file.");
        } finally {
          setLoading(false);
        }
      };
      fetchPrefilledFile();
    }
  }, [prefilledFileName]);
  // --- [END FIX] ---

  const handleFileChange = (e) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setError(null);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!selectedDeadlineId) {
      setError("Please select an assignment."); return;
    }
    if (!lms_username) { // This should be pre-filled from state
       setError("Username is missing. Please log in again."); return;
    }
    if (!password) {
      setError("Please enter your LMS password."); return;
    }
    if (!file) {
      setError("Please select a file to submit."); return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("deadline_id", selectedDeadlineId);
      formData.append("lms_username", lms_username); // Send correct username
      formData.append("lms_password", password);
      formData.append("file", file);

      // Use secure apiCall
      const data = await apiCall("/api/homework/submit", {
        method: "POST",
        body: formData,
        isFormData: true,
      });

      if (data.status) {
        setResult({ success: true, message: data.status });
        setSelectedDeadlineId("");
        setPassword("");
        setFile(null);
        if (document.getElementById("file-input")) {
          document.getElementById("file-input").value = "";
        }
      } else {
        setError(data.error || "Failed to submit homework");
      }
    } catch (err) {
      setError(err.message || "Failed to submit homework.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="homework-submit-page">
      <h1 className="page-title">Auto Submit Homework</h1>
      <p className="description">
        Submit your homework to the LMS. The agent will log in, navigate,
        upload your file, and submit it for you.
      </p>

      <Card>
        <form onSubmit={handleSubmit} className="homework-form">
          <div className="form-group">
            <label htmlFor="assignment-select">
              Assignment <span className="required">*</span>
            </label>
            {loadingAssignments ? (
              <LoadingSpinner />
            ) : (
              <select
                id="assignment-select"
                value={selectedDeadlineId}
                onChange={(e) => setSelectedDeadlineId(e.target.value)}
                disabled={loading}
                required
              >
                <option value="" disabled>-- Select an assignment --</option>
                {assignments.map((assignment) => (
                  <option key={assignment.id} value={assignment.id}>
                    {assignment.course_name} - {assignment.time_string}
                  </option>
                ))}
              </select>
            )}
          </div>
          
          <div className="form-group">
            <label htmlFor="username">
              LMS Username <span className="required">*</span>
            </label>
            <input
              type="text"
              id="username"
              value={lms_username} // Pre-filled from localStorage
              onChange={(e) => setLmsUsername(e.target.value)}
              disabled={loading}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">
              LMS Password <span className="required">*</span>
            </label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Your LMS password"
              disabled={loading}
              required
            />
            <small className="help-text security-note">
              🔒 Your credentials are required for this submission only.
            </small>
          </div>

          <div className="form-group">
            <label>
              Homework File <span className="required">*</span>
            </label>
            <div className="file-input-wrapper">
              <input
                type="file"
                id="file-input"
                className="file-input"
                onChange={handleFileChange}
                disabled={loading || !!prefilledFileName} // Disable if pre-filled
                required={!file}
              />
              <label
                htmlFor="file-input"
                className={`file-label ${file ? "has-file" : ""} ${!!prefilledFileName ? "disabled" : ""}`}
              >
                {file ? (
                  <>
                    <span style={{ fontSize: '1.5rem', display: 'block', marginBottom: '0.5rem' }}>📄</span>
                    {file.name}
                  </>
                ) : (
                  <>
                    <span style={{ fontSize: '1.5rem', display: 'block', marginBottom: '0.5rem' }}>📂</span>
                    Choose Homework File
                  </>
                )}
              </label>
            </div>
            {prefilledFileName && (
              <small className="help-text">
                Using AI-graded file. To change, go back to AI Tools.
              </small>
            )}
          </div>

          {error && <ErrorAlert message={error} />}
          {result && result.success && (
            <div className="success-alert">
              <strong>✓ Success!</strong> {result.message}
            </div>
          )}

          <button
            type="submit"
            className="submit-button"
            disabled={loading || loadingAssignments}
          >
            {loading ? "Submitting..." : "Submit Homework"}
          </button>
        </form>
      </Card>
      
      {/* ... (Your loading/info cards are fine) ... */}
    </div>
  );
}

export default HomeworkSubmitPage;