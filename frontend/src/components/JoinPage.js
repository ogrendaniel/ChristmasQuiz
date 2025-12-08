import React, { useState, useEffect } from 'react';
import './JoinPage.css';

function JoinPage({ quizId, onJoinSuccess }) {
  const [username, setUsername] = useState('');
  const [loading, setLoading] = useState(false);
  const [quizExists, setQuizExists] = useState(null);

  useEffect(() => {
    // Verify quiz exists
    const checkQuiz = async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/quiz/${quizId}`);
        if (response.ok) {
          const data = await response.json();
          if (data.started) {
            alert('This quiz has already started!');
            setQuizExists(false);
          } else {
            setQuizExists(true);
          }
        } else {
          setQuizExists(false);
        }
      } catch (error) {
        console.error('Error checking quiz:', error);
        setQuizExists(false);
      }
    };
    
    checkQuiz();
  }, [quizId]);

  const handleJoin = async (e) => {
    e.preventDefault();
    
    if (!username.trim()) {
      alert('Please enter a username');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(
        `http://localhost:8000/api/quiz/${quizId}/join`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ username: username.trim() }),
        }
      );
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to join quiz');
      }
      
      const data = await response.json();
      onJoinSuccess(data);
    } catch (error) {
      console.error('Error joining quiz:', error);
      alert(error.message);
    } finally {
      setLoading(false);
    }
  };

  if (quizExists === null) {
    return (
      <div className="join-page">
        <div className="join-container">
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  if (quizExists === false) {
    return (
      <div className="join-page">
        <div className="join-container">
          <h1>❌ Quiz Not Found</h1>
          <p>This quiz doesn't exist or has already started.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="join-page">
      <div className="join-container">
        <h1>🎯 Join Quiz</h1>
        <p className="quiz-id">Quiz ID: <strong>{quizId}</strong></p>
        
        <form onSubmit={handleJoin} className="join-form">
          <div className="form-group">
            <label htmlFor="username">Enter Your Username</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Your name..."
              maxLength={20}
              className="username-input"
              autoFocus
            />
          </div>
          
          <button 
            type="submit" 
            className="join-btn"
            disabled={loading || !username.trim()}
          >
            {loading ? 'Joining...' : 'Join Quiz'}
          </button>
        </form>

        <p className="info-text">
          Wait for the host to start the game after you join!
        </p>
      </div>
    </div>
  );
}

export default JoinPage;
