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
    
    # Create quizzes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quizzes (
            id TEXT PRIMARY KEY,
            host_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started BOOLEAN DEFAULT 0
        )
    """)
    
    # Create players table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id TEXT PRIMARY KEY,
            quiz_id TEXT NOT NULL,
            username TEXT NOT NULL,
            score INTEGER DEFAULT 0,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (quiz_id) REFERENCES quizzes(id),
            UNIQUE(quiz_id, username)
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
            FOREIGN KEY (player_id) REFERENCES players(id),
            UNIQUE(player_id, quiz_id, day_number)
        )
    """)
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

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
    host_id = str(uuid.uuid4())
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO quizzes (id, host_id, created_at, started)
        VALUES (?, ?, ?, 0)
    """, (quiz_id, host_id, datetime.now()))
    
    conn.commit()
    conn.close()
    
    return {
        "quiz_id": quiz_id,
        "host_id": host_id,
        "join_link": f"{FRONTEND_URL}/join/{quiz_id}"
    }

@app.get("/api/quiz/{quiz_id}")
def get_quiz(quiz_id: str):
    """Get quiz details"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, host_id, created_at, started
        FROM quizzes WHERE id = ?
    """, (quiz_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    return {
        "id": row[0],
        "host_id": row[1],
        "created_at": row[2],
        "started": bool(row[3])
    }

@app.post("/api/quiz/{quiz_id}/join")
def join_quiz(quiz_id: str, player: Player):
    """Add a player to the quiz or rejoin with existing username"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if quiz exists
    cursor.execute("SELECT started FROM quizzes WHERE id = ?", (quiz_id,))
    quiz_row = cursor.fetchone()
    
    if not quiz_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Check if username already exists in this quiz
    cursor.execute("""
        SELECT id, score FROM players WHERE quiz_id = ? AND username = ?
    """, (quiz_id, player.username))
    
    existing_player = cursor.fetchone()
    
    if existing_player:
        # Player is rejoining - return their existing data
        conn.close()
        return {
            "player_id": existing_player[0],
            "username": player.username,
            "quiz_id": quiz_id,
            "score": existing_player[1],
            "rejoined": True
        }
    
    # New player joining
    if quiz_row[0]:  # started is True
        conn.close()
        raise HTTPException(status_code=400, detail="Quiz already started, cannot join as a new player")
    
    player_id = str(uuid.uuid4())
    
    cursor.execute("""
        INSERT INTO players (id, quiz_id, username, score, joined_at)
        VALUES (?, ?, ?, 0, ?)
    """, (player_id, quiz_id, player.username, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    
    return {
        "player_id": player_id,
        "username": player.username,
        "quiz_id": quiz_id,
        "score": 0,
        "rejoined": False
    }

@app.get("/api/quiz/{quiz_id}/players")
def get_players(quiz_id: str):
    """Get all players in a quiz"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if quiz exists
    cursor.execute("SELECT id FROM quizzes WHERE id = ?", (quiz_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Get all players
    cursor.execute("""
        SELECT id, username, score, joined_at
        FROM players WHERE quiz_id = ?
        ORDER BY joined_at
    """, (quiz_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    players = [
        {
            "id": row[0],
            "username": row[1],
            "score": row[2],
            "joined_at": row[3]
        }
        for row in rows
    ]
    
    return {"players": players}

@app.get("/api/quiz/{quiz_id}/leaderboard")
def get_leaderboard(quiz_id: str):
    """Get leaderboard for a quiz with players ranked by score"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if quiz exists
    cursor.execute("SELECT id FROM quizzes WHERE id = ?", (quiz_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Get all players ranked by score (highest first)
    cursor.execute("""
        SELECT id, username, score
        FROM players WHERE quiz_id = ?
        ORDER BY score DESC, joined_at ASC
    """, (quiz_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    leaderboard = []
    current_rank = 1
    for idx, row in enumerate(rows):
        leaderboard.append({
            "rank": current_rank,
            "player_id": row[0],
            "username": row[1],
            "score": row[2]
        })
        # Only increment rank if next player has different score
        if idx + 1 < len(rows) and rows[idx + 1][2] != row[2]:
            current_rank = idx + 2
    
    return {"leaderboard": leaderboard}

@app.post("/api/quiz/{quiz_id}/start")
def start_quiz(quiz_id: str, host_id: str):
    """Start the quiz (only host can start)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get quiz details
    cursor.execute("""
        SELECT host_id, started FROM quizzes WHERE id = ?
    """, (quiz_id,))
    
    quiz_row = cursor.fetchone()
    
    if not quiz_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    if quiz_row[0] != host_id:
        conn.close()
        raise HTTPException(status_code=403, detail="Only host can start the quiz")
    
    # Check if there are players
    cursor.execute("SELECT COUNT(*) FROM players WHERE quiz_id = ?", (quiz_id,))
    player_count = cursor.fetchone()[0]
    
    if player_count == 0:
        conn.close()
        raise HTTPException(status_code=400, detail="Need at least one player to start")
    
    # Start the quiz
    cursor.execute("UPDATE quizzes SET started = 1 WHERE id = ?", (quiz_id,))
    conn.commit()
    conn.close()
    
    return {"message": "Quiz started!", "started": True}

@app.put("/api/player/{player_id}/score")
def update_score(player_id: str, score: int):
    """Update player score"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM players WHERE id = ?", (player_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Player not found")
    
    cursor.execute("UPDATE players SET score = ? WHERE id = ?", (score, player_id))
    conn.commit()
    conn.close()
    
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
    
    # Check if player must complete previous day first (sequential access)
    if day_number > 1:
        cursor.execute("""
            SELECT id FROM player_answers 
            WHERE player_id = ? AND quiz_id = ? AND day_number = ?
        """, (submission.player_id, submission.quiz_id, day_number - 1))
        
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(
                status_code=403, 
                detail=f"Must complete day {day_number - 1} before accessing day {day_number}"
            )
    
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
    
    # Update player's score in database
    cursor.execute("UPDATE players SET score = ? WHERE id = ?", (total_score, submission.player_id))
    conn.commit()
    conn.close()
    
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

@app.get("/api/player/{player_id}/quiz/{quiz_id}/can-access/{day_number}")
def can_access_day(player_id: str, quiz_id: str, day_number: int):
    """Check if a player can access a specific day (must complete previous days in order)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Day 1 is always accessible
    if day_number == 1:
        conn.close()
        return {"can_access": True, "reason": "First day is always accessible"}
    
    # Check if previous day was completed
    cursor.execute("""
        SELECT id FROM player_answers 
        WHERE player_id = ? AND quiz_id = ? AND day_number = ?
    """, (player_id, quiz_id, day_number - 1))
    
    if cursor.fetchone():
        conn.close()
        return {"can_access": True, "reason": f"Day {day_number - 1} completed"}
    else:
        conn.close()
        return {"can_access": False, "reason": f"Must complete day {day_number - 1} first"}

