import React, { useState, useEffect } from "react"
import { apiCall, apiFetchFile } from "../utils/api"
import Card from "../components/Card"
import LoadingSpinner from "../components/LoadingSpinner"
import ErrorAlert from "../components/ErrorAlert"
import QuestionList from "../components/QuestionList"
import "./CourseDetailPage.css"

function CourseDetailPage({ course, setCurrentPage, setFlashcardParams }) {
  const [deadlines, setDeadlines] = useState([])
  const [files, setFiles] = useState([])
  const [aiContent, setAiContent] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [previewLoading, setPreviewLoading] = useState(null);
  const [generatingFlashcards, setGeneratingFlashcards] = useState({})

  // Handler for the Flashcard button
  const handleGenerateFlashcards = async (filename) => {
    try {
      setGeneratingFlashcards(prev => ({ ...prev, [filename]: true }))
      
      // Use the secure endpoint with 'course.id'
      const endpoint = `/api/course/${course.id}/files/${encodeURIComponent(filename)}/flashcards`
      
      const data = await apiCall(endpoint, { method: 'POST' })
      
      // Set flashcard params and navigate
      setFlashcardParams({
        courseId: course.id,
        fileId: filename,
        flashcardData: data.flashcards
      })
      setCurrentPage("flashcards")
    } catch (err) {
      setError(`Failed to generate flashcards: ${err.message}`)
    } finally {
      setGeneratingFlashcards(prev => ({ ...prev, [filename]: false }))
    }
  }

  useEffect(() => {
    const fetchCourseDetails = async () => {
      if (!course || !course.id) { 
        setError("No course selected.");
        setLoading(false);
        return;
      }

      try {
        setLoading(true)
        setError(null)
        
        const [deadlinesData, filesData, aiContentData] = await Promise.all([
          apiCall(`/api/deadlines/${course.id}`),
          apiCall(`/api/course/${course.id}/files`),
          apiCall(`/api/course/${course.id}/content`)
        ])

        setDeadlines(deadlinesData || [])
        setFiles(filesData || [])
        setAiContent(aiContentData || [])
        
      } catch (err) {
        setError(err.message || "Failed to load course details")
      } finally {
        setLoading(false)
      }
    }

    fetchCourseDetails()
  }, [course.id]) 

  // Secure file preview handler
  const handleFilePreview = async (filename) => {
    setPreviewLoading(filename); 
    setError(null);
    try {
      const endpoint = `/api/get_file/${course.id}/${encodeURIComponent(filename)}`;
      const blobUrl = await apiFetchFile(endpoint); 
      window.open(blobUrl, '_blank'); 
    } catch (err) {
      setError(err.message || 'Could not open file preview.');
    } finally {
      setPreviewLoading(null); 
    }
  };

  const getDisplayFiles = () => {
    const fileSet = new Set(files);
    const processedFiles = [];
    const sortedFiles = [...files].sort((a, b) => {
        const aExt = a.split('.').pop().toLowerCase();
        const bExt = b.split('.').pop().toLowerCase();
        if (aExt.includes('doc') || aExt.includes('ppt')) return -1;
        if (bExt.includes('doc') || bExt.includes('ppt')) return 1;
        return 0;
    });

    for (const filename of sortedFiles) {
      if (fileSet.has(filename) === false) continue; 

      const base_name = filename.substring(0, filename.lastIndexOf('.'));
      const ext = filename.substring(filename.lastIndexOf('.')).toLowerCase();

      let fileObj = {
        displayName: decodeURIComponent(filename),
        linkName: filename,
        isViewable: false, 
      };

      if (ext === '.docx' || ext === '.pptx') {
        const pdf_version = `${base_name}.pdf`;
        if (fileSet.has(pdf_version)) {
          fileObj.linkName = pdf_version;
          fileObj.isViewable = true;
          fileSet.delete(pdf_version);
        } else {
          fileObj.isViewable = false;
        }
      } else if (ext === '.pdf' || ext === '.txt') {
        fileObj.isViewable = true;
      }
      processedFiles.push(fileObj);
      fileSet.delete(filename);
    }
    return processedFiles;
  };
  
  const displayFiles = getDisplayFiles();

  const renderAiContent = (item) => {
    try {
      const content = item.content_json; 
      if (item.type === 'summary') {
        return (
          <>
            <strong>Summary:</strong>
            <ul>{content.summary?.map((pt, i) => <li key={i}>{pt}</li>) || <li>N/A</li>}</ul>
            <strong>Key Topics:</strong>
            <ul>{content.key_topics?.map((pt, i) => <li key={i}>{pt}</li>) || <li>N/A</li>}</ul>
          </>
        )
      }
      if (item.type === 'questions') {
        return ( <QuestionList questions={content.review_questions} /> );
      }
      if (item.type === 'hint') {
        return (
          <>
            <p><strong>Your Question:</strong> {item.user_question}</p>
            <p><strong>Hint:</strong> {content.hint}</p>
          </>
        )
      }
      if (item.type === 'flashcards') {
        return (
          <div className="flashcard-history-item">
            <p><em>{content.flashcards?.length || 0} cards ready to review.</em></p>
            <button 
              className="view-flashcards-btn"
              onClick={() => {
                 // 1. Load the saved data into the params
                 setFlashcardParams({
                   courseId: course.id,
                   fileId: item.source_file,
                   flashcardData: content.flashcards 
                 })
                 // 2. Navigate to the Flashcards page
                 setCurrentPage("flashcards")
              }}
            >
              Open Flashcards Deck
            </button>
          </div>
        )
      }
    } catch (e) { 
      console.error("Error rendering AI content:", e, item);
      return <p>Error rendering AI content (see console).</p> 
    }
  }

  if (loading) return <LoadingSpinner />
  if (error) return <ErrorAlert message={error} onDismiss={() => setError(null)} />

  return (
    <div className="course-detail-page">
      <button onClick={() => setCurrentPage("courses")} className="back-button">
        &larr; Back to All Courses
      </button>

      <h1 className="page-title">{course.name}</h1>
      
      {/* Deadlines Card */}
      <Card title="Upcoming Deadlines" className="detail-card">
        {deadlines.length > 0 ? (
          <ul className="deadline-list">
            {deadlines.map((d) => (
              <li key={d.id} className={`deadline-item ${d.status === 'Overdue' ? 'overdue' : 'upcoming'}`}>
                <div className="deadline-info">
                    <strong>{d.status}:</strong> {d.time_string}
                    {d.parsed_iso_date && <span> (Due: {new Date(d.parsed_iso_date).toLocaleString()})</span>}
                    <a href={d.url} target="_blank" rel="noopener noreferrer"> (Link)</a>
                </div>
              </li>
            ))}
          </ul>
        ) : <p>No deadlines found for this course.</p>}
      </Card>

      {/* Scraped Files Card */}
      <Card title="Scraped Files" className="detail-card">
        {displayFiles.length > 0 ? (
          <ul className="file-list">
            {displayFiles.map((file, i) => (
              <li key={i} className="file-item">
                <div className="file-info">
                    {file.isViewable ? (
                      <button 
                        className="file-link-button"
                        onClick={() => handleFilePreview(file.linkName)}
                        disabled={previewLoading === file.linkName}
                      >
                        {previewLoading === file.linkName ? 'Loading...' : file.displayName}
                        <span className="file-type-badge"> (Preview)</span>
                      </button>
                    ) : (
                      <a 
                        href={`${import.meta.env.VITE_API_URL}/api/get_file/${course.id}/${encodeURIComponent(file.linkName)}`}
                        target="_blank" 
                        rel="noopener noreferrer"
                        download={file.displayName}
                      >
                        {file.displayName}
                        <span className="file-type-badge"> (Download)</span>
                      </a>
                    )}
                </div>
                
                {/* Flashcard Button */}
                {(file.linkName.endsWith('.pdf') || file.linkName.endsWith('.docx') ||
                  file.linkName.endsWith('.pptx') || file.linkName.endsWith('.txt')) && (
                  <button
                    onClick={() => handleGenerateFlashcards(file.linkName)}
                    disabled={generatingFlashcards[file.linkName]}
                    className="flashcard-button"
                  >
                    {generatingFlashcards[file.linkName] ? '⏳ Generating...' : '📇 Flashcards'}
                  </button>
                )}
              </li>
            ))}
          </ul>
        ) : <p>No files found for this course.</p>}
      </Card>

      {/* AI Content Card */}
      <Card title="Your AI-Generated Content" className="detail-card">
        {aiContent.length > 0 ? (
          <div className="ai-content-list">
            {aiContent.map((item) => (
              <div key={item.id} className="ai-content-item">
                <h4>{item.type.toUpperCase()} for "{item.source_file}"</h4>
                <p><em>(Generated on {new Date(item.created_at).toLocaleString()})</em></p>
                <div className="ai-content-body">
                  {renderAiContent(item)}
                </div>
              </div>
            ))}
          </div>
        ) : <p>No summaries, questions, or hints generated for this course yet.</p>}
      </Card>
    </div>
  )
}

export default CourseDetailPage