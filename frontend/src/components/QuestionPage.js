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
  const [imageUrls, setImageUrls] = useState([]);
  const [playerStatus, setPlayerStatus] = useState([]);

  useEffect(() => {
    const fetchQuestion = async () => {
      try {
        const quizId = quizData.quiz_id || playerData.quiz_id;
        const response = await fetchAPI(`${API_URL}/api/questions/${dayNumber}?quiz_id=${quizId}`);
        if (!response.ok) {
          throw new Error('Question not found');
        }
        const data = await response.json();
        setQuestion(data);
        
        // Fetch images as blobs to add ngrok header
        if (data.images && data.images.length > 0) {
          const imageBlobs = await Promise.all(
            data.images.map(async (imageUrl) => {
              try {
                const response = await fetchAPI(imageUrl);
                const blob = await response.blob();
                return URL.createObjectURL(blob);
              } catch (error) {
                console.error('Failed to load image:', imageUrl, error);
                return null;
              }
            })
          );
          setImageUrls(imageBlobs.filter(url => url !== null));
        }
      } catch (error) {
        console.error('Error fetching question:', error);
        alert('Failed to load question. This question may not be set up yet.');
      } finally {
        setLoading(false);
      }
    };

    fetchQuestion();
    
    // Cleanup blob URLs on unmount
    return () => {
      imageUrls.forEach(url => {
        if (url) URL.revokeObjectURL(url);
      });
    };
  }, [dayNumber]);

  // Separate useEffect for player status polling (host only)
  useEffect(() => {
    if (!isHost || !quizData?.quiz_id) return;

    const fetchPlayerStatus = async () => {
      try {
        const response = await fetchAPI(`${API_URL}/api/quiz/${quizData.quiz_id}/players`);
        if (response.ok) {
          const data = await response.json();
          // Check which players have answered this day
          const statusPromises = data.players.map(async (player) => {
            const answerResponse = await fetchAPI(
              `${API_URL}/api/quiz/${quizData.quiz_id}/player/${player.player_id}/answer/${dayNumber}`
            );
            const hasAnswered = answerResponse.ok;
            return {
              name: player.player_name,
              hasAnswered
            };
          });
          const statuses = await Promise.all(statusPromises);
          setPlayerStatus(statuses);
        }
      } catch (error) {
        console.error('Error fetching player status:', error);
      }
    };

    // Fetch immediately
    fetchPlayerStatus();
    
    // Then poll every 3 seconds
    const interval = setInterval(fetchPlayerStatus, 3000);
    
    return () => clearInterval(interval);
  }, [isHost, quizData, dayNumber]);

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
      setSubmitting(false); // Clear submitting state immediately
      setResult(data);
      setShowResult(true);
    } catch (error) {
      console.error('Error submitting answer:', error);
      alert(error.message);
      setSubmitting(false); // Also clear on error
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

  const imageCount = imageUrls.length;

  return (
    <div className="question-page-container">
      {/* Snowflakes overlay */}
      <div className="snow-overlay"></div>
      
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
        </div>

        <div className="question-main">
          <h2 className="question-text">{question.question_text}</h2>

          {imageCount > 0 && (
            <div className={`image-grid grid-${imageCount}`}>
              {imageUrls.map((imageUrl, index) => (
                <div key={index} className="image-slot">
                  <img 
                    src={imageUrl} 
                    alt={`Question visual ${index + 1}`}
                    onError={(e) => {
                      console.error(`Failed to load image at index ${index}`);
                      e.target.style.display = 'none';
                    }}
                    onLoad={() => console.log(`Image ${index + 1} loaded successfully`)}
                  />
                </div>
              ))}
            </div>
          )}

          {isHost ? (
            <div className="host-view-only">
              <div className="player-status-section">
                <h3>Player Answers Status</h3>
                <div className="player-status-summary">
                  {playerStatus.filter(p => p.hasAnswered).length} / {playerStatus.length} players have answered
                </div>
                <div className="player-status-list">
                  {playerStatus.map((player, index) => (
                    <div key={index} className={`player-status-item ${player.hasAnswered ? 'answered' : 'pending'}`}>
                      <span className="player-name">{player.name}</span>
                      <span className="status-icon">
                        {player.hasAnswered ? '✅' : '⏳'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="answer-form">
              <input
                type="text"
                id="answer"
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="Type your answer here..."
                disabled={submitting}
                autoFocus
              />
              <button type="submit" disabled={submitting || !answer.trim()} className={submitting ? 'checking' : ''}>
                {submitting ? (
                  <>
                    <span className="spinner"></span>
                    Submitting...
                  </>
                ) : (
                  'Submit Answer'
                )}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

export default QuestionPage;
