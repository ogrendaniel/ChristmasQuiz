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
  const [selectedPlayerModal, setSelectedPlayerModal] = useState(null);
  const [loadingPlayerAnswers, setLoadingPlayerAnswers] = useState(false);

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

  const openPlayerModal = async (player) => {
    setSelectedPlayerModal(player);
    setLoadingPlayerAnswers(true);

    // Fetch answers if not already loaded
    if (!playerAnswers[player.player_id]) {
      try {
        const response = await fetchAuthAPI(`${API_URL}/api/quiz/${selectedQuiz}/player/${player.player_id}/answers`);
        if (response.ok) {
          const data = await response.json();
          setPlayerAnswers(prev => ({ ...prev, [player.player_id]: data.answers || [] }));
        } else {
          const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
          console.error('Error response:', response.status, errorData);
          setError(`Failed to load player answers: ${errorData.detail || response.statusText}`);
        }
      } catch (err) {
        console.error('Error fetching player answers:', err);
        setError('Failed to load player answers: ' + err.message);
      }
    }
    setLoadingPlayerAnswers(false);
  };

  const closePlayerModal = () => {
    setSelectedPlayerModal(null);
    setEditingAnswer(null);
    setTempPoints('');
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

  const deleteQuiz = async (quizId) => {
    if (!window.confirm('Are you sure you want to delete this quiz? This action cannot be undone.')) {
      return;
    }

    try {
      const response = await fetchAuthAPI(`${API_URL}/api/quiz/${quizId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        // Remove from local state
        setQuizzes(prev => prev.filter(q => q.quiz_id !== quizId));
        if (selectedQuiz === quizId) {
          closeResults();
        }
      } else {
        setError('Failed to delete quiz');
      }
    } catch (err) {
      console.error('Error deleting quiz:', err);
      setError('Failed to delete quiz');
    }
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
                        {quiz.all_completed && (
                          <span className="badge all-completed">🎉 All Players Done</span>
                        )}
                        <button 
                          className="delete-quiz-btn"
                          onClick={() => deleteQuiz(quiz.quiz_id)}
                          title="Delete this quiz"
                        >
                          🗑️
                        </button>
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
                          className={`player-row ${index === 0 ? 'first-place' : ''}`}
                          onClick={() => openPlayerModal(player)}
                        >
                          <div className="player-rank">
                            {index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : `#${index + 1}`}
                          </div>
                          <div className="player-name">{player.username}</div>
                          <div className="player-stats">
                            <span className="player-score">
                              {player.score} pts
                            </span>
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
                            👁️ View Details
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Player Details Modal */}
        {selectedPlayerModal && (
          <div className="player-modal-overlay" onClick={closePlayerModal}>
            <div className="player-modal" onClick={(e) => e.stopPropagation()}>
              <div className="player-modal-header">
                <div className="player-modal-title">
                  <h2>📝 {selectedPlayerModal.username}'s Answers</h2>
                  <div className="player-modal-stats">
                    <span className="modal-stat">
                      <strong>Score:</strong> {selectedPlayerModal.score} pts
                    </span>
                    <span className="modal-stat">
                      <strong>Correct:</strong> {selectedPlayerModal.correct_answers}/{selectedPlayerModal.questions_answered}
                    </span>
                    <span className="modal-stat">
                      <strong>Accuracy:</strong> {selectedPlayerModal.questions_answered > 0
                        ? Math.round((selectedPlayerModal.correct_answers / selectedPlayerModal.questions_answered) * 100)
                        : 0}%
                    </span>
                  </div>
                </div>
                <button className="modal-close-btn" onClick={closePlayerModal}>✕</button>
              </div>

              <div className="player-modal-content">
                {loadingPlayerAnswers ? (
                  <div className="modal-loading">
                    <div className="loading-spinner"></div>
                    <p>Loading answers...</p>
                  </div>
                ) : !playerAnswers[selectedPlayerModal.player_id] || playerAnswers[selectedPlayerModal.player_id].length === 0 ? (
                  <div className="modal-no-answers">
                    <p>🎄 No answers submitted yet</p>
                  </div>
                ) : (
                  <div className="modal-answers-grid">
                    {playerAnswers[selectedPlayerModal.player_id].map((answer) => (
                      <div 
                        key={answer.day_number} 
                        className={`modal-answer-card ${answer.is_correct ? 'card-correct' : 'card-incorrect'}`}
                      >
                        <div className="modal-answer-header">
                          <span className="modal-question-num">Question #{answer.day_number}</span>
                          <span className={`modal-status-badge ${answer.is_correct ? 'badge-correct' : 'badge-incorrect'}`}>
                            {answer.is_correct ? '✓ Correct' : '✗ Incorrect'}
                          </span>
                        </div>

                        <div className="modal-answer-body">
                          <div className="modal-answer-section">
                            <span className="modal-label">Question:</span>
                            <p className="modal-question-text">{answer.question_text}</p>
                          </div>

                          <div className="modal-answer-section">
                            <span className="modal-label">Their Answer:</span>
                            <p className={`modal-player-answer ${!answer.is_correct ? 'wrong-answer' : ''}`}>
                              {answer.player_answer}
                            </p>
                          </div>

                          {!answer.is_correct && (
                            <div className="modal-answer-section">
                              <span className="modal-label">Correct Answer:</span>
                              <p className="modal-correct-answer">{answer.correct_answer}</p>
                            </div>
                          )}

                          {answer.ai_verified && (
                            <div className="modal-ai-info">
                              <span className="modal-ai-badge">
                                🤖 AI Verified ({answer.ai_confidence}% confidence)
                              </span>
                              <p className="modal-ai-reasoning">{answer.ai_reasoning}</p>
                            </div>
                          )}

                          <div className="modal-answer-section modal-points-section">
                            <span className="modal-label">Points:</span>
                            {editingAnswer === `${selectedPlayerModal.player_id}-${answer.day_number}` ? (
                              <div className="modal-points-edit">
                                <input
                                  type="number"
                                  value={tempPoints}
                                  onChange={(e) => setTempPoints(e.target.value)}
                                  className="modal-points-input"
                                  min="0"
                                  max="10"
                                />
                                <button className="modal-save-btn" onClick={() => saveAnswerPoints(selectedPlayerModal.player_id, answer.day_number, answer.is_correct)}>
                                  ✓ Save
                                </button>
                                <button className="modal-cancel-btn" onClick={cancelEditingAnswer}>
                                  ✗ Cancel
                                </button>
                              </div>
                            ) : (
                              <div className="modal-points-display">
                                <span className="modal-points-value">{answer.points_earned} pts</span>
                                <button 
                                  className="modal-edit-points-btn"
                                  onClick={() => startEditingAnswer(selectedPlayerModal.player_id, answer.day_number, answer.points_earned)}
                                >
                                  ✏️ Edit Points
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default QuizHistory;
