# 🎯 Quiz Application

A real-time multiplayer quiz application with host and player modes.

## Features

✅ **Host Mode:**
- Create unique quiz sessions with shareable links
- See players join in real-time
- Start the quiz when ready

✅ **Player Mode:**
- Join quiz via unique link
- Enter username
- Wait for host to start the game

✅ **Real-time Updates:**
- Player list updates automatically
- Score tracking (coming soon)
- Live quiz gameplay (coming soon)

## Setup Instructions

### Backend (FastAPI)

1. Navigate to the backend folder:
```bash
cd backend
```

2. Install dependencies:
```bash
pip install fastapi uvicorn pydantic
```

3. Run the backend server:
```bash
uvicorn main:app --reload
```

The backend will run on `http://localhost:8000`

### Frontend (React)

1. Navigate to the frontend folder:
```bash
cd frontend
```

2. Install dependencies (if not already done):
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

The frontend will run on `http://localhost:3000`

## How to Use

### As a Host:

1. Open `http://localhost:3000`
2. Click **"Create New Quiz"**
3. Share the generated link with players
4. Wait for players to join (you'll see them appear in real-time)
5. Click **"Start Quiz"** when ready

### As a Player:

1. Click the link shared by the host (e.g., `http://localhost:3000/join/abc123`)
2. Enter your username
3. Click **"Join Quiz"**
4. Wait for the host to start the game

## API Endpoints

- `POST /api/quiz/create` - Create a new quiz
- `GET /api/quiz/{quiz_id}` - Get quiz details
- `POST /api/quiz/{quiz_id}/join` - Join a quiz
- `GET /api/quiz/{quiz_id}/players` - Get all players
- `POST /api/quiz/{quiz_id}/start` - Start the quiz (host only)
- `PUT /api/player/{player_id}/score` - Update player score

## Project Structure

```
Quiz/
├── backend/
│   └── main.py          # FastAPI backend
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── WelcomePage.js      # Host creates quiz
│   │   │   ├── WaitingRoom.js      # Host waiting room
│   │   │   ├── JoinPage.js         # Player joins quiz
│   │   │   └── QuizPage.js         # Main quiz page
│   │   └── App.js                   # Main app with routing
│   └── package.json
└── README.md
```

## Next Steps

- [ ] Add quiz questions and answers
- [ ] Implement real-time scoring
- [ ] Add question timer
- [ ] Create leaderboard
- [ ] Add quiz categories
- [ ] Persist data in database
