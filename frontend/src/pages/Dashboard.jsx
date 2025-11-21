// src/pages/Dashboard.jsx

import React, { useState, useEffect } from 'react'
import Card from '../components/Card'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorAlert from '../components/ErrorAlert'
import { apiCall } from '../utils/api'
import './Dashboard.css'

function Dashboard({ setCurrentPage }) { // Accept setCurrentPage prop
  const [courses, setCourses] = useState([])
  const [deadlines, setDeadlines] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        // 1. Fetch Courses
        const coursesData = await apiCall('/api/courses')
        setCourses(coursesData || [])

        // 2. Fetch Deadlines (we need to iterate to get count)
        // This is a bit heavy, but gives us real numbers. 
        // For a real dashboard, you'd want a specific /api/stats endpoint.
        let allDeadlines = []
        for (const course of (coursesData || [])) {
            try {
                const courseDeadlines = await apiCall(`/api/deadlines/${course.id}`)
                allDeadlines = [...allDeadlines, ...courseDeadlines]
            } catch (e) {
                console.warn(`Failed to fetch deadlines for course ${course.id}`)
            }
        }
        setDeadlines(allDeadlines)
        setError(null)

      } catch (err) {
        setError(err.message || 'Failed to load dashboard data')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  // Calculate Stats
  const activeCourses = courses.length
  const upcomingDeadlines = deadlines.filter(d => d.status !== 'Overdue' && !d.is_completed).length
  const overdueDeadlines = deadlines.filter(d => d.status === 'Overdue' && !d.is_completed).length

  // Navigation Helpers
  const goTo = (page) => {
      if (setCurrentPage) setCurrentPage(page);
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1 className="dashboard-title">Welcome to LMS Assistant</h1>
        <p className="dashboard-subtitle">Your personal AI-powered study companion.</p>
      </div>

      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      {loading ? (
        <LoadingSpinner />
      ) : (
        <div className="dashboard-grid">
          
          {/* Stats Section */}
          <div className="stats-section">
            <h2 className="section-title">Overview</h2>
            <div className="stats-content">
              <div className="stat">
                <span className="stat-label">Active Courses</span>
                <span className="stat-value">{activeCourses}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Upcoming Tasks</span>
                <span className="stat-value" style={{color: '#ed8936'}}>{upcomingDeadlines}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Overdue</span>
                <span className="stat-value" style={{color: '#e53e3e'}}>{overdueDeadlines}</span>
              </div>
            </div>
          </div>

          {/* Recent Courses */}
          <div className="courses-preview">
            <h2 className="section-title">Your Courses</h2>
            <div className="courses-grid">
              {courses.length > 0 ? (
                courses.slice(0, 3).map((course) => (
                  <div key={course.id} className="course-card" onClick={() => goTo('courses')}>
                    <h3>{course.name}</h3>
                    <p className="course-description">
                        Click to view course details, files, and deadlines.
                    </p>
                    <span className="course-link">View Course &rarr;</span>
                  </div>
                ))
              ) : (
                <div className="no-data">
                    No courses found. Run the <strong>Scraper</strong> to import your data.
                </div>
              )}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="quick-actions">
            <h2 className="section-title">Quick Actions</h2>
            <div className="actions-grid">
              <div className="card" onClick={() => goTo('search')}>
                <h3>Search Materials</h3>
                <p className="action-description">Find any file or topic instantly.</p>
              </div>
              <div className="card" onClick={() => goTo('tools')}>
                <h3>AI Study Tools</h3>
                <p className="action-description">Summarize, quiz, and grade homework.</p>
              </div>
              <div className="card" onClick={() => goTo('calendar')}>
                <h3>Calendar & Plan</h3>
                <p className="action-description">Sync deadlines and generate study plans.</p>
              </div>
              <div className="card" onClick={() => goTo('meet')}>
                <h3>Meet Scheduler</h3>
                <p className="action-description">Auto-join and record meetings.</p>
              </div>
            </div>
          </div>

        </div>
      )}
    </div>
  )
}

export default Dashboard