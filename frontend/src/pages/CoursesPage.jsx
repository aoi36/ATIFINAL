import React from 'react'
import { useState, useEffect } from 'react'
import Card from '../components/Card'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorAlert from '../components/ErrorAlert'
import { apiCall } from '../utils/api'
import './CoursesPage.css' // Make sure to create this CSS file for styling

// This component receives 'setCurrentPage' and 'setSelectedCourse' as props from App.jsx
function CoursesPage({ setCurrentPage, setSelectedCourse }) {
  const [courses, setCourses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Fetch the list of courses when the component first loads
  useEffect(() => {
    const fetchCourses = async () => {
      try {
        setLoading(true)
        const data = await apiCall('/api/courses') // Fetches from your API
        setCourses(data || [])
        setError(null)
      } catch (err) {
        setError(err.message || 'Failed to load courses')
      } finally {
        setLoading(false)
      }
    }
    fetchCourses()
  }, []) // The empty array [] means this runs only once

  // This function is called when a user clicks on a course card
  const handleCourseClick = (course) => {
    setSelectedCourse(course) // Sets the selected course in App.jsx
    setCurrentPage('course-detail') // Tells App.jsx to change the page
  }

  return (
    <div className="courses-page">
      <h1 className="page-title">My Courses</h1>

      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      {loading ? (
        <LoadingSpinner />
      ) : (
        // A grid to display the course cards
        <div className="courses-list">
          {courses.length > 0 ? (
            courses.map((course) => (
              <Card
                key={course.id} // Use the course ID from your API
                title={course.name}
                className="course-card" // For styling (e.g., making it look clickable)
                onClick={() => handleCourseClick(course)} // This makes the card clickable
              >
                {/* You can add any other content inside the card here */}
                <p>Course ID: {course.id}</p>

                {/* This link lets the user open the original Moodle page in a new tab */}
                {/* e.stopPropagation() prevents the card's click event from firing */}
                <a
                  href={course.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                >
                  Go to LMS Page
                </a>
              </Card>
            ))
          ) : (
            // Show this if the API returns no courses
            <p className="no-data">No courses found. Run the /api/scrape endpoint first.</p>
          )}
        </div>
      )}
    </div>
  )
}

export default CoursesPage