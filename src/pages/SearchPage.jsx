
import React from "react"
import { useState } from "react"
import Card from "../components/Card"
import LoadingSpinner from "../components/LoadingSpinner"
import ErrorAlert from "../components/ErrorAlert"
import { apiCall } from "../utils/api"
import "./SearchPage.css"

function SearchPage() {
  const [query, setQuery] = useState("")
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [searched, setSearched] = useState(false)

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!query.trim()) {
      setError("Please enter a search query")
      return
    }

    try {
      setLoading(true)
      setError(null)
      const data = await apiCall(`/api/search?q=${encodeURIComponent(query)}`)
      setResults(data || [])
      setSearched(true)
    } catch (err) {
      setError(err.message || "Search failed")
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="search-page">
      <h1 className="page-title">Search Course Materials</h1>

      <Card className="search-card">
        <form onSubmit={handleSearch} className="search-form">
          <input
            type="text"
            className="search-input"
            placeholder="Search across all your course materials..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button type="submit" className="search-button" disabled={loading}>
            {loading ? "Searching..." : "Search"}
          </button>
        </form>
      </Card>

      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      <div className="results-section">
        {loading ? (
          <LoadingSpinner />
        ) : searched ? (
          results.length > 0 ? (
            <>
              <h2 className="results-title">
                Found {results.length} result{results.length !== 1 ? "s" : ""}
              </h2>
              <div className="results-grid">
{results.map((result, idx) => (
  <Card key={idx} title={decodeURIComponent(result.file_name || "Result")} className="result-card">
    <div className="result-content">
      
      {/* Use `dangerouslySetInnerHTML` to render the <strong> tags 
        from the snippet as bold text.
      */}
      <p 
        className="result-text" 
        dangerouslySetInnerHTML={{ __html: (result.snippet || "No preview available").replace(/\n/g, '<br />') }}
      />
      
      <div className="result-meta">
        {/* Use result.course_name for the source */}
        <span className="result-source">{result.course_name || "Unknown source"}</span>
        {/* result.score is correct */}
        {result.score && <span className="result-score">Match: {Math.round(result.score * 100)}%</span>}
      </div>
    </div>
  </Card>
))}
              </div>
            </>
          ) : (
            <div className="no-results">
              <p className="no-results-text">No results found for "{query}"</p>
              <p className="no-results-hint">Try different search terms</p>
            </div>
          )
        ) : (
          <div className="search-placeholder">
            <p>Enter a search query to find course materials</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default SearchPage
