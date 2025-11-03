
import React from "react"
import { useState } from "react"
import Card from "../components/Card"
import ErrorAlert from "../components/ErrorAlert"
import { apiCall } from "../utils/api"
import "./ScraperPage.css"

function ScraperPage() {
  const [status, setStatus] = useState("idle")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const [logs, setLogs] = useState([])

  const addLog = (message) => {
    setLogs((prev) => [...prev, { message, timestamp: new Date().toLocaleTimeString() }])
  }

  const handleScrape = async () => {
    try {
      setLoading(true)
      setError(null)
      setSuccess(null)
      setLogs([])
      setStatus("scraping")

      addLog("Starting LMS scrape...")
      const data = await apiCall("/api/scrape", {
        method: "POST",
        body: JSON.stringify({ action: "start" }),
        headers: { "Content-Type": "application/json" },
      })

      addLog("Scrape completed successfully!")
      setSuccess(`Scraping completed. ${data.message || "All courses updated."}`)
      setStatus("completed")
    } catch (err) {
      addLog(`Error: ${err.message}`)
      setError(err.message || "Failed to start scraping")
      setStatus("error")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="scraper-page">
      <h1 className="page-title">LMS Scraper Control</h1>

      <div className="scraper-container">
        <Card className="control-card">
          <h2 className="card-title">Scrape LMS Content</h2>
          <p className="card-description">
            Trigger a background scraping job to update all course materials and deadlines from your LMS.
          </p>

          {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}
          {success && (
            <div className="success-alert">
              <span className="success-icon">✓</span>
              <p className="success-message">{success}</p>
            </div>
          )}

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

          <button onClick={handleScrape} className="scrape-button" disabled={loading || status === "scraping"}>
            {loading ? "Starting..." : status === "scraping" ? "Scraping..." : "Start Scraping"}
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
        <h2 className="card-title">About the Scraper</h2>
        <div className="info-content">
          <p>The LMS scraper automatically:</p>
          <ul className="info-list">
            <li>Downloads all course materials</li>
            <li>Extracts assignment deadlines</li>
            <li>Indexes content for search</li>
            <li>Updates the local course database</li>
          </ul>
        </div>
      </Card>
    </div>
  )
}

export default ScraperPage
