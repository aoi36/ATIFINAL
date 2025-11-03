
import React from "react"
import "./Navigation.css"

function Navigation({ currentPage, setCurrentPage }) {
  const menuItems = [
    { id: "dashboard", label: "Dashboard", icon: "📊" },
    { id: "courses", label: "Courses", icon: "📚" },
    { id: "search", label: "Search", icon: "🔍" },
    { id: "tools", label: "AI Tools", icon: "✨" },
    { id: "meet", label: "Schedule Meet", icon: "📹" },
    { id: "scraper", label: "Scraper", icon: "⚙️" },
  ]

  return (
    <nav className="navigation">
      <div className="nav-header">
        <h1 className="nav-title">LMS Assistant</h1>
      </div>
      <ul className="nav-menu">
        {menuItems.map((item) => (
          <li key={item.id}>
            <button
              className={`nav-button ${currentPage === item.id ? "active" : ""}`}
              onClick={() => setCurrentPage(item.id)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </button>
          </li>
        ))}
      </ul>
    </nav>
  )
}

export default Navigation
