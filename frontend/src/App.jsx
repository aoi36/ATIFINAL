import React from 'react'
import { useState } from 'react'
import Navigation from './components/Navigation'
import Dashboard from './pages/Dashboard'
import CoursesPage from './pages/CoursesPage'
import SearchPage from './pages/SearchPage'
import AIToolsPage from './pages/AIToolsPage'
import MeetSchedulerPage from './pages/MeetSchedulerPage'
import ScraperPage from './pages/ScraperPage'
import LoginPage from './pages/LoginPage'
import FlashcardsPage from './pages/FlashcardsPage'
import HomeworkSubmitPage from './pages/HomeworkSubmitPage'
import RegisterPage from './pages/RegisterPage'
import CalendarPage from './pages/CalendarPage'
import ChatPage from './pages/ChatPage'
import LearningInsightsPage from './pages/LearningInsightsPage'
import { handleLogout } from './utils/api'
import './App.css'
import CourseDetailPage from './pages/CourseDetailPage'
import StudyPlanPage from './pages/StudyPlanPage'

function App() {
  const [currentPage, setCurrentPage] = useState('dashboard')
  const [selectedCourse, setSelectedCourse] = useState(null)
  const [isLoggedIn, setIsLoggedIn] = useState(localStorage.getItem('authToken') ? true : false)
  const [authPage, setAuthPage] = useState('login')
  const [flashcardParams, setFlashcardParams] = useState(null)
  const [homeworkGraderParams, setHomeworkGraderParams] = useState(null)
  const [homeworkSubmitParams, setHomeworkSubmitParams] = useState(null)
  if (!isLoggedIn) {
    if (authPage === 'login') {
      return (
        <LoginPage
          onLoginSuccess={() => setIsLoggedIn(true)}
          onSwitchToRegister={() => setAuthPage('register')} // <-- 3. Add prop
        />
      )
    } else {
      return (
        <RegisterPage
          onRegisterSuccess={() => setAuthPage('login')} // <-- 4. On success, go to login
          onSwitchToLogin={() => setAuthPage('login')} // <-- 5. Add prop
        />
      )
    }
  }
  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <Dashboard setCurrentPage={setCurrentPage}/>
      case 'courses':
        return <CoursesPage setCurrentPage={setCurrentPage} setSelectedCourse={setSelectedCourse} />
      case 'search':
        return <SearchPage />
      case 'calendar':
        return <CalendarPage />
      case 'tools':
        return (
          <AIToolsPage
            setCurrentPage={setCurrentPage}
            setHomeworkSubmitParams={setHomeworkSubmitParams}
          />
        )
      case 'homework-submit':
        return <HomeworkSubmitPage prefilledFileName={homeworkSubmitParams?.prefilledFileName} />
      case 'flashcards':
        if (flashcardParams) {
          return <FlashcardsPage params={flashcardParams} setCurrentPage={setCurrentPage} />
        }
      case 'chat':
        return <ChatPage />
      case 'study-plan':
        return <StudyPlanPage />
      case 'learning-insights':
        return <LearningInsightsPage />
      case 'course-detail':
        if (selectedCourse) {
          return (
            <CourseDetailPage
              course={selectedCourse}
              setCurrentPage={setCurrentPage}
              setFlashcardParams={setFlashcardParams}
            />
          )
        }
        // --- [THE FIX] ---
        // Add the props to the fallback render
        return <CoursesPage setCurrentPage={setCurrentPage} setSelectedCourse={setSelectedCourse} />
      case 'meet':
        return <MeetSchedulerPage />
      case 'scraper':
        return <ScraperPage />
      default:
        return <Dashboard />
    }
  }

  return (
    <div className="app">
      <Navigation
        currentPage={currentPage}
        setCurrentPage={setCurrentPage}
        onLogout={handleLogout}
      />
      <main className="main-content">{renderPage()}</main>
    </div>
  )
}

export default App