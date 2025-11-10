// src/pages/CourseDetailPage.jsx

import React, { useState, useEffect } from "react"
import { apiCall } from "../utils/api"
import Card from "../components/Card"
import LoadingSpinner from "../components/LoadingSpinner"
import ErrorAlert from "../components/ErrorAlert"
import "./CourseDetailPage.css"
import QuestionList from "../components/QuestionList"
// import "./CourseDetailPage.css" // You'll want to create this CSS file

function CourseDetailPage({ course, setCurrentPage }) {
  const [deadlines, setDeadlines] = useState([])
  const [files, setFiles] = useState([])
  const [aiContent, setAiContent] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchCourseDetails = async () => {
      
      
      // --- [FIX #1] ---
      // Your API sends 'id', not 'course_id'.
      if (!course || !course.course_id) { 
      // --- [END FIX] ---
        setError("No course selected.");
        setLoading(false);
        return;
      }

      try {
        setLoading(true)
        setError(null)
        
        // --- [FIX #2] ---
        // Use course.course_id in all API calls
        const [deadlinesData, filesData, aiContentData] = await Promise.all([
          apiCall(`/api/deadlines/${course.course_id}`),
          apiCall(`/api/course/${course.course_id}/files`),
          apiCall(`/api/course/${course.course_id}/content`)
        ])
        // --- [END FIX] ---

        setDeadlines(deadlinesData || [])
        setFiles(filesData || [])
        setAiContent(aiContentData || [])
        console.log(aiContentData)
        
      } catch (err) {
        setError(err.message || "Failed to load course details")
      } finally {
        setLoading(false)
      }
    }

    fetchCourseDetails()
  // --- [FIX #3] ---
  // Dependency array must also use course.course_id
  }, [course.course_id]) 
  // --- [END FIX] ---

  const getDisplayFiles = () => {
    const fileSet = new Set(files); // A set of all file names
    const processedFiles = []; // This will be our new list of file objects
    
    // Sort files to process docx/pptx *before* pdf/txt
    const sortedFiles = [...files].sort((a, b) => {
        const aExt = a.split('.').pop().toLowerCase();
        const bExt = b.split('.').pop().toLowerCase();
        // Prioritize docx/pptx
        if (aExt.includes('doc') || aExt.includes('ppt')) return -1;
        if (bExt.includes('doc') || bExt.includes('ppt')) return 1;
        return 0;
    });

    for (const filename of sortedFiles) {
      if (fileSet.has(filename) === false) continue; // Already processed as part of a pair

      const base_name = filename.substring(0, filename.lastIndexOf('.'));
      const ext = filename.substring(filename.lastIndexOf('.')).toLowerCase();

      let fileObj = {
        displayName: decodeURIComponent(filename), // The original name to show
        linkName: filename,    // The file to link to
        isViewable: false, // Can it be opened in the browser?
      };

      if (ext === '.docx' || ext === '.pptx') {
        const pdf_version = `${base_name}.pdf`;
        
        if (fileSet.has(pdf_version)) {
          // Found a PDF conversion!
          fileObj.linkName = pdf_version; // Link to the PDF
          fileObj.isViewable = true;
          fileSet.delete(pdf_version); // Mark the PDF as "handled"
        } else {
          // No PDF, link to original (will download)
          fileObj.isViewable = false;
        }
      } else if (ext === '.pdf' || ext === '.txt') {
        // It's a PDF or TXT, link to itself (is viewable)
        fileObj.isViewable = true;
      }
      // For .zip, .rar, is_viewable remains false

      processedFiles.push(fileObj);
      fileSet.delete(filename); // Mark this file as "handled"
    }
    return processedFiles;
  };
  
  const displayFiles = getDisplayFiles();

  if (loading) return <LoadingSpinner />
  if (error) return <ErrorAlert message={error} onDismiss={() => setError(null)} />

  // Helper to render AI content
  const renderAiContent = (item) => {
    try {
      // --- [FIX] ---
      // 'item.content_json' is ALREADY an object.
      // We just assign it directly.
      const content = item.content_json;
      // --- [END FIX] ---

      if (item.type === 'summary') {
        return (
          <>
            <strong>Summary:</strong>
            {/* Access content.summary directly */}
            <ul>{content.summary?.map((pt, i) => <li key={i}>{pt}</li>) || <li>N/A</li>}</ul>
            <strong>Key Topics:</strong>
            <ul>{content.key_topics?.map((pt, i) => <li key={i}>{pt}</li>) || <li>N/A</li>}</ul>
          </>
        )
      }
      if (item.type === 'questions') {
        return (
          <QuestionList questions={content.review_questions} />
        );
      }
      if (item.type === 'hint') {
        return (
          <>
            <p><strong>Your Question:</strong> {item.user_question}</p>
            {/* Access content.hint directly */}
            <p><strong>Hint:</strong> {content.hint}</p>
          </>
        )
      }
    } catch (e) { 
      console.error("Error rendering AI content:", e, item);
      return <p>Error rendering AI content (see console).</p> 
    }
  }

  return (
    <div className="course-detail-page">
      <button onClick={() => setCurrentPage("courses")} className="back-button">
        &larr; Back to All Courses
      </button>

      <h1 className="page-title">{course.name}</h1>
      
      <Card title="Upcoming Deadlines" className="detail-card">
        {deadlines.length > 0 ? (
          <ul>
            {deadlines.map((d) => (
              <li key={d.id} className={d.status === 'Overdue' ? 'overdue' : 'upcoming'}>
                <strong>{d.status}:</strong> {d.time_string}
                {d.parsed_iso_date && <span> (Due: {new Date(d.parsed_iso_date).toLocaleString()})</span>}
                <a href={d.url} target="_blank" rel="noopener noreferrer"> (Link)</a>
              </li>
            ))}
          </ul>
        ) : <p>No deadlines found for this course.</p>}
      </Card>

      <Card title="Scraped Files" className="detail-card">
        {displayFiles.length > 0 ? (
          <ul className="file-list">
            {displayFiles.map((file, i) => (
              <li key={i}>
                <a 
                   href={`${import.meta.env.VITE_API_URL}/api/get_file/${course.course_id}/${encodeURIComponent(file.linkName)}`}
                   target="_blank" 
                   rel="noopener noreferrer"
                   // This is important:
                   // - If it's viewable (PDF/TXT), 'download' is undefined (so it opens in-tab)
                   // - If it's not viewable (DOCX/ZIP), 'download' is set, forcing a download
                   download={file.isViewable ? undefined : file.displayName}
                >
                  {file.displayName}
                  {/* Add a helpful (Preview) or (Download) tag */}
                  <span className="file-type-badge">
                    {file.isViewable ? " (Preview)" : " (Download)"}
                  </span>
                </a>
              </li>
            ))}
          </ul>
        ) : <p>No files found for this course.</p>}
      </Card>

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