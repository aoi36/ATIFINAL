import React from 'react'
import './Navigation.css'

function Navigation({ currentPage, setCurrentPage, onLogout }) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'courses', label: 'Courses' },
    { id: 'search', label: 'Search' },
    { id: 'tools', label: 'AI Tools' },
    { id: 'chat', label: 'Chat' },
    { id: 'meet', label: 'Meet Scheduler' },
    { id: 'scraper', label: 'Scraper' },
    { id: 'calendar', label: 'Calendar' },
    { id: 'study-plan', label: 'Study Plan' },
    { id: 'learning-insights', label: 'Learning Insights' },
  ]

  return (
    <nav className="navigation">
      <div className="nav-header">
        <h1 className="nav-title">LMS Agent</h1>
      </div>
      <ul className="nav-menu">
        {navItems.map((item) => (
          <li key={item.id}>
            <button
              className={`nav-button ${currentPage === item.id ? 'active' : ''}`}
              onClick={() => setCurrentPage(item.id)}
            >
              <span className="nav-icon">
                {item.id === 'dashboard' && '📊'}
                {item.id === 'courses' && '📚'}
                {item.id === 'search' && '🔍'}
                {item.id === 'tools' && '⚙️'}
                {item.id === 'chat' && '💬'}
                {item.id === 'meet' && '📞'}
                {item.id === 'scraper' && '📑'}
                {item.id === 'calendar' && '📅'}
                {item.id === 'study-plan' && '📋'}
                {item.id === 'learning-insights' && '📈'}
              </span>
              {item.label}
            </button>
          </li>
        ))}
      </ul>
      <div className="nav-logout">
        <button className="logout-button" onClick={onLogout}>
          Logout
        </button>
      </div>
    </nav>
  )
}

export default Navigation