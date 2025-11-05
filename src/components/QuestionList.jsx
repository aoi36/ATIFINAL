// src/components/QuestionList.jsx

import React, { useState } from 'react';

// --- Configuration ---
// The number of questions to show by default
const INITIAL_SHOW_COUNT = 3; 
// ---------------------

function QuestionList({ questions }) {
  // State to track if the list is expanded or not
  const [isExpanded, setIsExpanded] = useState(false);

  if (!questions || questions.length === 0) {
    return <p className="no-data">No questions were generated for this file.</p>;
  }

  // Determine which questions to display based on the state
  const questionsToShow = isExpanded ? questions : questions.slice(0, INITIAL_SHOW_COUNT);

  // Function to flip the state
  const toggleExpand = () => {
    setIsExpanded(!isExpanded);
  };

  return (
    <div className="questions-list">
      {questionsToShow.map((q, idx) => (
        // We use the original question object 'q' to find its real index, 
        // so numbering stays correct (e.g., 1, 2, 3, 4...)
        <div key={idx} className="question-item">
          <p className="question-text">
            <strong>Q{questions.indexOf(q) + 1}:</strong> {q.question}
          </p>
          {q.options && (
            <ul className="options-list">
              {q.options.map((opt, optIdx) => (
                <li 
                  key={optIdx} 
                  className={opt === q.correct_answer ? 'correct-answer' : ''}
                >
                  {opt}
                </li>
              ))}
            </ul>
          )}
          <p className="explanation-text">
            <strong>Explanation:</strong> {q.explanation}
          </p>
        </div>
      ))}

      {/* --- The "View More" Button --- */}
      {/* Only show this button if there are more questions than the initial count */}
      {questions.length > INITIAL_SHOW_COUNT && (
        <button onClick={toggleExpand} className="toggle-questions-button">
          {isExpanded ? 'Show Less' : `Show More (${questions.length - INITIAL_SHOW_COUNT} remaining)`}
        </button>
      )}
    </div>
  );
}

export default QuestionList;