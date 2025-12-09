import React, { useState, useEffect } from 'react';
import './QuestionPage.css';
import { API_URL, fetchAPI } from '../config';

function QuestionPage({ dayNumber, quizData, playerData, isHost, onBack }) {
  const [question, setQuestion] = useState(null);
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [showResult, setShowResult] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    const fetchQuestion = async () => {
      try {
        const response = await fetchAPI(`${API_URL}/api/questions/${dayNumber}`);
        if (!response.ok) {
          throw new Error('Question not found');
        }
        const data = await response.json();
        setQuestion(data);
      } catch (error) {
        console.error('Error fetching question:', error);
        alert('Failed to load question. This question may not be set up yet.');
      } finally {
        setLoading(false);
      }
    };

    fetchQuestion();
  }, [dayNumber]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!answer.trim()) {
      alert('Please enter an answer');
      return;
    }

    setSubmitting(true);
    try {
      const response = await fetchAPI(
        `${API_URL}/api/questions/${dayNumber}/answer`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            player_id: playerData.player_id || playerData.id,
            quiz_id: quizData.quiz_id || playerData.quiz_id,
            answer: answer
          }),
        }
      );
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to submit answer');
      }
      
      const data = await response.json();
      setResult(data);
      setShowResult(true);
    } catch (error) {
      console.error('Error submitting answer:', error);
      alert(error.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = () => {
    onBack();
  };

  if (loading) {
    return (
      <div className="question-page-container">
        <div className="question-content-wrapper">
          <div className="loading">Loading question...</div>
        </div>
      </div>
    );
  }

  if (!question) {
    return (
      <div className="question-page-container">
        <div className="question-content-wrapper">
          <div className="error">Question not found</div>
          <button onClick={onBack} className="back-button">Back to Calendar</button>
        </div>
      </div>
    );
  }

  const imageCount = question.images.length;

  return (
    <div className="question-page-container">
      {showResult && (
        <div className="result-popup">
          <div className="result-content">
            <div className={`result-icon ${result.is_correct ? 'correct' : 'incorrect'}`}>
              {result.is_correct ? '🎉' : '❌'}
            </div>
            <h2>{result.is_correct ? 'Correct!' : 'Incorrect'}</h2>
            {!result.is_correct && (
              <p className="correct-answer">
                The correct answer was: <strong>{result.correct_answer}</strong>
              </p>
            )}
            <p className="points">Points earned: <strong>{result.points_earned}</strong></p>
            <p className="total-score">Total score: <strong>{result.total_score}</strong></p>
            <button onClick={handleClose} className="close-button">
              Back to Calendar
            </button>
          </div>
        </div>
      )}

      <div className="question-content-wrapper">
        <button onClick={onBack} className="back-button">← Back to Calendar</button>
        
        <div className="question-header">
          <h1>Day {dayNumber}</h1>
          {isHost ? (
            <p className="player-info host-badge">👑 HOST (View Only)</p>
          ) : (
            <p className="player-info">{playerData.username}</p>
          )}
        </div>

        <div className="question-main">
          <h2 className="question-text">{question.question_text}</h2>

          {imageCount > 0 && (
            <div className={`image-grid grid-${imageCount}`}>
              {question.images.map((image, index) => (
                <div key={index} className="image-slot">
                  <img src={image} alt={`Question visual ${index + 1}`} />
                </div>
              ))}
            </div>
          )}

          {isHost ? (
            <div className="host-view-only">
              <p className="host-message">
                🎅 <strong>Host View</strong> - You can see the question but cannot submit an answer.
              </p>
              <div className="question-preview">
                <p><strong>Question:</strong> {question.question_text}</p>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="answer-form">
              <label htmlFor="answer">Your Answer:</label>
              <input
                type="text"
                id="answer"
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="Type your answer here..."
                disabled={submitting}
                autoFocus
              />
              <button type="submit" disabled={submitting || !answer.trim()}>
                {submitting ? 'Submitting...' : 'Submit Answer'}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

export default QuestionPage;
