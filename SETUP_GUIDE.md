# Christmas Quiz - Setup & Testing Guide

## 🎯 What's Been Implemented

### Complete User Account System
- ✅ User registration and login with JWT authentication
- ✅ Custom question set management (create, edit, delete)
- ✅ Quiz history tracking with detailed results
- ✅ Dashboard for managing everything
- ✅ Beautiful Christmas-themed UI throughout

## 📋 Setup Instructions

### Ngrok start
C:\Users\danie\AppData\Local\Microsoft\WindowsApps\ngrok.exe start --all --config ngrok.yml

### Backend Setup

1. **Install Python Dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Create Environment File** (Optional but recommended)
   Create `backend/.env`:
   ```
   SECRET_KEY=your-secret-key-here-change-in-production-use-long-random-string
   FRONTEND_URL=http://localhost:3000
   ```

3. **Start the Backend Server**
   ```bash
   uvicorn main:app --reload
   ```
   
   The backend will run on `http://localhost:8000`

### Frontend Setup

1. **Update API URL**
   Edit `frontend/src/config.js` and update the `API_URL`:
   ```javascript
   export const API_URL = 'http://localhost:8000';  // For local development
   // OR
   export const API_URL = 'https://your-ngrok-url.ngrok-free.app';  // For ngrok
   ```

2. **Install Dependencies** (if not already done)
   ```bash
   cd frontend
   npm install
   ```

3. **Start the Frontend**
   ```bash
   npm start
   ```
   
   The frontend will run on `http://localhost:3000`

## 🧪 Testing the Full Flow

### 1. Register a New User
1. Go to `http://localhost:3000`
2. You'll see the login page
3. Click "Register here"
4. Fill in:
   - Username: `testuser`
   - Email: `test@example.com`
   - Password: `password123`
   - Confirm Password: `password123`
5. Click "Register"
6. You'll be automatically logged in and redirected to the dashboard

### 2. Create Custom Questions
1. From the dashboard, click "Manage Questions"
2. Click "+ New Set"
3. Enter a name like "My Christmas Questions" and click "Create"
4. Click on the newly created set
5. Click "+ Add Question"
6. Fill in:
   - Day Number: Select from dropdown (1-24)
   - Question Text: "What color is Santa's suit?"
   - Correct Answer: "red"
   - Images: (Optional) Add image URLs
7. Click "Save Question"
8. Repeat to add more questions (you can add up to 24)
9. Click "Back to Dashboard" when done

### 3. Create a Quiz
1. From the dashboard:
   - Select your custom question set from the dropdown
   - OR leave it as "Standard Questions"
2. Click "🎁 Create Quiz"
3. You'll see the waiting room with:
   - Quiz ID
   - Join link
   - Share these with players!

### 4. Join as a Player (Different Browser/Incognito)
1. Open a new incognito window or different browser
2. Go to the join link (e.g., `http://localhost:3000/join/abc12345`)
3. Enter a username (e.g., "Player1")
4. Click "Join Quiz"
5. You'll see "Waiting for host to start"

### 5. Start the Quiz
1. Back in the host window, click "Start Quiz"
2. Both host and players will see the advent calendar

### 6. Play the Quiz
**As a Player:**
1. Click on Day 1 box
2. Answer the question
3. See if you got it right
4. Continue through the days in order

**As a Host:**
1. You can view any day's question
2. See the leaderboard updating in real-time

### 7. View Quiz History
1. After finishing, go back to dashboard (refresh if needed)
2. Click "Quiz History" 
3. See your past quiz listed
4. Click "View Detailed Results" to see:
   - Player rankings
   - Scores and accuracy
   - Questions answered

## 🎨 Features Overview

### Dashboard
- Create new quizzes with standard or custom questions
- Quick stats: question sets, total quizzes, total players
- Recent quiz history preview
- Quick actions to manage questions and view history

### Question Manager
- Create multiple question sets
- Add 24 questions per set (one for each day)
- Set a default question set
- Delete question sets
- Track progress (X/24 questions complete)

### Quiz History
- List all hosted quizzes
- See quiz stats (players, top score, date)
- View detailed results for each quiz
- Player rankings with accuracy percentages

### Quiz Gameplay
- Advent calendar interface (24 boxes)
- Players must complete days in order
- Live leaderboard updates
- Beautiful Christmas theme
- Mobile responsive

## 🔐 Authentication Flow

1. **First Visit**: User sees login page
2. **After Login**: Redirected to dashboard
3. **Token Storage**: JWT token stored in localStorage
4. **Auto-Login**: Token validated on page refresh
5. **Logout**: Clears all data and returns to login

## 📱 Special Cases

### Join Links (No Auth Required)
- Players don't need accounts to join quizzes
- Join links work without authentication
- Player data saved in localStorage for rejoin

### Session Persistence
- Hosts can refresh and return to their quiz
- Players can refresh and return to their quiz
- Auth tokens persist across browser sessions

## 🐛 Troubleshooting

### Backend Issues

**Import Error for bcrypt/PyJWT:**
```bash
pip install bcrypt PyJWT pydantic-email-validator
```

**Database Error:**
- Delete `backend/quiz_database.db`
- Restart the backend (it will recreate tables)

**CORS Error:**
- Check FRONTEND_URL in backend matches your frontend URL
- Restart backend after changes

### Frontend Issues

**Login Fails:**
- Check backend is running on correct port
- Check API_URL in `config.js` matches backend
- Check browser console for errors

**Components Not Found:**
- Make sure all new component files are created:
  - `LoginPage.js`
  - `RegisterPage.js`
  - `DashboardPage.js`
  - `QuestionManager.js`
  - `QuizHistory.js`
  - And their corresponding `.css` files

**Questions Not Loading:**
- Make sure you're passing `quiz_id` when fetching questions
- Check if quiz has a `question_set_id` in database

## 🎄 Next Steps / Enhancements

Potential future improvements:
1. Password reset functionality
2. Email verification
3. Profile settings page
4. Edit existing questions (currently can only add/delete)
5. Import/export question sets
6. Quiz templates
7. Time limits for questions
8. Question categories/difficulty levels
9. Multiplayer live events
10. Prize/reward system

## 📊 Database Structure

The SQLite database includes:
- `users` - User accounts
- `custom_question_sets` - User's question collections
- `custom_questions` - Questions in custom sets
- `questions` - Standard questions
- `quizzes` - Quiz sessions (linked to users and question sets)
- `players` - Players in quizzes
- `player_answers` - Answer tracking

## 🎉 That's It!

You now have a complete, working Christmas Quiz application with:
- ✅ User authentication
- ✅ Custom question management
- ✅ Quiz hosting and playing
- ✅ History and analytics
- ✅ Beautiful UI

Enjoy hosting your Christmas quizzes! 🎄🎅⭐
