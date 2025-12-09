from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uuid
from datetime import datetime
import sqlite3
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Frontend URL configuration - can be set via environment variable
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://*.ngrok-free.app",  # Allow all ngrok URLs
        "https://*.ngrok.io",
        "*"  # Or add your specific ngrok URL here
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
DB_PATH = "quiz_database.db"

def init_db():
    """Initialize the database with questions table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create questions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY,
            day_number INTEGER UNIQUE NOT NULL,
            question_text TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            image_1 TEXT,
            image_2 TEXT,
            image_3 TEXT,
            image_4 TEXT,
            image_5 TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create player_answers table to track which questions players have answered
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS player_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id TEXT NOT NULL,
            quiz_id TEXT NOT NULL,
            day_number INTEGER NOT NULL,
            answer TEXT NOT NULL,
            is_correct BOOLEAN NOT NULL,
            points_earned INTEGER NOT NULL,
            answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(player_id, quiz_id, day_number)
        )
    """)
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# In-memory storage (replace with database in production)
quizzes = {}
players = {}

class Player(BaseModel):
    username: str

class Quiz(BaseModel):
    id: str
    host_id: str
    created_at: datetime
    started: bool
    players: List[dict]

class Question(BaseModel):
    day_number: int
    question_text: str
    correct_answer: str
    image_1: Optional[str] = None
    image_2: Optional[str] = None
    image_3: Optional[str] = None
    image_4: Optional[str] = None
    image_5: Optional[str] = None

class AnswerSubmission(BaseModel):
    player_id: str
    quiz_id: str
    answer: str

@app.get("/")
def root():
    return {"message": "Quiz API is running!"}

@app.post("/api/quiz/create")
def create_quiz():
    """Create a new quiz and return unique quiz ID"""
    quiz_id = str(uuid.uuid4())[:8]  # Short unique ID
    quizzes[quiz_id] = {
        "id": quiz_id,
        "host_id": str(uuid.uuid4()),
        "created_at": datetime.now(),
        "started": False,
        "players": []
    }
    return {
        "quiz_id": quiz_id,
        "host_id": quizzes[quiz_id]["host_id"],
        "join_link": f"{FRONTEND_URL}/join/{quiz_id}"
    }

@app.get("/api/quiz/{quiz_id}")
def get_quiz(quiz_id: str):
    """Get quiz details"""
    if quiz_id not in quizzes:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return quizzes[quiz_id]

@app.post("/api/quiz/{quiz_id}/join")
def join_quiz(quiz_id: str, player: Player):
    """Add a player to the quiz"""
    if quiz_id not in quizzes:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    quiz = quizzes[quiz_id]
    
    if quiz["started"]:
        raise HTTPException(status_code=400, detail="Quiz already started")
    
    # Check if username already exists in this quiz
    if any(p["username"] == player.username for p in quiz["players"]):
        raise HTTPException(status_code=400, detail="Username already taken")
    
    player_id = str(uuid.uuid4())
    player_data = {
        "id": player_id,
        "username": player.username,
        "score": 0,
        "joined_at": datetime.now().isoformat()
    }
    
    quiz["players"].append(player_data)
    players[player_id] = {**player_data, "quiz_id": quiz_id}
    
    return {
        "player_id": player_id,
        "username": player.username,
        "quiz_id": quiz_id
    }

@app.get("/api/quiz/{quiz_id}/players")
def get_players(quiz_id: str):
    """Get all players in a quiz"""
    if quiz_id not in quizzes:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return {"players": quizzes[quiz_id]["players"]}

@app.post("/api/quiz/{quiz_id}/start")
def start_quiz(quiz_id: str, host_id: str):
    """Start the quiz (only host can start)"""
    if quiz_id not in quizzes:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    quiz = quizzes[quiz_id]
    
    if quiz["host_id"] != host_id:
        raise HTTPException(status_code=403, detail="Only host can start the quiz")
    
    if len(quiz["players"]) == 0:
        raise HTTPException(status_code=400, detail="Need at least one player to start")
    
    quiz["started"] = True
    return {"message": "Quiz started!", "started": True}

@app.put("/api/player/{player_id}/score")
def update_score(player_id: str, score: int):
    """Update player score"""
    if player_id not in players:
        raise HTTPException(status_code=404, detail="Player not found")
    
    players[player_id]["score"] = score
    
    # Update in quiz as well
    quiz_id = players[player_id]["quiz_id"]
    for player in quizzes[quiz_id]["players"]:
        if player["id"] == player_id:
            player["score"] = score
            break
    
    return {"player_id": player_id, "score": score}

# Question endpoints
@app.post("/api/questions")
def create_question(question: Question):
    """Create a new question (admin/setup endpoint)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO questions (day_number, question_text, correct_answer, image_1, image_2, image_3, image_4, image_5)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (question.day_number, question.question_text, question.correct_answer, 
              question.image_1, question.image_2, question.image_3, question.image_4, question.image_5))
        conn.commit()
        question_id = cursor.lastrowid
        conn.close()
        return {"message": "Question created", "id": question_id}
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Question for this day already exists")

@app.get("/api/questions/{day_number}")
def get_question(day_number: int):
    """Get question for a specific day"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT day_number, question_text, image_1, image_2, image_3, image_4, image_5
        FROM questions WHERE day_number = ?
    """, (day_number,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Collect images that are not null
    images = [img for img in [row[2], row[3], row[4], row[5], row[6]] if img]
    
    return {
        "day_number": row[0],
        "question_text": row[1],
        "images": images
    }

@app.post("/api/questions/{day_number}/answer")
def submit_answer(day_number: int, submission: AnswerSubmission):
    """Submit and check answer for a question"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get the correct answer
    cursor.execute("SELECT correct_answer FROM questions WHERE day_number = ?", (day_number,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Question not found")
    
    correct_answer = row[0].strip().lower()
    user_answer = submission.answer.strip().lower()
    is_correct = correct_answer == user_answer
    points_earned = 10 if is_correct else 0
    
    # Check if player already answered this question
    cursor.execute("""
        SELECT id FROM player_answers 
        WHERE player_id = ? AND quiz_id = ? AND day_number = ?
    """, (submission.player_id, submission.quiz_id, day_number))
    
    existing = cursor.fetchone()
    
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="Question already answered")
    
    # Record the answer
    cursor.execute("""
        INSERT INTO player_answers (player_id, quiz_id, day_number, answer, is_correct, points_earned)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (submission.player_id, submission.quiz_id, day_number, submission.answer, is_correct, points_earned))
    
    conn.commit()
    
    # Update player's total score
    cursor.execute("""
        SELECT SUM(points_earned) FROM player_answers 
        WHERE player_id = ? AND quiz_id = ?
    """, (submission.player_id, submission.quiz_id))
    
    total_score = cursor.fetchone()[0] or 0
    conn.close()
    
    # Update in-memory player score
    if submission.player_id in players:
        players[submission.player_id]["score"] = total_score
        quiz_id = players[submission.player_id]["quiz_id"]
        if quiz_id in quizzes:
            for player in quizzes[quiz_id]["players"]:
                if player["id"] == submission.player_id:
                    player["score"] = total_score
                    break
    
    return {
        "is_correct": is_correct,
        "correct_answer": row[0] if not is_correct else None,
        "points_earned": points_earned,
        "total_score": total_score
    }

@app.get("/api/player/{player_id}/quiz/{quiz_id}/answered")
def get_answered_questions(player_id: str, quiz_id: str):
    """Get list of questions this player has already answered"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT day_number, is_correct, points_earned 
        FROM player_answers 
        WHERE player_id = ? AND quiz_id = ?
    """, (player_id, quiz_id))
    
    rows = cursor.fetchall()
    conn.close()
    
    answered = [{"day": row[0], "correct": bool(row[1]), "points": row[2]} for row in rows]
    
    return {"answered_questions": answered}
