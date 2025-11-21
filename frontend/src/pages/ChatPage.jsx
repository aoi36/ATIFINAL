// src/pages/ChatPage.jsx

import React, { useState, useEffect, useRef } from "react"
import LoadingSpinner from "../components/LoadingSpinner"
import ErrorAlert from "../components/ErrorAlert"
import { apiCall } from "../utils/api"
import "./ChatPage.css"

function ChatPage() {
  const [messages, setMessages] = useState([])
  const [selectedTool, setSelectedTool] = useState("search")
  const [currentProvider, setCurrentProvider] = useState("github") // Changed default to github
  const [messageInput, setMessageInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [menuOpen, setMenuOpen] = useState(false)
  const [conversationId, setConversationId] = useState(null)
  const [courses, setCourses] = useState([])
  const [selectedCourse, setSelectedCourse] = useState(null)
  const [providers, setProviders] = useState({})
  const [loadingCourses, setLoadingCourses] = useState(true)
  
  const messagesEndRef = useRef(null)
  const textareaRef = useRef(null)

  const tools = [
    {
      id: "search",
      name: "Search Materials",
      icon: "🔍",
      description: "Find course content"
    },
    {
      id: "summarize",
      name: "Summarize Document",
      icon: "📄",
      description: "AI-powered summaries"
    },
    {
      id: "questions",
      name: "Generate Questions",
      icon: "❓",
      description: "Create practice MCQs"
    },
    {
      id: "homework",
      name: "Get Homework Help",
      icon: "⚡",
      description: "Hints for assignments"
    }
  ]

  // Provider labels mapping - UPDATED with GitHub
  const providerLabels = {
    github: "GitHub (GPT-4o)", // NEW!
    gemini: "Gemini 2.5 Pro",
    claude: "Claude 3.5",
    chatgpt: "ChatGPT 4"
  }

  // Provider descriptions for better UX
  const providerDescriptions = {
    github: "Free GPT-4o via GitHub Models",
    gemini: "Fast and efficient",
    claude: "Best for analysis",
    chatgpt: "Versatile and balanced"
  }

  // Fetch available AI providers and courses on mount
  useEffect(() => {
    fetchProviders()
    fetchCourses()
  }, [])

  const fetchProviders = async () => {
    try {
      const data = await apiCall('/api/chat/providers')
      setProviders(data)
      
      // Prioritize GitHub if available, then others
      const providerPriority = ['github', 'gemini', 'claude', 'chatgpt']
      const availableProvider = providerPriority.find(key => data[key]?.available)
      
      if (availableProvider) {
        setCurrentProvider(availableProvider)
      }
    } catch (err) {
      console.error("Failed to fetch providers:", err)
      // Don't show error to user - providers will just show as unavailable
    }
  }

  const fetchCourses = async () => {
    try {
      const data = await apiCall('/api/courses')
      setCourses(data)
    } catch (err) {
      console.error("Failed to fetch courses:", err)
      setError("Failed to load courses")
    } finally {
      setLoadingCourses(false)
    }
  }

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + "px"
    }
  }, [messageInput])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, loading])

  const handleSendMessage = async (e) => {
    e.preventDefault()
    
    if (!messageInput.trim() || loading) return

    // Check if provider is available
    if (providers[currentProvider] && !providers[currentProvider].available) {
      setError(`${providerLabels[currentProvider]} is not configured. Please select another provider.`)
      return
    }

    const userMessage = {
      id: Date.now().toString(),
      content: messageInput,
      role: "user",
      timestamp: new Date().toLocaleTimeString()
    }

    setMessages(prev => [...prev, userMessage])
    const currentInput = messageInput
    setMessageInput("")
    setLoading(true)
    setError(null)

    try {
      const data = await apiCall('/api/chat/message', {
        method: 'POST',
        body: {
          message: currentInput,
          conversation_id: conversationId,
          ai_provider: currentProvider, // Will send 'github' when selected
          course_id: selectedCourse
        }
      })

      // Set conversation ID if this was a new conversation
      if (!conversationId && data.conversation_id) {
        setConversationId(data.conversation_id)
      }

      const assistantMessage = {
        id: (Date.now() + 1).toString(),
        content: data.response,
        role: "assistant",
        timestamp: new Date().toLocaleTimeString(),
        token_count: data.token_count
      }

      setMessages(prev => [...prev, assistantMessage])
      
    } catch (err) {
      console.error("Chat error:", err)
      setError(err.message || "Failed to send message. Please try again.")
      
      // Remove the user message if sending failed
      setMessages(prev => prev.filter(msg => msg.id !== userMessage.id))
      setMessageInput(currentInput) // Restore the message
      
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage(e)
    }
  }

  const handleNewConversation = () => {
    setConversationId(null)
    setMessages([])
    setError(null)
  }

  const currentToolName = tools.find(t => t.id === selectedTool)?.name || "Select Tool"
  const currentProviderLabel = providerLabels[currentProvider] || "Select AI"

  return (
    <div className="chat-page">
      <h1 className="page-title">AI Chat Assistant</h1>

      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      <div className="chat-layout">
        <div className="chat-sidebar">
          <h3 className="sidebar-title">Tools</h3>
          <div className="tools-list">
            {tools.map(tool => (
              <button
                key={tool.id}
                onClick={() => setSelectedTool(tool.id)}
                className={`tool-button ${selectedTool === tool.id ? "active" : ""}`}
              >
                <span className="tool-icon">{tool.icon}</span>
                <div className="tool-details">
                  <p className="tool-name">{tool.name}</p>
                  <p className="tool-desc">{tool.description}</p>
                </div>
              </button>
            ))}
          </div>

          {/* Course Selection */}
          {!loadingCourses && courses.length > 0 && (
            <>
              <h3 className="sidebar-title" style={{ marginTop: '1.5rem' }}>Course Context</h3>
              <select 
                value={selectedCourse || ""} 
                onChange={(e) => setSelectedCourse(e.target.value ? parseInt(e.target.value) : null)}
                className="course-select"
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  borderRadius: '0.5rem',
                  border: '1px solid var(--border)',
                  backgroundColor: 'var(--background)',
                  color: 'var(--text-primary)',
                  fontSize: '0.9rem',
                  cursor: 'pointer'
                }}
              >
                <option value="">No course context</option>
                {courses.map(course => (
                  <option key={course.id} value={course.id}>
                    {course.name}
                  </option>
                ))}
              </select>
            </>
          )}

          {/* New Conversation Button */}
          {conversationId && (
            <button
              onClick={handleNewConversation}
              style={{
                marginTop: '1rem',
                width: '100%',
                padding: '0.75rem',
                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                border: '1px solid var(--primary)',
                borderRadius: '0.5rem',
                color: 'var(--primary)',
                fontSize: '0.9rem',
                fontWeight: '600',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
              onMouseOver={(e) => e.target.style.backgroundColor = 'rgba(99, 102, 241, 0.2)'}
              onMouseOut={(e) => e.target.style.backgroundColor = 'rgba(99, 102, 241, 0.1)'}
            >
              + New Conversation
            </button>
          )}
        </div>

        <div className="chat-main-area">
          <div className="chat-header">
            <h2>{currentToolName}</h2>
            <p className="chat-header-desc">
              Chat with your AI study assistant
              {selectedCourse && courses.find(c => c.id === selectedCourse) && (
                <span style={{ color: 'var(--primary)', marginLeft: '0.5rem' }}>
                  • {courses.find(c => c.id === selectedCourse).name}
                </span>
              )}
            </p>
          </div>

          <div className="messages-container">
            {messages.length === 0 ? (
              <div className="chat-welcome">
                <p className="welcome-emoji">👋</p>
                <h3>Welcome to AI Chat Assistant</h3>
                <p>Powered by {currentProviderLabel} - Start asking questions!</p>
                <ul className="quick-tips">
                  <li>📚 Search course materials instantly</li>
                  <li>📝 Get document summaries</li>
                  <li>❓ Generate practice questions</li>
                  <li>💡 Get homework help</li>
                </ul>
                {courses.length > 0 && (
                  <p style={{ marginTop: '1rem', color: 'var(--text-muted)' }}>
                    💡 Tip: Select a course for context-aware responses
                  </p>
                )}
              </div>
            ) : (
              messages.map(msg => (
                <div key={msg.id} className={`message ${msg.role}`}>
                  <div className="message-bubble">
                    <p className="message-content">{msg.content}</p>
                    <span className="message-time">
                      {msg.timestamp}
                      {msg.token_count && (
                        <span style={{ marginLeft: '0.5rem', opacity: 0.6 }}>
                          • {msg.token_count} tokens
                        </span>
                      )}
                    </span>
                  </div>
                </div>
              ))
            )}
            {loading && (
              <div className="message assistant">
                <div className="message-bubble">
                  <LoadingSpinner />
                  <p style={{ marginTop: '0.5rem', fontSize: '0.85rem', opacity: 0.7 }}>
                    {currentProviderLabel} is thinking...
                  </p>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <form onSubmit={handleSendMessage} className="chat-input-form">
            <div className="input-wrapper">
              <textarea
                ref={textareaRef}
                value={messageInput}
                onChange={e => setMessageInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask anything about your courses..."
                className="message-input"
                rows="1"
                disabled={loading}
              />
              
              <div className="input-controls">
                <div className="provider-dropdown">
                  <button
                    type="button"
                    onClick={() => setMenuOpen(!menuOpen)}
                    className="provider-badge"
                    disabled={loading}
                  >
                    {currentProviderLabel}
                    {providers[currentProvider] && !providers[currentProvider].available && (
                      <span style={{ marginLeft: '0.25rem', fontSize: '0.75rem' }}>⚠️</span>
                    )}
                  </button>
                  
                  {menuOpen && (
                    <div className="provider-menu">
                      {/* GitHub first - it's FREE! */}
                      {providerLabels.github && (
                        <button
                          type="button"
                          onClick={() => {
                            setCurrentProvider('github')
                            setMenuOpen(false)
                          }}
                          className={`provider-option ${currentProvider === 'github' ? "active" : ""}`}
                          disabled={providers.github && !providers.github.available}
                        >
                          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
                            <span style={{ fontWeight: '600' }}>
                              {providerLabels.github}
                              {currentProvider === 'github' && <span style={{ marginLeft: '0.5rem' }}>✓</span>}
                            </span>
                            <span style={{ fontSize: '0.75rem', opacity: 0.7, marginTop: '0.15rem' }}>
                              {providers.github && providers.github.available ? 
                                '🆓 Free GPT-4o' : 
                                '(Not configured)'
                              }
                            </span>
                          </div>
                        </button>
                      )}
                      
                      {/* Divider */}
                      {providerLabels.github && (
                        <div style={{ 
                          height: '1px', 
                          backgroundColor: 'var(--border)', 
                          margin: '0.5rem 0' 
                        }} />
                      )}
                      
                      {/* Other providers */}
                      {Object.entries(providerLabels)
                        .filter(([id]) => id !== 'github')
                        .map(([id, label]) => (
                          <button
                            key={id}
                            type="button"
                            onClick={() => {
                              setCurrentProvider(id)
                              setMenuOpen(false)
                            }}
                            className={`provider-option ${currentProvider === id ? "active" : ""}`}
                            disabled={providers[id] && !providers[id].available}
                          >
                            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
                              <span style={{ fontWeight: '600' }}>
                                {label}
                                {currentProvider === id && <span style={{ marginLeft: '0.5rem' }}>✓</span>}
                              </span>
                              <span style={{ fontSize: '0.75rem', opacity: 0.7, marginTop: '0.15rem' }}>
                                {providers[id] && !providers[id].available ? 
                                  '(Not configured)' : 
                                  providerDescriptions[id]
                                }
                              </span>
                            </div>
                          </button>
                        ))}
                    </div>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={loading || !messageInput.trim()}
                  className="send-button"
                >
                  ➤
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

export default ChatPage