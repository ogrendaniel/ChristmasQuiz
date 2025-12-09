import React, { useState, useEffect } from 'react';
import './DashboardPage.css';
import { API_URL, fetchAuthAPI } from '../config';

function DashboardPage({ userData, onCreateQuiz, onNavigateToQuestions, onNavigateToHistory, onLogout }) {
  const [questionSets, setQuestionSets] = useState([]);
  const [selectedQuestionSet, setSelectedQuestionSet] = useState('standard');
  const [recentQuizzes, setRecentQuizzes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      // Fetch user's question sets
      const setsResponse = await fetchAuthAPI(`${API_URL}/api/question-sets`);
      if (setsResponse.ok) {
        const setsData = await setsResponse.json();
        setQuestionSets(setsData.question_sets || []);
        
        // Set default question set if one exists
        const defaultSet = setsData.question_sets.find(set => set.is_default);
        if (defaultSet) {
          setSelectedQuestionSet(defaultSet.id);
        }
      }

      // Fetch recent quiz history
      const historyResponse = await fetchAuthAPI(`${API_URL}/api/user/quiz-history`);
      if (historyResponse.ok) {
        const historyData = await historyResponse.json();
        setRecentQuizzes(historyData.quizzes.slice(0, 5) || []); // Show only 5 most recent
      }
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      setError('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateQuiz = async () => {
    try {
      const body = selectedQuestionSet === 'standard' 
        ? {} 
        : { question_set_id: selectedQuestionSet };

      const response = await fetchAuthAPI(`${API_URL}/api/quiz/create`, {
        method: 'POST',
        body: JSON.stringify(body)
      });

      if (response.ok) {
        const data = await response.json();
        onCreateQuiz(data);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to create quiz');
      }
    } catch (err) {
      console.error('Error creating quiz:', err);
      setError('Failed to create quiz');
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="dashboard-page">
      <div className="snow-overlay"></div>
      
      <div className="dashboard-container">
        {/* Header */}
        <div className="dashboard-header">
          <div className="header-content">
            <h1>🎄 Christmas Quiz Dashboard 🎄</h1>
            <p className="welcome-text">Welcome back, <strong>{userData.username}</strong>!</p>
          </div>
          <button className="logout-button" onClick={onLogout}>
            Logout
          </button>
        </div>

        {error && <div className="dashboard-error">{error}</div>}

        {/* Main Content */}
        <div className="dashboard-content">
          {/* Create Quiz Section */}
          <div className="dashboard-card create-quiz-card">
            <h2>🎅 Create New Quiz</h2>
            <p>Choose your question set and start a new quiz session</p>
            
            <div className="question-set-selector">
              <label htmlFor="questionSet">Question Set:</label>
              <select 
                id="questionSet"
                value={selectedQuestionSet}
                onChange={(e) => setSelectedQuestionSet(e.target.value)}
                disabled={loading}
              >
                <option value="standard">Standard Questions</option>
                {questionSets.map(set => (
                  <option key={set.id} value={set.id}>
                    {set.name} ({set.question_count}/24 questions)
                    {set.is_default ? ' ⭐' : ''}
                  </option>
                ))}
              </select>
            </div>

            <button 
              className="create-quiz-button"
              onClick={handleCreateQuiz}
              disabled={loading}
            >
              🎁 Create Quiz
            </button>

            {questionSets.length === 0 && !loading && (
              <p className="hint-text">
                💡 No custom question sets yet. <span className="link-text" onClick={onNavigateToQuestions}>Create one now!</span>
              </p>
            )}
          </div>

          {/* Quick Actions */}
          <div className="dashboard-card actions-card">
            <h2>⚙️ Quick Actions</h2>
            <div className="action-buttons">
              <button className="action-button" onClick={onNavigateToQuestions}>
                <span className="icon">📝</span>
                <span className="text">Manage Questions</span>
                <span className="description">Create and edit your custom questions</span>
              </button>
              <button className="action-button" onClick={onNavigateToHistory}>
                <span className="icon">📊</span>
                <span className="text">Quiz History</span>
                <span className="description">View past quizzes and results</span>
              </button>
            </div>
          </div>

          {/* Recent Quizzes */}
          <div className="dashboard-card recent-quizzes-card">
            <h2>📜 Recent Quizzes</h2>
            {loading ? (
              <p className="loading-text">Loading...</p>
            ) : recentQuizzes.length === 0 ? (
              <p className="empty-text">No quizzes hosted yet. Create your first quiz above!</p>
            ) : (
              <div className="quiz-list">
                {recentQuizzes.map(quiz => (
                  <div key={quiz.quiz_id} className="quiz-item">
                    <div className="quiz-info">
                      <div className="quiz-id">Quiz ID: <strong>{quiz.quiz_id}</strong></div>
                      <div className="quiz-date">{formatDate(quiz.created_at)}</div>
                    </div>
                    <div className="quiz-stats">
                      <span className="stat">👥 {quiz.player_count} players</span>
                      <span className="stat">🏆 {quiz.top_score} pts</span>
                      <span className={`status ${quiz.started ? 'started' : 'waiting'}`}>
                        {quiz.started ? '✓ Started' : '⏳ Waiting'}
                      </span>
                    </div>
                    <div className="quiz-questions">
                      {quiz.question_set_name}
                    </div>
                  </div>
                ))}
              </div>
            )}
            {recentQuizzes.length > 0 && (
              <button className="view-all-button" onClick={onNavigateToHistory}>
                View All Quizzes →
              </button>
            )}
          </div>

          {/* Stats Overview */}
          <div className="dashboard-card stats-card">
            <h2>📈 Your Stats</h2>
            <div className="stats-grid">
              <div className="stat-item">
                <div className="stat-value">{questionSets.length}</div>
                <div className="stat-label">Question Sets</div>
              </div>
              <div className="stat-item">
                <div className="stat-value">{recentQuizzes.length}</div>
                <div className="stat-label">Total Quizzes</div>
              </div>
              <div className="stat-item">
                <div className="stat-value">
                  {recentQuizzes.reduce((sum, q) => sum + q.player_count, 0)}
                </div>
                <div className="stat-label">Total Players</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DashboardPage;
