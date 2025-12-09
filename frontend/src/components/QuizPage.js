import React, { useState, useMemo, useEffect } from 'react';
import './QuizPage.css';
import QuestionPage from './QuestionPage';
import { API_URL, fetchAPI } from '../config';

function QuizPage({ quizData, playerData, isHost }) {
  const [selectedDay, setSelectedDay] = useState(null);
  const [answeredQuestions, setAnsweredQuestions] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  const [lockedDayError, setLockedDayError] = useState(null);
  
  // Create array of numbers 1-24 and shuffle only once using useMemo
  const shuffledDays = useMemo(() => {
    const days = Array.from({ length: 24 }, (_, i) => i + 1);
    return [...days].sort(() => Math.random() - 0.5);
  }, []); // Empty dependency array means this only runs once

  useEffect(() => {
    // Fetch answered questions for players only
    if (!isHost && playerData) {
      fetchAnsweredQuestions();
    }
  }, [isHost, playerData]);

  useEffect(() => {
    // Fetch leaderboard immediately on mount
    fetchLeaderboard();
    
    // Poll leaderboard every 5 seconds
    const interval = setInterval(fetchLeaderboard, 5000);
    return () => clearInterval(interval);
  }, [quizData, playerData]);

  const fetchAnsweredQuestions = async () => {
    try {
      const playerId = playerData.player_id || playerData.id;
      const quizId = quizData.quiz_id || playerData.quiz_id;
      
      const response = await fetchAPI(
        `${API_URL}/api/player/${playerId}/quiz/${quizId}/answered`
      );
      
      if (response.ok) {
        const data = await response.json();
        const answeredDays = data.answered_questions.map(q => q.day);
        setAnsweredQuestions(answeredDays);
      }
    } catch (error) {
      console.error('Error fetching answered questions:', error);
    }
  };

  const fetchLeaderboard = async () => {
    try {
      const quizId = quizData?.quiz_id || playerData?.quiz_id;
      if (!quizId) return;
      
      const response = await fetchAPI(
        `${API_URL}/api/quiz/${quizId}/leaderboard`
      );
      
      if (response.ok) {
        const data = await response.json();
        setLeaderboard(data.leaderboard);
      }
    } catch (error) {
      console.error('Error fetching leaderboard:', error);
    }
  };

  const handleDayClick = async (day) => {
    // Hosts can access any day
    if (isHost) {
      setSelectedDay(day);
      return;
    }
    
    // If player and question already answered, don't allow click
    if (answeredQuestions.includes(day)) {
      return;
    }
    
    // Check if player can access this day (must complete previous days)
    if (day > 1 && !answeredQuestions.includes(day - 1)) {
      setLockedDayError({ day, requiredDay: day - 1 });
      return;
    }
    
    setSelectedDay(day);
  };

  const handleBackToCalendar = () => {
    setSelectedDay(null);
    // Refresh answered questions when returning
    if (!isHost && playerData) {
      fetchAnsweredQuestions();
    }
    // Refresh leaderboard immediately
    fetchLeaderboard();
  };

  const isDayAnswered = (day) => {
    return !isHost && answeredQuestions.includes(day);
  };

  const isDayLocked = (day) => {
    // Hosts can access all days
    if (isHost) return false;
    
    // Day 1 is always unlocked
    if (day === 1) return false;
    
    // Check if previous day is completed
    return !answeredQuestions.includes(day - 1);
  };

  if (selectedDay) {
    return (
      <QuestionPage 
        dayNumber={selectedDay}
        quizData={quizData}
        playerData={playerData}
        isHost={isHost}
        onBack={handleBackToCalendar}
      />
    );
  }

  return (
    <div className="quiz-page advent-calendar">
      {/* Snowflakes overlay */}
      <div className="snow-overlay"></div>
      
      {/* Locked Day Error Popup */}
      {lockedDayError && (
        <div className="locked-day-overlay" onClick={() => setLockedDayError(null)}>
          <div className="locked-day-popup" onClick={(e) => e.stopPropagation()}>
            <div className="locked-icon">🔒</div>
            <h2>Day {lockedDayError.day} is Locked!</h2>
            <p className="locked-message">
              You must complete <strong>Day {lockedDayError.requiredDay}</strong> before accessing Day {lockedDayError.day}.
            </p>
            <p className="locked-hint">
              Complete the previous days in order to unlock more questions! 🎄
            </p>
            <button className="locked-close-btn" onClick={() => setLockedDayError(null)}>
              Got it!
            </button>
          </div>
        </div>
      )}
      
      <div className="calendar-header">
        <h1>🎄 Christmas Advent Quiz Calendar 🎄</h1>
        <p className="subtitle">Click on a door to reveal the question!</p>
        {isHost ? (
          <p className="role-info">HOST • Quiz ID: <strong>{quizData.quiz_id}</strong></p>
        ) : (
          <p className="role-info">Player: <strong>{playerData.username}</strong> • Quiz ID: <strong>{quizData.quiz_id || playerData.quiz_id}</strong></p>
        )}
      </div>

      <div className="quiz-content-wrapper">
        {/* Leaderboard */}
        {leaderboard.length > 0 && (
          <div className="leaderboard-container">
            <h2>🏆 Leaderboard</h2>
            <div className="leaderboard">
              {leaderboard.map((entry, index) => (
                <div 
                  key={entry.player_id} 
                  className={`leaderboard-entry ${index === 0 ? 'first-place' : ''} ${entry.player_id === (playerData?.player_id || playerData?.id) ? 'current-player' : ''}`}
                >
                  <span className="rank">#{entry.rank}</span>
                  <span className="username">{entry.username}</span>
                  <span className="score">{entry.score} pts</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="advent-grid">{shuffledDays.map((day) => {
            const isAnswered = isDayAnswered(day);
            const isLocked = isDayLocked(day);
            
            return (
              <div 
                key={day} 
                className={`advent-door ${isAnswered ? 'answered' : ''} ${isLocked ? 'locked' : ''}`}
                onClick={() => handleDayClick(day)}
              >
                <div className="door-content">
                  <div className="door-number">{day}</div>
                  <div className="door-decoration">
                    {isAnswered ? '✓' : '❄️'}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="calendar-footer">
        <p>{isHost ? 'Select any day to view that question!' : 'Complete days in order from 1 to 24!'}</p>
        <p className="instruction">{isHost ? 'All 24 doors are available' : 'Unlock doors by completing the previous day'}</p>
      </div>
    </div>
  );
}

export default QuizPage;
