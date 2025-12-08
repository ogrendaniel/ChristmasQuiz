import React, { useState } from 'react';
import './WelcomePage.css';

function WelcomePage({ onCreateQuiz }) {
  const [loading, setLoading] = useState(false);

  const handleCreateQuiz = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/quiz/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error('Failed to create quiz');
      }
      
      const data = await response.json();
      onCreateQuiz(data);
    } catch (error) {
      console.error('Error creating quiz:', error);
      alert('Failed to create quiz. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="welcome-page">
      <div className="welcome-container">
        <h1>🎯 Quiz Master</h1>
        <p className="subtitle">Create your own quiz and invite players!</p>
        
        <div className="features">
          <div className="feature">
            <span className="icon">🔗</span>
            <p>Generate a unique link</p>
          </div>
          <div className="feature">
            <span className="icon">👥</span>
            <p>Invite players to join</p>
          </div>
          <div className="feature">
            <span className="icon">🏆</span>
            <p>Track scores in real-time</p>
          </div>
        </div>

        <button 
          className="create-btn" 
          onClick={handleCreateQuiz}
          disabled={loading}
        >
          {loading ? 'Creating...' : 'Create New Quiz'}
        </button>
      </div>
    </div>
  );
}

export default WelcomePage;
