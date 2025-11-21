import React, { useState, useEffect } from 'react';
import './FlashcardsPage.css';
import { apiCall } from '../utils/api';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';

function FlashcardsPage({ params, setCurrentPage }) {
  const [flashcards, setFlashcards] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showingAnswer, setShowingAnswer] = useState(false);
  
  // This line is correct
  const { courseId, fileId, flashcardData } = params;

  // --- [FIX #1] ---
  // Use the data passed from the previous page.
  // Only call the API if that data is missing (e.g., on a page refresh).
  useEffect(() => {
    if (flashcardData && flashcardData.length > 0) {
      // 1. Data was already provided, just use it.
      setFlashcards(flashcardData);
      setLoading(false);
    } else {
      // 2. Data is missing, fetch it from the API.
      console.log("No flashcard data passed, fetching from API...");
      loadFlashcards();
    }
  }, [flashcardData, courseId, fileId]); // Depend on the props
  // --- [END FIX #1] ---

  const loadFlashcards = async () => {
    setLoading(true);
    setError('');

    try {
      // --- [FIX #2] ---
      // The API endpoint was plural "courses". It should be singular "course".
      // The 'courseId' variable here IS the 'course_db_id' the API expects.
      const endpoint = `/api/course/${courseId}/files/${encodeURIComponent(fileId)}/flashcards`;
      // --- [END FIX #2] ---
      
      const response = await apiCall(endpoint, { method: 'POST' });
      
      if (response.flashcards && response.flashcards.length > 0) {
        setFlashcards(response.flashcards);
      } else {
        setError('No flashcards generated. The file might not contain suitable content.');
      }
    } catch (err) {
      setError(err.message || 'Failed to generate flashcards');
    } finally {
      setLoading(false);
    }
  };

  const handleFlip = () => {
    setIsFlipped(!isFlipped);
    setShowingAnswer(!showingAnswer);
  };

  const handleNext = () => {
    if (currentIndex < flashcards.length - 1) {
      setCurrentIndex(currentIndex + 1);
      setIsFlipped(false);
      setShowingAnswer(false);
    }
  };

  const handlePrevious = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
      setIsFlipped(false);
      setShowingAnswer(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === ' ') {
      e.preventDefault();
      handleFlip();
    } else if (e.key === 'ArrowRight') {
      handleNext();
    } else if (e.key === 'ArrowLeft') {
      handlePrevious();
    }
  };

  useEffect(() => {
    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [currentIndex, isFlipped, flashcards]); // This is correct

  return (
    <div className="flashcards-page">
      <button onClick={() => setCurrentPage("course-detail")} className="back-button">
        &larr; Back
      </button>

      <div className="flashcards-header">
        <h1>🎴 AI Flashcards</h1>
        <p>Study with AI-generated flashcards for: <strong>{decodeURIComponent(fileId)}</strong></p>
      </div>

      {loading && <LoadingSpinner message="Analyzing document and creating flashcards..." />}
      {error && <ErrorAlert message={error} onClose={() => setError('')} />}

      {flashcards.length > 0 && !loading && (
        <div className="flashcard-viewer">
          <div className="flashcard-progress">
            Card {currentIndex + 1} of {flashcards.length}
          </div>

          {/* We must check that flashcards[currentIndex] exists */}
          {flashcards[currentIndex] && (
            <div
              className={`flashcard ${isFlipped ? 'flipped' : ''}`}
              onClick={handleFlip}
            >
              <div className="flashcard-inner">
                <div className="flashcard-front">
                  <div className="flashcard-category">
                    {flashcards[currentIndex].category}
                  </div>
                  <h2>{flashcards[currentIndex].term}</h2>
                  <p className="flashcard-hint">Click or press Space to reveal</p>
                </div>
                <div className="flashcard-back">
                  <div className="flashcard-category">
                    {flashcards[currentIndex].category}
                  </div>
                  <h3>{flashcards[currentIndex].term}</h3>
                  <p>{flashcards[currentIndex].definition}</p>
                </div>
              </div>
            </div>
          )}

          <div className="flashcard-controls">
            <button
              onClick={handlePrevious}
              disabled={currentIndex === 0}
              className="nav-btn"
            >
              ← Previous
            </button>
            <button onClick={handleFlip} className="flip-btn">
              {showingAnswer ? 'Show Term' : 'Show Definition'}
            </button>
            <button
              onClick={handleNext}
              disabled={currentIndex === flashcards.length - 1}
              className="nav-btn"
            >
              Next →
            </button>
          </div>

          <div className="keyboard-hints">
            <span>Space: Flip</span>
            <span>←→: Navigate</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default FlashcardsPage;