// src/pages/ScraperPage.jsx

import React, { useState, useEffect } from "react"
import Card from "../components/Card"
import LoadingSpinner from "../components/LoadingSpinner"
import ErrorAlert from "../components/ErrorAlert"
import { apiCall } from "../utils/api"
import "./ScraperPage.css"

function ScraperPage() {
  const [status, setStatus] = useState("idle")
  const [loading, setLoading] = useState(false) // This is for the main "Start" button
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const [logs, setLogs] = useState([])

  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")

  const addLog = (message) => {
    setLogs((prev) => [{ message, timestamp: new Date().toLocaleTimeString() }, ...prev])
  }

  // --- [FIXED] Polling logic using useEffect ---
  useEffect(() => {
    let intervalId = null;

    const pollStatus = async () => {
      try {
        // 1. Get status AND result
        const data = await apiCall("/api/scrape/status", { method: "GET" });

        if (data.status === "idle") {
          // The backend says it's done. Now check if it succeeded or failed.
          
          if (data.result && data.result.success === false) {
             // --- [CASE 1: FAILED] ---
             addLog(`❌ Scrape Failed: ${data.result.message}`);
             setError(`Scrape Failed: ${data.result.message}`); // Show red alert
             setStatus("error");
          } else {
             // --- [CASE 2: SUCCESS] ---
             // (Or if result is null, we assume it just finished cleanly)
             addLog("✅ Backend scrape completed successfully!");
             setSuccess("Scraping completed. All courses and files updated.");
             setStatus("completed");
          }
          
          setLoading(false);
          if (intervalId) clearInterval(intervalId); // Stop polling
        } 
        // If data.status is "scraping", we do nothing and loop again.
        
      } catch (err) {
        addLog(`Error polling status: ${err.message}`);
        setError("Failed to check scrape status.");
        setStatus("error");
        setLoading(false);
        if (intervalId) clearInterval(intervalId);
      }
    };

    if (status === "scraping") {
      setLoading(true);
      intervalId = setInterval(pollStatus, 3000); // Poll every 3 seconds
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [status]);

  // --- [FIXED] handleScrape only *starts* the job ---
  const handleScrape = async () => {
    if (!username.trim() || !password.trim()) {
      setError("Please enter your LMS Username and Password.")
      return
    }
    
    setLoading(true); // Show spinner on button
    setError(null);
    setSuccess(null);
    setLogs([]);
    addLog("Sending scrape request to backend...");

    try {
      // Call the API *once* to start the job
      const data = await apiCall("/api/scrape", {
        method: "POST",
        body: {
          username: username,
          password: password
        },
        headers: { "Content-Type": "application/json" },
        isFormData: false 
      });

      addLog(`Backend responded: ${data.status}`);
      // --- [THE FIX] ---
      // NOW set the status to "scraping"
      // This will trigger the useEffect hook to start polling
      setStatus("scraping");
      // --- [END FIX] ---
      
    } catch (err) {
      // This catches an error if the *initial* POST request fails
      addLog(`Scrape request failed: ${err.message}`);
      setError(err.message || "Failed to start scraping");
      setStatus("error"); // Set status to error
      setLoading(false); // Stop loading on initial failure
    }
    // We don't set loading=false in a finally block here
    // The poller will set it to false when the job is done
  }

  return (
    <div className="scraper-page">
      <h1 className="page-title">LMS Scraper Control</h1>

      <div className="scraper-container">
        <Card className="control-card">
          <h2 className="card-title">Scrape LMS Content</h2>
          <p className="card-description">
            Enter your LMS credentials to update all course materials and deadlines.
          </p>

          {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}
          {success && (
            <div className="success-alert">
              {/* ... (success alert JSX) ... */}
            </div>
          )}

          {/* --- Input Fields --- */}
          <div className="form-group">
            <label className="form-label">LMS Username</label>
            <input
              type="text"
              className="form-input"
              placeholder="Your LMS Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={status === "scraping"}
            />
          </div>
          <div className="form-group">
            <label className="form-label">LMS Password</label>
            <input
              type="password"
              className="form-input"
              placeholder="Your LMS Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={status === "scraping"}
            />
          </div>
          
          <div className="status-box">
            <p className="status-label">Status:</p>
            <span className={`status-badge ${status}`}>
              {status === "idle"
                ? "⏸️ Idle"
                : status === "scraping"
                  ? "🔄 Scraping..."
                  : status === "completed"
                    ? "✓ Completed"
                    : status === "error"
                      ? "✗ Error"
                      : status}
            </span>
          </div>

          <button onClick={handleScrape} className="scrape-button" disabled={loading}>
            {/* [FIX] Button is only disabled by 'loading' (click/initial request) 
                or 'status' (polling) */}
            {status === "scraping" ? "Scraping..." : "Start Full Scrape"}
          </button>
        </Card>

        <Card className="logs-card">
          <h2 className="card-title">Activity Log</h2>
          <div className="logs-container">
            {logs.length > 0 ? (
              logs.map((log, idx) => ( 
                <div key={idx} className="log-entry">
                  <span className="log-time">{log.timestamp}</span>
                  <span className="log-message">{log.message}</span>
                </div>
              ))
            ) : (
              <p className="logs-empty">No activity yet. Start scraping to see logs.</p>
            )}
          </div>
        </Card>
      </div>

      <Card className="info-card">
        {/* ... (Info card content is fine) ... */}
      </Card>
    </div>
  )
}

export default ScraperPage