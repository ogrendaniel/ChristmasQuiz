import React, { useState, useEffect } from 'react';
import './App.css';
import LoginPage from './components/LoginPage';
import RegisterPage from './components/RegisterPage';
import DashboardPage from './components/DashboardPage';
import QuestionManager from './components/QuestionManager';
import QuizHistory from './components/QuizHistory';
import WaitingRoom from './components/WaitingRoom';
import JoinPage from './components/JoinPage';
import QuizPage from './components/QuizPage';
import { API_URL, fetchAPI, fetchAuthAPI } from './config';

function App() {
  const [page, setPage] = useState('loading'); // loading, login, register, dashboard, questions, history, waiting, join, quiz
  const [userData, setUserData] = useState(null);
  const [quizData, setQuizData] = useState(null);
  const [playerData, setPlayerData] = useState(null);
  const [isHost, setIsHost] = useState(false);

  useEffect(() => {
    checkAuthentication();
  }, []);

  const checkAuthentication = async () => {
    const token = localStorage.getItem('authToken');
    const savedUserData = localStorage.getItem('userData');
    
    // Check if this is a join link (unauthenticated access allowed)
    const path = window.location.pathname;
    const joinMatch = path.match(/^\/join\/([a-zA-Z0-9]+)$/);
    
    if (joinMatch) {
      const quizId = joinMatch[1];
      
      // Check if we have saved player data for this quiz
      const savedPlayerData = localStorage.getItem('quizPlayerData');
      if (savedPlayerData) {
        const playerInfo = JSON.parse(savedPlayerData);
        if (playerInfo.quiz_id === quizId) {
          // Check quiz status to determine which page to show
          try {
            const quizResponse = await fetchAPI(`${API_URL}/api/quiz/${quizId}/check`);
            if (quizResponse.ok) {
              const quizData = await quizResponse.json();
              setPlayerData(playerInfo);
              setQuizData({ quiz_id: quizId });
              setIsHost(false);
              
              // If quiz has started, go to quiz page; otherwise, go to waiting room
              if (quizData.started) {
                setPage('quiz');
              } else {
                setPage('player-waiting');
              }
              return;
            }
          } catch (error) {
            console.error('Error checking quiz status:', error);
          }
        }
      }
      
      // New join
      setPage('join');
      setQuizData({ quiz_id: quizId });
      return;
    }
    
    // Check for authenticated user
    if (!token || !savedUserData) {
      setPage('login');
      return;
    }

    try {
      // Verify token is still valid
      const response = await fetchAuthAPI(`${API_URL}/api/auth/me`);
      if (response.ok) {
        const data = await response.json();
        setUserData(data);
        
        // Check if returning to a hosted quiz AND the URL matches
        const savedQuizData = localStorage.getItem('quizData');
        const savedIsHost = localStorage.getItem('isHost');
        const hostMatch = path.match(/^\/host\/([a-zA-Z0-9-]+)$/);
        
        if (hostMatch) {
          const urlQuizId = hostMatch[1];
          
          // If we have saved quiz data and it matches, restore it
          if (savedIsHost === 'true' && savedQuizData) {
            const quizInfo = JSON.parse(savedQuizData);
            if (quizInfo.quiz_id === urlQuizId) {
              setQuizData(quizInfo);
              setIsHost(true);
              setPage('quiz');
              return;
            }
          }
          
          // No saved data or doesn't match - fetch the quiz from server
          try {
            const quizResponse = await fetchAuthAPI(`${API_URL}/api/quiz/${urlQuizId}`);
            if (quizResponse.ok) {
              const quizData = await quizResponse.json();
              setQuizData({ quiz_id: urlQuizId, ...quizData });
              setIsHost(true);
              setPage('quiz');
              // Save to localStorage
              localStorage.setItem('quizData', JSON.stringify({ quiz_id: urlQuizId, ...quizData }));
              localStorage.setItem('isHost', 'true');
              return;
            } else {
              // Quiz not found or not owned by user
              console.error('Quiz not found or access denied');
              setPage('dashboard');
              window.history.pushState({}, '', '/');
            }
          } catch (error) {
            console.error('Error fetching quiz:', error);
            setPage('dashboard');
            window.history.pushState({}, '', '/');
          }
        } else if (path === '/' || path === '') {
          // At root path, go to dashboard
          setPage('dashboard');
        } else {
          // Unknown path, redirect to dashboard
          setPage('dashboard');
          window.history.pushState({}, '', '/');
        }
      } else {
        // Token invalid, clear and show login
        handleLogout();
      }
    } catch (err) {
      console.error('Auth check failed:', err);
      handleLogout();
    }
  };

  const handleLogin = (data) => {
    setUserData(data);
    setPage('dashboard');
    window.history.pushState({}, '', '/');
  };

  const handleRegister = (data) => {
    setUserData(data);
    setPage('dashboard');
    window.history.pushState({}, '', '/');
  };

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('userData');
    localStorage.removeItem('quizData');
    localStorage.removeItem('isHost');
    setUserData(null);
    setQuizData(null);
    setIsHost(false);
    setPage('login');
    window.history.pushState({}, '', '/');
  };

  const handleCreateQuiz = (data) => {
    setQuizData(data);
    setIsHost(true);
    setPage('waiting');
    // Save to localStorage
    localStorage.setItem('quizData', JSON.stringify(data));
    localStorage.setItem('isHost', 'true');
    // Update URL without reloading
    window.history.pushState({}, '', `/host/${data.quiz_id}`);
  };

  const handleJoinSuccess = (data) => {
    setPlayerData(data);
    setIsHost(false);
    // Save to localStorage
    localStorage.setItem('quizPlayerData', JSON.stringify(data));
    localStorage.setItem('isHost', 'false');
    
    if (data.rejoined) {
      // If rejoining, go straight to quiz
      setPage('quiz');
    } else {
      setPage('player-waiting');
    }
  };

  const handleStartQuiz = () => {
    setPage('quiz');
    // Maintain the URL for both host and player
    if (isHost && quizData?.quiz_id) {
      window.history.pushState({}, '', `/host/${quizData.quiz_id}`);
    } else if (!isHost && playerData?.quiz_id) {
      window.history.pushState({}, '', `/join/${playerData.quiz_id}`);
    }
  };

  const handleBackToDashboard = () => {
    setPage('dashboard');
    // Clear quiz data when explicitly going back to dashboard
    localStorage.removeItem('quizData');
    localStorage.removeItem('isHost');
    setQuizData(null);
    setIsHost(false);
    window.history.pushState({}, '', '/');
  };

  if (page === 'loading') {
    return (
      <div className="App" style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #c92a2a 0%, #8b1a1a 100%)'
      }}>
        <div style={{ color: 'white', fontSize: '1.5em' }}>Loading...</div>
      </div>
    );
  }

  return (
    <div className="App">
      {page === 'login' && (
        <LoginPage 
          onLogin={handleLogin}
          onSwitchToRegister={() => setPage('register')}
        />
      )}
      
      {page === 'register' && (
        <RegisterPage 
          onRegister={handleRegister}
          onSwitchToLogin={() => setPage('login')}
        />
      )}
      
      {page === 'dashboard' && userData && (
        <DashboardPage 
          userData={userData}
          onCreateQuiz={handleCreateQuiz}
          onNavigateToQuestions={() => setPage('questions')}
          onNavigateToHistory={() => setPage('history')}
          onLogout={handleLogout}
        />
      )}
      
      {page === 'questions' && userData && (
        <QuestionManager onBack={handleBackToDashboard} />
      )}
      
      {page === 'history' && userData && (
        <QuizHistory onBack={handleBackToDashboard} />
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
    // Poll to check if quiz has started (using public endpoint)
    const checkQuizStatus = async () => {
      try {
        const response = await fetchAPI(
          `${API_URL}/api/quiz/${playerData.quiz_id}/check`
        );
        const data = await response.json();
        if (data.started && !quizStarted) {
          setQuizStarted(true);
          onQuizStart();
        }
      } catch (error) {
        console.error('Error checking quiz status:', error);
      }
    };

    checkQuizStatus(); // Check immediately
    const interval = setInterval(checkQuizStatus, 2000); // Then every 2 seconds
    
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
