import React, { useState, useEffect } from 'react';
import './WaitingRoom.css';
import { API_URL, fetchAPI } from '../config';

function WaitingRoom({ quizData, onStartQuiz }) {
  const [players, setPlayers] = useState([]);
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchPlayers = async () => {
      try {
        const response = await fetchAPI(
          `${API_URL}/api/quiz/${quizData.quiz_id}/players`
        );
        const data = await response.json();
        setPlayers(data.players);
      } catch (error) {
        console.error('Error fetching players:', error);
      }
    };

    // Poll for new players every 2 seconds
    const interval = setInterval(fetchPlayers, 2000);
    fetchPlayers(); // Initial fetch
    
    return () => clearInterval(interval);
  }, [quizData.quiz_id]);

  const copyToClipboard = () => {
    // Try modern clipboard API first, fallback to older method
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(quizData.join_link)
        .then(() => {
          setCopied(true);
          setTimeout(() => setCopied(false), 2000);
        })
        .catch(() => {
          // Fallback for HTTP (non-HTTPS) contexts
          fallbackCopy();
        });
    } else {
      fallbackCopy();
    }
  };

  const fallbackCopy = () => {
    const textArea = document.createElement('textarea');
    textArea.value = quizData.join_link;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    document.body.appendChild(textArea);
    textArea.select();
    try {
      document.execCommand('copy');
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      alert('Copy failed. Please copy manually: ' + quizData.join_link);
    }
    document.body.removeChild(textArea);
  };

  const handleStartQuiz = async () => {
    if (players.length === 0) {
      alert('You need at least one player to start the quiz!');
      return;
    }

    setLoading(true);
    try {
      const response = await fetchAPI(
        `${API_URL}/api/quiz/${quizData.quiz_id}/start?host_id=${quizData.host_id}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );
      
      if (!response.ok) {
        throw new Error('Failed to start quiz');
      }
      
      onStartQuiz();
    } catch (error) {
      console.error('Error starting quiz:', error);
      alert('Failed to start quiz. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="waiting-room">
      <div className="waiting-container">
        <h1>🎮 Waiting Room</h1>
        <p className="quiz-id">Quiz ID: <strong>{quizData.quiz_id}</strong></p>

        <div className="link-section">
          <p>Share this link with players:</p>
          <div className="link-container">
            <input 
              type="text" 
              value={quizData.join_link} 
              readOnly 
              className="link-input"
            />
            <button onClick={copyToClipboard} className="copy-btn">
              {copied ? '✓ Copied!' : '📋 Copy'}
            </button>
          </div>
        </div>

        <div className="players-section">
          <h2>Players Joined ({players.length})</h2>
          {players.length === 0 ? (
            <p className="no-players">Waiting for players to join...</p>
          ) : (
            <div className="players-list">
              {players.map((player, index) => (
                <div key={player.id} className="player-card">
                  <span className="player-number">{index + 1}</span>
                  <span className="player-name">{player.username}</span>
                  <span className="player-status">✓ Ready</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <button 
          className="start-btn" 
          onClick={handleStartQuiz}
          disabled={loading || players.length === 0}
        >
          {loading ? 'Starting...' : `Start Quiz (${players.length} ${players.length === 1 ? 'player' : 'players'})`}
        </button>
      </div>
    </div>
  );
}

export default WaitingRoom;
