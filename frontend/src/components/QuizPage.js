import React, { useState, useMemo, useEffect } from 'react';
import './QuizPage.css';
import QuestionPage from './QuestionPage';
import { API_URL, fetchAPI } from '../config';

function QuizPage({ quizData, playerData, isHost }) {
  const [selectedDay, setSelectedDay] = useState(null);
  const [answeredQuestions, setAnsweredQuestions] = useState([]);
  
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

  const handleDayClick = (day) => {
    // If player and question already answered, don't allow click
    if (!isHost && answeredQuestions.includes(day)) {
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
  };

  const isDayAnswered = (day) => {
    return !isHost && answeredQuestions.includes(day);
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
      
      <div className="calendar-header">
        <h1>🎄 Christmas Advent Quiz Calendar 🎄</h1>
        <p className="subtitle">Click on a door to reveal the question!</p>
        {isHost ? (
          <p className="role-info">HOST • Quiz ID: <strong>{quizData.quiz_id}</strong></p>
        ) : (
          <p className="role-info">Player: <strong>{playerData.username}</strong> • Quiz ID: <strong>{quizData.quiz_id || playerData.quiz_id}</strong></p>
        )}
      </div>

      <div className="advent-grid">
        {shuffledDays.map((day) => (
          <div 
            key={day} 
            className={`advent-door ${isDayAnswered(day) ? 'answered' : ''}`}
            onClick={() => handleDayClick(day)}
          >
            <div className="door-content">
              <div className="door-number">{day}</div>
              <div className="door-decoration">
                {isDayAnswered(day) ? '✓' : '❄️'}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="calendar-footer">
        <p>Select any day to start that question!</p>
        <p className="instruction">All 24 doors are available • Complete them all to finish the quiz</p>
      </div>
    </div>
  );
}

export default QuizPage;
