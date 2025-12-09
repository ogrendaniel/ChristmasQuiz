import React, { useState, useEffect } from 'react';
import './QuizHistory.css';
import { API_URL, fetchAuthAPI } from '../config';

function QuizHistory({ onBack }) {
  const [quizzes, setQuizzes] = useState([]);
  const [selectedQuiz, setSelectedQuiz] = useState(null);
  const [quizResults, setQuizResults] = useState(null);
  const [expandedPlayer, setExpandedPlayer] = useState(null);
  const [playerAnswers, setPlayerAnswers] = useState({});
  const [editingScore, setEditingScore] = useState(null);
  const [editingAnswer, setEditingAnswer] = useState(null);
  const [tempScore, setTempScore] = useState('');
  const [tempPoints, setTempPoints] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchQuizHistory();
  }, []);

  const fetchQuizHistory = async () => {
    setLoading(true);
    try {
      const response = await fetchAuthAPI(`${API_URL}/api/user/quiz-history`);
      if (response.ok) {
        const data = await response.json();
        setQuizzes(data.quizzes || []);
      } else {
        setError('Failed to load quiz history');
      }
    } catch (err) {
      console.error('Error fetching quiz history:', err);
      setError('Failed to load quiz history');
    } finally {
      setLoading(false);
    }
  };

  const fetchQuizResults = async (quizId) => {
    try {
      const response = await fetchAuthAPI(`${API_URL}/api/quiz/${quizId}/results`);
      if (response.ok) {
        const data = await response.json();
        setQuizResults(data);
        setSelectedQuiz(quizId);
      } else {
        setError('Failed to load quiz results');
      }
    } catch (err) {
      console.error('Error fetching quiz results:', err);
      setError('Failed to load quiz results');
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const closeResults = () => {
    setSelectedQuiz(null);
    setQuizResults(null);
    setExpandedPlayer(null);
    setPlayerAnswers({});
    setEditingScore(null);
    setEditingAnswer(null);
  };

  const togglePlayerAnswers = async (playerId) => {
    if (expandedPlayer === playerId) {
      setExpandedPlayer(null);
      return;
    }

    setExpandedPlayer(playerId);

    // Fetch answers if not already loaded
    if (!playerAnswers[playerId]) {
      try {
        const response = await fetchAuthAPI(`${API_URL}/api/quiz/${selectedQuiz}/player/${playerId}/answers`);
        if (response.ok) {
          const data = await response.json();
          setPlayerAnswers(prev => ({ ...prev, [playerId]: data.answers }));
        } else {
          setError('Failed to load player answers');
        }
      } catch (err) {
        console.error('Error fetching player answers:', err);
        setError('Failed to load player answers');
      }
    }
  };

  const startEditingScore = (playerId, currentScore) => {
    setEditingScore(playerId);
    setTempScore(currentScore.toString());
  };

  const cancelEditingScore = () => {
    setEditingScore(null);
    setTempScore('');
  };

  const savePlayerScore = async (playerId) => {
    const newScore = parseInt(tempScore);
    if (isNaN(newScore) || newScore < 0) {
      setError('Please enter a valid score');
      return;
    }

    try {
      const response = await fetchAuthAPI(`${API_URL}/api/quiz/${selectedQuiz}/player/${playerId}/score`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ score: newScore })
      });

      if (response.ok) {
        // Update the local state
        setQuizResults(prev => ({
          ...prev,
          players: prev.players.map(p =>
            p.player_id === playerId ? { ...p, score: newScore } : p
          ).sort((a, b) => b.score - a.score)
        }));
        setEditingScore(null);
        setTempScore('');
      } else {
        setError('Failed to update score');
      }
    } catch (err) {
      console.error('Error updating score:', err);
      setError('Failed to update score');
    }
  };

  const startEditingAnswer = (playerId, dayNumber, currentPoints) => {
    setEditingAnswer(`${playerId}-${dayNumber}`);
    setTempPoints(currentPoints.toString());
  };

  const cancelEditingAnswer = () => {
    setEditingAnswer(null);
    setTempPoints('');
  };

  const saveAnswerPoints = async (playerId, dayNumber, currentlyCorrect) => {
    const newPoints = parseInt(tempPoints);
    if (isNaN(newPoints) || newPoints < 0) {
      setError('Please enter valid points');
      return;
    }

    try {
      const response = await fetchAuthAPI(
        `${API_URL}/api/quiz/${selectedQuiz}/player/${playerId}/answer/${dayNumber}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            is_correct: newPoints > 0,
            points_earned: newPoints 
          })
        }
      );

      if (response.ok) {
        const data = await response.json();
        
        // Update player answers
        setPlayerAnswers(prev => ({
          ...prev,
          [playerId]: prev[playerId].map(ans =>
            ans.day_number === dayNumber 
              ? { ...ans, is_correct: data.is_correct, points_earned: data.points_earned }
              : ans
          )
        }));

        // Update player score in results
        setQuizResults(prev => ({
          ...prev,
          players: prev.players.map(p => {
            if (p.player_id === playerId) {
              const newScore = p.score + data.points_difference;
              const correctAnswers = p.correct_answers + (data.is_correct && !currentlyCorrect ? 1 : !data.is_correct && currentlyCorrect ? -1 : 0);
              return { ...p, score: newScore, correct_answers: correctAnswers };
            }
            return p;
          }).sort((a, b) => b.score - a.score)
        }));

        setEditingAnswer(null);
        setTempPoints('');
      } else {
        setError('Failed to update answer');
      }
    } catch (err) {
      console.error('Error updating answer:', err);
      setError('Failed to update answer');
    }
  };

  return (
    <div className="quiz-history-page">
      <div className="snow-overlay"></div>

      <div className="history-container">
        {/* Header */}
        <div className="history-header">
          <button className="back-button" onClick={onBack}>
            ← Back to Dashboard
          </button>
          <h1>📊 Quiz History</h1>
        </div>

        {error && (
          <div className="history-error">
            {error}
            <button onClick={() => setError('')}>×</button>
          </div>
        )}

        {/* Quiz List */}
        <div className="history-content">
          {loading ? (
            <div className="loading-state">
              <p>Loading quiz history...</p>
            </div>
          ) : quizzes.length === 0 ? (
            <div className="empty-state">
              <h2>🎄 No Quizzes Yet</h2>
              <p>You haven't hosted any quizzes yet.</p>
              <p>Go to the dashboard to create your first quiz!</p>
            </div>
          ) : (
            <div className="quizzes-list">
              {quizzes.map(quiz => (
                <div key={quiz.quiz_id} className="quiz-history-item">
                  <div className="quiz-main-info">
                    <div className="quiz-header-row">
                      <div className="quiz-id-section">
                        <span className="quiz-label">Quiz ID:</span>
                        <span className="quiz-id">{quiz.quiz_id}</span>
                      </div>
                      <div className="quiz-status-badges">
                        <span className={`badge ${quiz.started ? 'started' : 'not-started'}`}>
                          {quiz.started ? '✓ Started' : '⏳ Not Started'}
                        </span>
                        {quiz.completed && <span className="badge completed">✓ Completed</span>}
                      </div>
                    </div>

                    <div className="quiz-date">
                      📅 {formatDate(quiz.created_at)}
                    </div>

                    <div className="quiz-stats-row">
                      <div className="stat-box">
                        <div className="stat-icon">👥</div>
                        <div className="stat-info">
                          <div className="stat-value">{quiz.player_count}</div>
                          <div className="stat-label">Players</div>
                        </div>
                      </div>

                      <div className="stat-box">
                        <div className="stat-icon">🏆</div>
                        <div className="stat-info">
                          <div className="stat-value">{quiz.top_score}</div>
                          <div className="stat-label">Top Score</div>
                        </div>
                      </div>

                      <div className="stat-box">
                        <div className="stat-icon">📝</div>
                        <div className="stat-info">
                          <div className="stat-value">{quiz.question_set_name}</div>
                          <div className="stat-label">Questions</div>
                        </div>
                      </div>
                    </div>

                    {quiz.player_count > 0 && (
                      <button
                        className="view-results-button"
                        onClick={() => fetchQuizResults(quiz.quiz_id)}
                      >
                        View Detailed Results →
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Results Modal */}
        {selectedQuiz && quizResults && (
          <div className="results-modal-overlay" onClick={closeResults}>
            <div className="results-modal" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h2>Quiz Results - {selectedQuiz}</h2>
                <button className="close-modal" onClick={closeResults}>×</button>
              </div>

              <div className="modal-content">
                <div className="results-summary">
                  <div className="summary-stat">
                    <span className="summary-label">Total Players:</span>
                    <span className="summary-value">{quizResults.players.length}</span>
                  </div>
                  <div className="summary-stat">
                    <span className="summary-label">Average Score:</span>
                    <span className="summary-value">
                      {quizResults.players.length > 0
                        ? Math.round(
                            quizResults.players.reduce((sum, p) => sum + p.score, 0) /
                            quizResults.players.length
                          )
                        : 0}
                    </span>
                  </div>
                </div>

                <div className="players-results">
                  <h3>Player Rankings</h3>
                  <div className="players-table">
                    {quizResults.players.map((player, index) => (
                      <div key={player.player_id} className="player-card">
                        <div 
                          className={`player-row ${index === 0 ? 'first-place' : ''} ${expandedPlayer === player.player_id ? 'expanded' : ''}`}
                          onClick={() => togglePlayerAnswers(player.player_id)}
                        >
                          <div className="player-rank">
                            {index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : `#${index + 1}`}
                          </div>
                          <div className="player-name">{player.username}</div>
                          <div className="player-stats">
                            {editingScore === player.player_id ? (
                              <div className="score-edit-inline" onClick={(e) => e.stopPropagation()}>
                                <input
                                  type="number"
                                  value={tempScore}
                                  onChange={(e) => setTempScore(e.target.value)}
                                  className="score-input"
                                  min="0"
                                />
                                <button className="save-btn" onClick={() => savePlayerScore(player.player_id)}>✓</button>
                                <button className="cancel-btn" onClick={cancelEditingScore}>✗</button>
                              </div>
                            ) : (
                              <>
                                <span className="player-score">
                                  {player.score} pts
                                  <button 
                                    className="edit-icon-btn"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      startEditingScore(player.player_id, player.score);
                                    }}
                                  >
                                    ✏️
                                  </button>
                                </span>
                              </>
                            )}
                            <span className="player-answers">
                              {player.correct_answers}/{player.questions_answered} correct
                            </span>
                            <span className="player-accuracy">
                              {player.questions_answered > 0
                                ? Math.round((player.correct_answers / player.questions_answered) * 100)
                                : 0}% accuracy
                            </span>
                          </div>
                          <div className="expand-icon">
                            {expandedPlayer === player.player_id ? '▼' : '▶'}
                          </div>
                        </div>

                        {/* Expanded answers section */}
                        {expandedPlayer === player.player_id && (
                          <div className="player-answers-details">
                            {!playerAnswers[player.player_id] ? (
                              <div className="loading-answers">Loading answers...</div>
                            ) : playerAnswers[player.player_id].length === 0 ? (
                              <div className="no-answers">No answers yet</div>
                            ) : (
                              <div className="answers-list">
                                {playerAnswers[player.player_id].map((answer) => (
                                  <div 
                                    key={answer.day_number} 
                                    className={`answer-row ${answer.is_correct ? 'correct' : 'incorrect'}`}
                                  >
                                    {/* Header with day number and status */}
                                    <div className="answer-row-header">
                                      <span className="col-day">Question #{answer.day_number}</span>
                                      <span className={`status-badge ${answer.is_correct ? 'correct-badge' : 'incorrect-badge'}`}>
                                        {answer.is_correct ? '✓ Correct' : '✗ Incorrect'}
                                      </span>
                                      {answer.ai_verified && (
                                        <span 
                                          className="ai-badge" 
                                          title={`AI Verified (${answer.ai_confidence}% confidence)\n${answer.ai_reasoning}`}
                                        >
                                          🤖 AI {answer.ai_confidence}%
                                        </span>
                                      )}
                                    </div>

                                    {/* Content */}
                                    <div className="answer-row-content">
                                      {/* Question */}
                                      <div className="answer-info-line">
                                        <span className="answer-label">Question</span>
                                        <span className="col-question">{answer.question_text}</span>
                                      </div>

                                      {/* Their Answer */}
                                      <div className="answer-info-line">
                                        <span className="answer-label">Their Answer</span>
                                        <span className="col-answer">{answer.player_answer}</span>
                                      </div>

                                      {/* Correct Answer */}
                                      <div className="answer-info-line">
                                        <span className="answer-label">Correct Answer</span>
                                        <span className="col-correct">{answer.correct_answer}</span>
                                      </div>

                                      {/* Points */}
                                      <div className="answer-info-line">
                                        <span className="answer-label">Points Earned</span>
                                        <div className="col-points">
                                          {editingAnswer === `${player.player_id}-${answer.day_number}` ? (
                                            <div className="points-edit-inline">
                                              <input
                                                type="number"
                                                value={tempPoints}
                                                onChange={(e) => setTempPoints(e.target.value)}
                                                className="points-input"
                                                min="0"
                                              />
                                              <button className="save-btn-small" onClick={() => saveAnswerPoints(player.player_id, answer.day_number, answer.is_correct)}>✓</button>
                                              <button className="cancel-btn-small" onClick={cancelEditingAnswer}>✗</button>
                                            </div>
                                          ) : (
                                            <>
                                              <span style={{fontSize: '1.2em', color: '#2f7d3f'}}>{answer.points_earned} pts</span>
                                              <button 
                                                className="edit-answer-btn"
                                                onClick={() => startEditingAnswer(player.player_id, answer.day_number, answer.points_earned)}
                                              >
                                                Edit Points
                                              </button>
                                            </>
                                          )}
                                        </div>
                                      </div>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default QuizHistory;
