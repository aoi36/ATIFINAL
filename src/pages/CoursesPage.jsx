
import React from "react"
import { useState, useEffect } from "react"
import Card from "../components/Card"
import LoadingSpinner from "../components/LoadingSpinner"
import ErrorAlert from "../components/ErrorAlert"
import { apiCall } from "../utils/api"
import "./CoursesPage.css"

function CoursesPage() {
  const [courses, setCourses] = useState([])
  const [selectedCourse, setSelectedCourse] = useState(null)
  const [deadlines, setDeadlines] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadingDeadlines, setLoadingDeadlines] = useState(false)
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

  const fetchDeadlines = async (courseId) => {
    try {
      setLoadingDeadlines(true)
      const data = await apiCall(`/api/deadlines/${courseId}`)
      setDeadlines(data || [])
    } catch (err) {
      setError(err.message || "Failed to load deadlines")
    } finally {
      setLoadingDeadlines(false)
    }
  }

  const handleSelectCourse = (course) => {
    setSelectedCourse(course)
    fetchDeadlines(course.id)
  }

  return (
    <div className="courses-page">
      <h1 className="page-title">Courses</h1>

      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      <div className="courses-container">
        <div className="courses-list">
          <h2 className="section-title">All Courses</h2>
          {loading ? (
            <LoadingSpinner />
          ) : courses.length > 0 ? (
            <div className="course-items">
              {courses.map((course) => (
                <div
                  key={course.id}
                  className={`course-item ${selectedCourse?.id === course.id ? "active" : ""}`}
                  onClick={() => handleSelectCourse(course)}
                >
                  <span className="course-name">{course.name}</span>
                  <span className="course-code">{course.code || "N/A"}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="no-data">No courses found</p>
          )}
        </div>

        <div className="course-details">
          {selectedCourse ? (
            <>
              <h2 className="section-title">{selectedCourse.name}</h2>
              <Card title="Course Information">
                <div className="info-grid">
                  <div className="info-item">
                    <span className="info-label">Course Code</span>
                    <span className="info-value">{selectedCourse.code || "N/A"}</span>
                  </div>
                  <div className="info-item">
                    <span className="info-label">Instructor</span>
                    <span className="info-value">{selectedCourse.instructor || "Unknown"}</span>
                  </div>
                </div>
              </Card>

              <div className="deadlines-section">
                <h3 className="section-title">Upcoming Deadlines</h3>
                {loadingDeadlines ? (
                  <LoadingSpinner />
                ) : deadlines.length > 0 ? (
                  <div className="deadline-items">
                    {deadlines.map((deadline, idx) => (
                      <Card key={idx} className="deadline-card">
                        <div className="deadline-header">
                          <span className="deadline-name">{deadline.name || "Assignment"}</span>
                          <span
                            className={`deadline-badge ${new Date(deadline.date) < new Date() ? "overdue" : "upcoming"}`}
                          >
                            {new Date(deadline.date) < new Date() ? "Overdue" : "Upcoming"}
                          </span>
                        </div>
                        <p className="deadline-date">{new Date(deadline.date).toLocaleDateString()}</p>
                      </Card>
                    ))}
                  </div>
                ) : (
                  <p className="no-data">No deadlines for this course</p>
                )}
              </div>
            </>
          ) : (
            <div className="placeholder">
              <p>Select a course to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default CoursesPage
