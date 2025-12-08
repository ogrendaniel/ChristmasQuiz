import React, { useState, useEffect } from 'react';
import './App.css';
import WelcomePage from './components/WelcomePage';
import WaitingRoom from './components/WaitingRoom';
import JoinPage from './components/JoinPage';
import QuizPage from './components/QuizPage';

function App() {
  const [page, setPage] = useState('welcome'); // welcome, waiting, join, quiz
  const [quizData, setQuizData] = useState(null);
  const [playerData, setPlayerData] = useState(null);
  const [isHost, setIsHost] = useState(false);

  useEffect(() => {
    // Check if this is a join link
    const path = window.location.pathname;
    const joinMatch = path.match(/^\/join\/([a-zA-Z0-9]+)$/);
    
    if (joinMatch) {
      const quizId = joinMatch[1];
      setPage('join');
      setQuizData({ quiz_id: quizId });
    }
  }, []);

  const handleCreateQuiz = (data) => {
    setQuizData(data);
    setIsHost(true);
    setPage('waiting');
    // Update URL without reloading
    window.history.pushState({}, '', `/host/${data.quiz_id}`);
  };

  const handleJoinSuccess = (data) => {
    setPlayerData(data);
    setIsHost(false);
    setPage('player-waiting');
  };

  const handleStartQuiz = () => {
    setPage('quiz');
  };

  return (
    <div className="App">
      {page === 'welcome' && (
        <WelcomePage onCreateQuiz={handleCreateQuiz} />
      )}
      
      {page === 'waiting' && quizData && (
        <WaitingRoom 
          quizData={quizData} 
          onStartQuiz={handleStartQuiz} 
        />
      )}
      
      {page === 'join' && quizData && (
        <JoinPage 
          quizId={quizData.quiz_id} 
          onJoinSuccess={handleJoinSuccess} 
        />
      )}
      
      {page === 'player-waiting' && playerData && (
        <PlayerWaitingRoom 
          playerData={playerData} 
          onQuizStart={handleStartQuiz}
        />
      )}
      
      {page === 'quiz' && (
        <QuizPage 
          quizData={quizData} 
          playerData={playerData}
          isHost={isHost}
        />
      )}
    </div>
  );
}

// Component for players waiting for host to start
function PlayerWaitingRoom({ playerData, onQuizStart }) {
  const [quizStarted, setQuizStarted] = useState(false);

  useEffect(() => {
    // Poll to check if quiz has started
    const interval = setInterval(async () => {
      try {
        const response = await fetch(
          `http://localhost:8000/api/quiz/${playerData.quiz_id}`
        );
        const data = await response.json();
        if (data.started && !quizStarted) {
          setQuizStarted(true);
          onQuizStart();
        }
      } catch (error) {
        console.error('Error checking quiz status:', error);
      }
    }, 2000);
    
    return () => clearInterval(interval);
  }, [playerData.quiz_id, quizStarted, onQuizStart]);

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
      padding: '20px'
    }}>
      <div style={{
        background: 'white',
        borderRadius: '20px',
        padding: '50px 40px',
        maxWidth: '500px',
        width: '100%',
        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
        textAlign: 'center'
      }}>
        <h1 style={{ fontSize: '2.5em', margin: '0 0 20px 0', color: '#333' }}>
          ✓ Joined Successfully!
        </h1>
        <p style={{ fontSize: '1.3em', color: '#666', marginBottom: '30px' }}>
          Welcome, <strong>{playerData.username}</strong>!
        </p>
        <div style={{
          background: '#f8f9fa',
          padding: '30px',
          borderRadius: '10px',
          marginBottom: '20px'
        }}>
          <div style={{ fontSize: '3em', marginBottom: '15px' }}>⏳</div>
          <p style={{ fontSize: '1.2em', color: '#555', margin: 0 }}>
            Waiting for the host to start the quiz...
          </p>
        </div>
        <p style={{ color: '#999', fontSize: '0.9em', fontStyle: 'italic' }}>
          The game will start automatically when the host is ready!
        </p>
      </div>
    </div>
  );
}

export default App;
