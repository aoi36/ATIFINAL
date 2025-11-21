import React, { useState, useEffect } from 'react'
import Card from '../components/Card'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorAlert from '../components/ErrorAlert'
import { apiCall } from '../utils/api'
import './LearningInsightsPage.css'

function LearningInsightsPage() {
  const [activeTab, setActiveTab] = useState('progress') // progress, habits, weekly, recommendations
  const [courses, setCourses] = useState([])
  const [selectedCourse, setSelectedCourse] = useState(null)
  const [dashboard, setDashboard] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchInitialData()
  }, [])

  const fetchInitialData = async () => {
    try {
      setLoading(true)
      // Fetch courses and dashboard in parallel
      const [coursesData, dashboardData] = await Promise.all([
        apiCall('/api/courses'),
        apiCall('/api/insights/dashboard'),
      ])

      console.log('[DEBUG] Courses:', coursesData)
      console.log('[DEBUG] Dashboard Response:', dashboardData)

      setCourses(coursesData || [])

      // Extract dashboard from response - backend wraps it in { success, dashboard }
      const dashboardContent = dashboardData?.dashboard || dashboardData || null
      console.log('[DEBUG] Extracted Dashboard:', dashboardContent)
      setDashboard(dashboardContent)

      // Don't auto-select first course - let user pick "All Courses" or a specific one
      // setSelectedCourse remains null initially to show "All Courses"

      setError(null)
    } catch (err) {
      console.error('[ERROR]', err)
      setError(err.message || 'Failed to load learning insights')
    } finally {
      setLoading(false)
    }
  }

  const refreshDashboard = async () => {
    try {
      const data = await apiCall('/api/insights/dashboard')
      console.log('[DEBUG] Refresh Dashboard Response:', data)
      const dashboardContent = data?.dashboard || data || null
      console.log('[DEBUG] Refresh Extracted Dashboard:', dashboardContent)
      setDashboard(dashboardContent)
    } catch (err) {
      console.error('Failed to refresh dashboard:', err)
    }
  }

  if (loading) return <LoadingSpinner />

  return (
    <div className="learning-insights-page">
      <div className="insights-header">
        <h1>Learning Insights & Analytics</h1>
        <p>Track your progress, analyze learning habits, and get personalized recommendations</p>
      </div>

      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      {/* Course Selector */}
      {courses.length > 0 && (
        <div className="course-selector">
          <label>Select Course:</label>
          <select
            value={selectedCourse?.id || ''}
            onChange={(e) => {
              if (e.target.value === '') {
                setSelectedCourse(null) // null means "All Courses"
              } else {
                const course = courses.find((c) => c.id == e.target.value)
                setSelectedCourse(course)
              }
            }}
          >
            <option value="">All Courses</option>
            {courses.map((course) => (
              <option key={course.id} value={course.id}>
                {course.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="insights-tabs">
        <button
          className={`tab-btn ${activeTab === 'progress' ? 'active' : ''}`}
          onClick={() => setActiveTab('progress')}
        >
          Progress
        </button>
        {/* <button
          className={`tab-btn ${activeTab === 'habits' ? 'active' : ''}`}
          onClick={() => setActiveTab('habits')}
        >
          Learning Habits
        </button>
        <button
          className={`tab-btn ${activeTab === 'weekly' ? 'active' : ''}`}
          onClick={() => setActiveTab('weekly')}
        >
          Weekly Trends
        </button> */}
        <button
          className={`tab-btn ${activeTab === 'recommendations' ? 'active' : ''}`}
          onClick={() => setActiveTab('recommendations')}
        >
          Recommendations
        </button>
      </div>

      {/* Tab Content */}
      <div className="insights-content">
        {activeTab === 'progress' && (
          <ProgressSection
            dashboard={dashboard}
            selectedCourse={selectedCourse}
            onRefresh={refreshDashboard}
          />
        )}

        {activeTab === 'habits' && (
          <HabitsSection dashboard={dashboard} onRefresh={refreshDashboard} />
        )}

        {activeTab === 'weekly' && (
          <WeeklySection selectedCourse={selectedCourse} onRefresh={refreshDashboard} />
        )}

        {activeTab === 'recommendations' && (
          <RecommendationsSection dashboard={dashboard} onRefresh={refreshDashboard} />
        )}
      </div>
    </div>
  )
}

// Progress Section Component
function ProgressSection({ dashboard, selectedCourse, onRefresh }) {
  const [updating, setUpdating] = useState(false)
  const [newProgress, setNewProgress] = useState({ completed: '', total: '' })

  const handleUpdateProgress = async () => {
    console.log('[DEBUG] handleUpdateProgress called')
    console.log('[DEBUG] selectedCourse:', selectedCourse)
    console.log('[DEBUG] newProgress:', newProgress)

    if (!selectedCourse) {
      console.log('[DEBUG] No course selected')
      alert('Please select a specific course first (not "All Courses")')
      return
    }

    const completed = parseInt(newProgress.completed)
    const total = parseInt(newProgress.total)

    console.log('[DEBUG] Parsed values - completed:', completed, 'total:', total)
    console.log(
      '[DEBUG] NaN check - completed isNaN:',
      isNaN(completed),
      'total isNaN:',
      isNaN(total)
    )

    if (isNaN(completed) || isNaN(total)) {
      console.log('[DEBUG] Invalid number format')
      alert('Please enter valid numbers for both fields')
      return
    }

    if (completed < 0 || total <= 0) {
      console.log('[DEBUG] Range validation failed')
      alert('Completed topics must be >= 0 and total must be > 0')
      return
    }

    if (completed > total) {
      console.log('[DEBUG] Completed exceeds total')
      alert('Completed topics cannot exceed total topics')
      return
    }

    try {
      setUpdating(true)
      const payload = {
        course_db_id: selectedCourse.id,
        completed_topics: completed,
        total_topics: total,
      }
      console.log('[DEBUG] Sending payload:', payload)

      const result = await apiCall('/api/insights/progress/update', {
        method: 'POST',
        body: payload,
      })

      console.log('[DEBUG] Update result:', result)

      if (result.success) {
        console.log('[DEBUG] Update successful, clearing form and refreshing')
        setNewProgress({ completed: '', total: '' })
        await onRefresh()
        alert('✅ Progress updated successfully!')
      } else {
        console.log('[DEBUG] Update returned error:', result.error)
        alert(`❌ Update failed: ${result.error}`)
      }
    } catch (err) {
      console.error('[DEBUG] Exception during update:', err)
      alert(`❌ Error: ${err.message}`)
    } finally {
      setUpdating(false)
    }
  }

  const progress = dashboard?.progress || []
  const selectedProgress = selectedCourse
    ? progress.find((p) => p.course_db_id === selectedCourse.id)
    : null // null means show all courses

  // When "All Courses" is selected, show all progress
  const displayProgress = selectedProgress ? [selectedProgress] : progress

  return (
    <div className="section-content">
      {/* When "All Courses" is selected - show grid of all courses */}
      {!selectedCourse ? (
        <>
          {displayProgress.length > 0 ? (
            <div className="progress-grid">
              {displayProgress.map((prog) => (
                <Card
                  key={prog.id || prog.course_db_id}
                  title={prog.course_name || 'Progress'}
                  className="card-large"
                >
                  <div className="progress-display">
                    <div className="progress-stat">
                      <span className="label">Completed Topics</span>
                      <span className="value">
                        {prog.completed_topics} / {prog.total_topics}
                      </span>
                    </div>

                    <div className="progress-bar-container">
                      <div
                        className={`progress-bar ${
                          prog.is_behind_schedule ? 'behind' : 'on-track'
                        }`}
                        style={{ width: `${Math.min(prog.progress_percentage, 100)}%` }}
                      />
                    </div>

                    <div className="progress-percentage">
                      {Math.min(prog.progress_percentage, 100).toFixed(1)}% Complete
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            <Card title="Current Progress" className="card-large">
              <p className="no-data">No progress data. Select a course and update your progress.</p>
            </Card>
          )}
        </>
      ) : (
        /* When a specific course is selected - show 2 column layout */
        <div className="grid-2">
          {/* LEFT: Progress Card */}
          <Card title="Current Progress" className="card-large">
            {selectedProgress ? (
              <div className="progress-display">
                <div className="progress-stat">
                  <span className="label">Completed Topics</span>
                  <span className="value">
                    {selectedProgress.completed_topics} / {selectedProgress.total_topics}
                  </span>
                </div>

                <div className="progress-bar-container">
                  <div
                    className={`progress-bar ${
                      selectedProgress.is_behind_schedule ? 'behind' : 'on-track'
                    }`}
                    style={{ width: `${Math.min(selectedProgress.progress_percentage, 100)}%` }}
                  />
                </div>

                <div className="progress-percentage">
                  {Math.min(selectedProgress.progress_percentage, 100).toFixed(1)}% Complete
                </div>
              </div>
            ) : (
              <p className="no-data">No progress data yet. Update below to get started.</p>
            )}
          </Card>

          {/* RIGHT: Update Progress Form */}
          <Card title="Update Progress" className="card-large">
            <div className="form-group">
              <label>📊 Completed Topics:</label>
              <input
                type="number"
                min="0"
                value={newProgress.completed}
                onChange={(e) => setNewProgress({ ...newProgress, completed: e.target.value })}
                placeholder="Enter number of topics completed"
              />
            </div>

            <div className="form-group">
              <label>📚 Total Topics:</label>
              <input
                type="number"
                min="1"
                value={newProgress.total}
                onChange={(e) => setNewProgress({ ...newProgress, total: e.target.value })}
                placeholder="Enter total number of topics"
              />
            </div>

            <button className="btn-primary" onClick={handleUpdateProgress} disabled={updating}>
              {updating ? 'Updating...' : 'Update Progress'}
            </button>
          </Card>
        </div>
      )}

      {/* Alerts */}
      {dashboard?.alerts && dashboard.alerts.length > 0 && (
        <Card title="Alerts" className="alerts-card">
          <div className="alerts-list">
            {dashboard.alerts.map((alert, idx) => (
              <div key={idx} className={`alert-item severity-${alert.severity}`}>
                <span className="course-name">{alert.course}</span>
                <span className="alert-message">{alert.message}</span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}

// Learning Habits Section
function HabitsSection({ dashboard, onRefresh }) {
  const [loading, setLoading] = useState(false)
  const [showSessionForm, setShowSessionForm] = useState(false)
  const [sessionForm, setSessionForm] = useState({
    course_db_id: '',
    session_date: new Date().toISOString().split('T')[0],
    start_time: '09:00',
    end_time: '10:00',
    topics_studied: '',
    content_type: 'video',
    difficulty_level: 'medium',
    focus_score: 75,
  })

  // Extract analysis from response structure
  // Backend returns { success, analysis, recommendations }
  const analysis = dashboard?.habits?.analysis || dashboard?.analysis
  const recommendations = dashboard?.habits?.recommendations || dashboard?.recommendations

  const handleRefreshHabits = async () => {
    setLoading(true)
    try {
      const result = await apiCall('/api/insights/habits', { method: 'GET' })
      console.log('[DEBUG] Habits result:', result)

      if (result.success) {
        alert('✅ Analysis updated successfully!')
        onRefresh()
      } else {
        alert(`⚠️ ${result.message || 'Unable to analyze habits. Log more study sessions first.'}`)
      }
    } catch (err) {
      alert(`❌ Error: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleLogSession = async () => {
    if (!sessionForm.course_db_id) {
      alert('Please select a course')
      return
    }

    if (!sessionForm.topics_studied.trim()) {
      alert('Please enter topics studied')
      return
    }

    try {
      setLoading(true)
      const startTime = sessionForm.start_time + ':00'
      const endTime = sessionForm.end_time + ':00'

      const payload = {
        course_db_id: parseInt(sessionForm.course_db_id),
        session_date: sessionForm.session_date,
        start_time: startTime,
        end_time: endTime,
        topics_studied: sessionForm.topics_studied,
        content_type: sessionForm.content_type,
        difficulty_level: sessionForm.difficulty_level,
        focus_score: parseFloat(sessionForm.focus_score),
      }

      console.log('[DEBUG] Logging session:', payload)

      const result = await apiCall('/api/insights/session/log', {
        method: 'POST',
        body: payload,
      })

      console.log('[DEBUG] Session logged:', result)

      if (result.success) {
        alert('✅ Study session logged successfully!')
        setSessionForm({
          course_db_id: '',
          session_date: new Date().toISOString().split('T')[0],
          start_time: '09:00',
          end_time: '10:00',
          topics_studied: '',
          content_type: 'video',
          difficulty_level: 'medium',
          focus_score: 75,
        })
        setShowSessionForm(false)
        await onRefresh()

        // Automatically trigger analysis after logging session
        setTimeout(() => {
          handleRefreshHabits()
        }, 500)
      } else {
        alert(`❌ Error: ${result.error}`)
      }
    } catch (err) {
      console.error('[DEBUG] Error logging session:', err)
      alert(`❌ Error: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  if (!analysis) {
    return (
      <div className="section-content">
        <div className="grid-2">
          <Card title="Learning Habits">
            <p className="no-data">
              Not enough data. Log some study sessions to analyze your habits.
            </p>
            <button
              className="btn-primary"
              onClick={() => setShowSessionForm(!showSessionForm)}
              disabled={loading}
            >
              {showSessionForm ? '✕ Cancel' : '📝 Log Study Session'}
            </button>
          </Card>

          {showSessionForm && (
            <Card title="New Study Session" className="card-form">
              <div className="form-group">
                <label>📚 Course:</label>
                <select
                  value={sessionForm.course_db_id}
                  onChange={(e) => setSessionForm({ ...sessionForm, course_db_id: e.target.value })}
                  className="form-input"
                >
                  <option value="">Select a course</option>
                  {dashboard?.courses?.map((course) => (
                    <option key={course.id} value={course.id}>
                      {course.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>📅 Date:</label>
                <input
                  type="date"
                  value={sessionForm.session_date}
                  onChange={(e) => setSessionForm({ ...sessionForm, session_date: e.target.value })}
                  className="form-input"
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>⏰ Start:</label>
                  <input
                    type="time"
                    value={sessionForm.start_time}
                    onChange={(e) => setSessionForm({ ...sessionForm, start_time: e.target.value })}
                    className="form-input"
                  />
                </div>
                <div className="form-group">
                  <label>⏰ End:</label>
                  <input
                    type="time"
                    value={sessionForm.end_time}
                    onChange={(e) => setSessionForm({ ...sessionForm, end_time: e.target.value })}
                    className="form-input"
                  />
                </div>
              </div>

              <div className="form-group">
                <label>📖 Topics:</label>
                <input
                  type="text"
                  value={sessionForm.topics_studied}
                  onChange={(e) =>
                    setSessionForm({ ...sessionForm, topics_studied: e.target.value })
                  }
                  placeholder="e.g., Arrays, Linked Lists"
                  className="form-input"
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>🎬 Type:</label>
                  <select
                    value={sessionForm.content_type}
                    onChange={(e) =>
                      setSessionForm({ ...sessionForm, content_type: e.target.value })
                    }
                    className="form-input"
                  >
                    <option value="video">Video</option>
                    <option value="reading">Reading</option>
                    <option value="practice">Practice</option>
                    <option value="quiz">Quiz</option>
                    <option value="mixed">Mixed</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>🎯 Difficulty:</label>
                  <select
                    value={sessionForm.difficulty_level}
                    onChange={(e) =>
                      setSessionForm({ ...sessionForm, difficulty_level: e.target.value })
                    }
                    className="form-input"
                  >
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label>🧠 Focus (0-100):</label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={sessionForm.focus_score}
                  onChange={(e) => setSessionForm({ ...sessionForm, focus_score: e.target.value })}
                  className="form-range"
                />
                <span className="focus-value">{sessionForm.focus_score}/100</span>
              </div>

              <button className="btn-primary" onClick={handleLogSession} disabled={loading}>
                {loading ? 'Logging...' : '✅ Log Session'}
              </button>
            </Card>
          )}
        </div>

        <div style={{ marginTop: '20px', textAlign: 'center' }}>
          <button className="btn-primary" onClick={handleRefreshHabits} disabled={loading}>
            {loading ? 'Analyzing...' : '🔄 Try Analyzing Now'}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="section-content">
      <div className="grid-2">
        <Card title="Peak Study Times">
          <div className="habit-stat">
            <span className="habit-label">Peak Study Hour</span>
            <span className="habit-value">{analysis.peak_study_hour}</span>
          </div>

          <div className="habit-stat">
            <span className="habit-label">Most Productive Day</span>
            <span className="habit-value">{analysis.most_productive_day}</span>
          </div>

          <div className="habit-stat">
            <span className="habit-label">Optimal Session Duration</span>
            <span className="habit-value">{analysis.average_session_duration_minutes} min</span>
          </div>
        </Card>

        <Card title="Study Metrics">
          <div className="habit-stat">
            <span className="habit-label">Daily Study Hours</span>
            <span className="habit-value">{analysis.average_daily_study_hours}</span>
          </div>

          <div className="habit-stat">
            <span className="habit-label">Focus Score</span>
            <span className="habit-value">{analysis.average_focus_score}</span>
          </div>

          <div className="habit-stat">
            <span className="habit-label">Total Sessions (30d)</span>
            <span className="habit-value">{analysis.total_sessions_30days}</span>
          </div>
        </Card>
      </div>

      {/* Recommendations */}
      {recommendations && recommendations.length > 0 && (
        <Card title="Personalized Tips">
          <ul className="recommendations-list">
            {recommendations.map((rec, idx) => (
              <li key={idx}>{rec}</li>
            ))}
          </ul>
        </Card>
      )}

      <button className="btn-primary" onClick={handleRefreshHabits} disabled={loading}>
        {loading ? 'Refreshing...' : 'Refresh Analysis'}
      </button>
    </div>
  )
}

// Weekly Trends Section
function WeeklySection({ selectedCourse, onRefresh }) {
  const [weeklyData, setWeeklyData] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (selectedCourse) {
      fetchWeeklyData()
    } else {
      setWeeklyData(null)
    }
  }, [selectedCourse])

  const fetchWeeklyData = async () => {
    try {
      setLoading(true)
      const data = await apiCall(`/api/insights/weekly/compare/${selectedCourse.id}`)
      setWeeklyData(data)
    } catch (err) {
      console.error('Error fetching weekly data:', err)
    } finally {
      setLoading(false)
    }
  }

  if (!selectedCourse) {
    return (
      <div className="section-content">
        <Card title="Weekly Trends">
          <p className="no-data">
            ℹ️ Weekly Trends are only available when you select a specific course.
            <br />
            Please select a course from the dropdown above.
          </p>
        </Card>
      </div>
    )
  }

  if (loading) return <LoadingSpinner />

  if (!weeklyData?.trends) {
    return (
      <div className="section-content">
        <Card title="Weekly Trends">
          <p className="no-data">No weekly data available yet. Log study sessions to see trends.</p>
        </Card>
      </div>
    )
  }

  const { trends, insights } = weeklyData

  return (
    <div className="section-content">
      <Card title="Weekly Comparison">
        <div className="grid-3">
          <div className="trend-card">
            <h4>Study Hours</h4>
            {trends.study_hours_trend && trends.study_hours_trend.length > 0 && (
              <div className="trend-sparkline">
                {trends.study_hours_trend.map((val, i) => (
                  <div
                    key={i}
                    className="trend-bar"
                    style={{
                      height: `${Math.max(
                        20,
                        (val / Math.max(...trends.study_hours_trend)) * 100
                      )}%`,
                    }}
                    title={`Week ${i + 1}: ${val.toFixed(1)}h`}
                  />
                ))}
              </div>
            )}
            <p className="trend-label">
              {trends.study_hours_trend &&
                trends.study_hours_trend[trends.study_hours_trend.length - 1]?.toFixed(1)}
              h this week
            </p>
          </div>

          <div className="trend-card">
            <h4>Quiz Scores</h4>
            {trends.quiz_score_trend && trends.quiz_score_trend.length > 0 && (
              <div className="trend-sparkline">
                {trends.quiz_score_trend.map((val, i) => (
                  <div
                    key={i}
                    className="trend-bar"
                    style={{ height: `${Math.max(20, val)}%` }}
                    title={`Week ${i + 1}: ${val.toFixed(0)}%`}
                  />
                ))}
              </div>
            )}
            <p className="trend-label">
              {trends.quiz_score_trend &&
                trends.quiz_score_trend[trends.quiz_score_trend.length - 1]?.toFixed(0)}
              % average
            </p>
          </div>

          <div className="trend-card">
            <h4>Topics Completed</h4>
            {trends.topics_completed_trend && trends.topics_completed_trend.length > 0 && (
              <div className="trend-sparkline">
                {trends.topics_completed_trend.map((val, i) => (
                  <div
                    key={i}
                    className="trend-bar"
                    style={{
                      height: `${Math.max(
                        20,
                        (val / Math.max(...trends.topics_completed_trend)) * 100
                      )}%`,
                    }}
                    title={`Week ${i + 1}: ${val} topics`}
                  />
                ))}
              </div>
            )}
            <p className="trend-label">
              {trends.topics_completed_trend &&
                trends.topics_completed_trend[trends.topics_completed_trend.length - 1]}{' '}
              this week
            </p>
          </div>
        </div>
      </Card>

      {/* Insights */}
      {insights && insights.length > 0 && (
        <Card title="Insights">
          <ul className="insights-list">
            {insights.map((insight, idx) => (
              <li key={idx}>{insight}</li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  )
}

// Recommendations Section
function RecommendationsSection({ dashboard, onRefresh }) {
  const [generating, setGenerating] = useState(false)
  const recommendations = dashboard?.recommendations || []

  console.log('[DEBUG] Recommendations:', recommendations)

  const handleGenerateRecommendations = async () => {
    try {
      setGenerating(true)
      const result = await apiCall('/api/insights/recommendations/generate', {
        method: 'POST',
      })
      console.log('[DEBUG] Generate result:', result)
      onRefresh()
      alert('Recommendations generated successfully!')
    } catch (err) {
      alert(`Error: ${err.message}`)
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="section-content">
      <button className="btn-primary" onClick={handleGenerateRecommendations} disabled={generating}>
        {generating ? 'Generating...' : 'Generate New Recommendations'}
      </button>

      {recommendations.length > 0 ? (
        <div className="recommendations-grid">
          {recommendations.map((rec) => (
            <Card key={rec.id} title={rec.title} className="recommendation-card">
              <div className="recommendation-content">
                <p>{rec.description}</p>
                <div className="recommendation-meta">
                  <span className={`priority-badge priority-${rec.priority}`}>
                    {rec.priority.toUpperCase()}
                  </span>
                  <span className="created-date">
                    {rec.created_at ? new Date(rec.created_at).toLocaleDateString() : 'Recently'}
                  </span>
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <Card title="No Recommendations Yet">
          <p className="no-data">
            Generate recommendations to get personalized learning suggestions.
          </p>
        </Card>
      )}
    </div>
  )
}

export default LearningInsightsPage