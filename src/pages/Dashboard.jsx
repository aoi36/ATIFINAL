
import React from "react"
import { useState, useEffect } from "react"
import Card from "../components/Card"
import LoadingSpinner from "../components/LoadingSpinner"
import ErrorAlert from "../components/ErrorAlert"
import { apiCall } from "../utils/api"
import "./Dashboard.css"

function Dashboard() {
  const [courses, setCourses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchCourses()
  }, [])

  const fetchCourses = async () => {
    try {
      setLoading(true)
      const data = await apiCall("/api/courses")
      setCourses(data || [])
      setError(null)
    } catch (err) {
      setError(err.message || "Failed to load courses")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1 className="dashboard-title">Welcome to LMS Assistant</h1>
        <p className="dashboard-subtitle">Manage your courses and access AI-powered study tools</p>
      </div>

      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      {loading ? (
        <LoadingSpinner />
      ) : (
        <div className="dashboard-grid">
          <div className="stats-section">
            <Card title="Quick Stats">
              <div className="stats-content">
                <div className="stat">
                  <span className="stat-label">Active Courses</span>
                  <span className="stat-value">{courses.length}</span>
                </div>
              </div>
            </Card>
          </div>

          <div className="courses-preview">
            <h2 className="section-title">Recent Courses</h2>
            <div className="courses-grid">
              {courses.length > 0 ? (
                courses.slice(0, 6).map((course) => (
                  <Card key={course.id} title={course.name} className="course-card">
                    <p className="course-description">{course.description || "No description"}</p>
                  </Card>
                ))
              ) : (
                <p className="no-data">No courses available yet</p>
              )}
            </div>
          </div>

          <div className="quick-actions">
            <h2 className="section-title">Quick Actions</h2>
            <div className="actions-grid">
              <Card title="Search Materials" subtitle="Find course content">
                <p className="action-description">Search across all your course materials</p>
              </Card>
              <Card title="Summarize Document" subtitle="AI-powered summaries">
                <p className="action-description">Upload files and get instant summaries</p>
              </Card>
              <Card title="Generate Questions" subtitle="Practice with MCQs">
                <p className="action-description">Create practice questions from your materials</p>
              </Card>
              <Card title="Get Homework Help" subtitle="Smart hints for assignments">
                <p className="action-description">Receive guidance without spoiling answers</p>
              </Card>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Dashboard
