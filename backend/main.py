from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
import sqlite3
import os
from dotenv import load_dotenv
import bcrypt
import jwt
import ollama
import re
from pathlib import Path
from answer_validator import validate_answer, get_validation_rule, ValidationRule

# Load environment variables from .env file
load_dotenv()

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24 * 30  # 30 days

# Ollama Configuration
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")  # Can be changed to mistral, llama3, etc.
USE_OLLAMA = os.getenv("USE_OLLAMA", "true").lower() == "true"
OLLAMA_CONFIDENCE_THRESHOLD = int(os.getenv("OLLAMA_CONFIDENCE_THRESHOLD", "80"))  # 80% minimum confidence

security = HTTPBearer()

app = FastAPI()

# Frontend URL configuration - can be set via environment variable
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (simplest for development with ngrok)
    allow_credentials=False,  # Must be False when allow_origins is "*"
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Add middleware to handle OPTIONS requests explicitly
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    if request.method == "OPTIONS":
        return Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Max-Age": "3600",
            }
        )
    response = await call_next(request)
    return response

# Database setup
DB_PATH = "quiz_database.db"

# Create images directory if it doesn't exist
IMAGES_DIR = Path("images")
IMAGES_DIR.mkdir(exist_ok=True)

# Mount static files for images AFTER CORS middleware
app.mount("/images", StaticFiles(directory="images"), name="images")

def get_full_image_url(image_path: str, request) -> str:
    """Convert relative image paths to full URLs"""
    if not image_path:
        return None
    
    # If it's already a full URL (starts with http:// or https://), return as-is
    if image_path.startswith('http://') or image_path.startswith('https://'):
        return image_path
    
    # If it's a relative path starting with /images/, convert to API endpoint
    if image_path.startswith('/images/'):
        base_url = str(request.base_url).rstrip('/')
        filename = image_path.replace('/images/', '')
        return f"{base_url}/api/image/{filename}"
    
    return image_path

def init_db():
    """Initialize the database with all required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create questions table (standard questions - not linked to user)
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
    
    # Create custom_question_sets table (user's custom question sets)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_question_sets (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            is_default BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Create custom_questions table (questions in custom sets)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_set_id TEXT NOT NULL,
            day_number INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            image_1 TEXT,
            image_2 TEXT,
            image_3 TEXT,
            image_4 TEXT,
            image_5 TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (question_set_id) REFERENCES custom_question_sets(id),
            UNIQUE(question_set_id, day_number)
        )
    """)
    
    # Create quizzes table (updated to link to user and question set)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quizzes (
            id TEXT PRIMARY KEY,
            host_id TEXT NOT NULL,
            user_id TEXT,
            question_set_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started BOOLEAN DEFAULT 0,
            completed BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (question_set_id) REFERENCES custom_question_sets(id)
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
            ai_verified BOOLEAN DEFAULT 0,
            ai_confidence INTEGER,
            ai_reasoning TEXT,
            FOREIGN KEY (player_id) REFERENCES players(id),
            UNIQUE(player_id, quiz_id, day_number)
        )
    """)
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# Pydantic Models
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Player(BaseModel):
    username: str

class Quiz(BaseModel):
    id: str
    host_id: str
    created_at: datetime
    started: bool
    players: List[dict]

class QuizCreate(BaseModel):
    question_set_id: Optional[str] = None  # If None, use standard questions

class Question(BaseModel):
    day_number: int
    question_text: str
    correct_answer: str
    image_1: Optional[str] = None
    image_2: Optional[str] = None
    image_3: Optional[str] = None
    image_4: Optional[str] = None
    image_5: Optional[str] = None

class CustomQuestionSetCreate(BaseModel):
    name: str

class AnswerSubmission(BaseModel):
    player_id: str
    quiz_id: str
    answer: str

# Helper Functions
def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(user_id: str, username: str) -> str:
    """Create JWT access token"""
    expires = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode = {
        "sub": user_id,
        "username": username,
        "exp": expires
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verify JWT token and return user data"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {
            "user_id": payload.get("sub"),
            "username": payload.get("username")
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

def check_answer_with_ai(player_answer: str, correct_answer: str, day_number: int = None) -> dict:
    """
    Check if player's answer matches the correct answer.
    Uses rule-based validation first, with AI as fallback.
    Returns dict with: is_match (bool), confidence (int 0-100), reasoning (str), method (str)
    """
    # Try rule-based validation first if we have a rule for this day
    if day_number is not None:
        validation_rule = get_validation_rule(day_number)
        if validation_rule:
            print(f"📋 RULE-BASED CHECK (Day {day_number}) - Player: '{player_answer}'")
            result = validate_answer(player_answer, validation_rule)
            
            # If rule-based validation worked, return the result
            if result is not None:
                print(f"{'✓' if result['is_correct'] else '✗'} {result['reasoning']}")
                return {
                    "is_match": result["is_correct"],
                    "confidence": result["confidence"],
                    "reasoning": result["reasoning"],
                    "method": result["method"]
                }
            
            # If result is None, fall through to AI validation
            print(f"⚠️ Rule returned None, falling back to AI for day {day_number}")
    
    # Fallback: check for exact match (fast path)
    is_exact = player_answer.strip().lower() == correct_answer.strip().lower()
    if is_exact:
        print(f"✓ EXACT MATCH - Player: '{player_answer}' | Correct: '{correct_answer}'")
        return {
            "is_match": True,
            "confidence": 100,
            "reasoning": "Exact match",
            "method": "exact"
        }
    
    # Not an exact match - check if AI is enabled
    print(f"🤖 AI CHECK - Player: '{player_answer}' | Correct: '{correct_answer}' | USE_OLLAMA: {USE_OLLAMA}")
    
    if not USE_OLLAMA:
        # Ollama is disabled, return no match
        return {
            "is_match": False,
            "confidence": 0,
            "reasoning": "No exact match (AI disabled)",
            "method": "exact"
        }
    
    try:
        prompt = f"""Compare these two answers and determine if they match, considering:
- Minor spelling mistakes (e.g., "Cristmas" vs "Christmas", "tvspel" vs "tv-spel")
- Different wordings that mean the same thing (e.g., "Santa Claus" vs "Father Christmas")
- Partial answers that capture the essential meaning
- Capitalization and punctuation differences
- For lists: items can be in any order, separators can vary (commas, "och"/"and", etc.)
- For lists: matching items even with spelling variations counts as correct

Player's answer: "{player_answer}"
Correct answer: "{correct_answer}"

If these are lists, check if they contain the same items (order doesn't matter).
Spelling variations and different separators (comma, "och", "and") should be accepted.

Respond ONLY in this exact format:
MATCH: YES or NO
CONFIDENCE: [0-100]
REASONING: [brief explanation]

Example response:
MATCH: YES
CONFIDENCE: 95
REASONING: Same list items in different order with minor spelling variations"""

        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{
                'role': 'user',
                'content': prompt
            }],
            options={
                'temperature': 0.1,  # Low temperature for more consistent results
                'num_predict': 100   # Limit response length
            }
        )
        
        response_text = response['message']['content'].strip()
        print(f"AI RESPONSE: {response_text}")
        
        # Parse the response
        match_line = re.search(r'MATCH:\s*(YES|NO)', response_text, re.IGNORECASE)
        confidence_line = re.search(r'CONFIDENCE:\s*(\d+)', response_text)
        reasoning_line = re.search(r'REASONING:\s*(.+)', response_text, re.IGNORECASE)
        
        if not match_line or not confidence_line:
            raise ValueError("Invalid AI response format")
        
        is_match = match_line.group(1).upper() == "YES"
        confidence = int(confidence_line.group(1))
        reasoning = reasoning_line.group(1).strip() if reasoning_line else "AI evaluation"
        
        # Only accept if confidence meets threshold
        if is_match and confidence < OLLAMA_CONFIDENCE_THRESHOLD:
            is_match = False
            reasoning = f"Confidence {confidence}% below threshold {OLLAMA_CONFIDENCE_THRESHOLD}%"
        
        return {
            "is_match": is_match,
            "confidence": confidence,
            "reasoning": reasoning,
            "method": "ai"
        }
        
    except Exception as e:
        print(f"Ollama error: {e}. Falling back to exact match.")
        # Fallback to exact match on error
        is_exact = player_answer.strip().lower() == correct_answer.strip().lower()
        return {
            "is_match": is_exact,
            "confidence": 100 if is_exact else 0,
            "reasoning": f"AI unavailable, used exact match. Error: {str(e)}",
            "method": "exact_fallback"
        }

@app.get("/")
def root():
    return {"message": "Quiz API is running!"}

# Authentication Endpoints
@app.post("/api/auth/register")
def register(user: UserRegister):
    """Register a new user"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if username or email already exists
    cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", 
                  (user.username, user.email))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )
    
    # Create new user
    user_id = str(uuid.uuid4())
    password_hash = hash_password(user.password)
    
    cursor.execute("""
        INSERT INTO users (id, username, email, password_hash, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, user.username, user.email, password_hash, datetime.now()))
    
    conn.commit()
    conn.close()
    
    # Create access token
    token = create_access_token(user_id, user.username)
    
    return {
        "user_id": user_id,
        "username": user.username,
        "email": user.email,
        "access_token": token,
        "token_type": "bearer"
    }

@app.post("/api/auth/login")
def login(credentials: UserLogin):
    """Login and get access token"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, username, email, password_hash 
        FROM users WHERE email = ?
    """, (credentials.email,))
    
    user = cursor.fetchone()
    conn.close()
    
    if not user or not verify_password(credentials.password, user[3]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Create access token
    token = create_access_token(user[0], user[1])
    
    return {
        "user_id": user[0],
        "username": user[1],
        "email": user[2],
        "access_token": token,
        "token_type": "bearer"
    }

@app.get("/api/auth/me")
def get_current_user(user_data: dict = Depends(verify_token)):
    """Get current user information"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, username, email, created_at 
        FROM users WHERE id = ?
    """, (user_data["user_id"],))
    
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "user_id": user[0],
        "username": user[1],
        "email": user[2],
        "created_at": user[3]
    }

@app.post("/api/quiz/create")
def create_quiz(quiz_data: Optional[QuizCreate] = None, user_data: dict = Depends(verify_token)):
    """Create a new quiz (authenticated users only)"""
    quiz_id = str(uuid.uuid4())[:8]  # Short unique ID
    host_id = str(uuid.uuid4())
    
    question_set_id = quiz_data.question_set_id if quiz_data else None
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # If question_set_id provided, verify it belongs to the user
    if question_set_id:
        cursor.execute("""
            SELECT id FROM custom_question_sets 
            WHERE id = ? AND user_id = ?
        """, (question_set_id, user_data["user_id"]))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question set not found or does not belong to user"
            )
    
    cursor.execute("""
        INSERT INTO quizzes (id, host_id, user_id, question_set_id, created_at, started)
        VALUES (?, ?, ?, ?, ?, 0)
    """, (quiz_id, host_id, user_data["user_id"], question_set_id, datetime.now()))
    
    conn.commit()
    conn.close()
    
    return {
        "quiz_id": quiz_id,
        "host_id": host_id,
        "user_id": user_data["user_id"],
        "question_set_id": question_set_id,
        "join_link": f"{FRONTEND_URL}/join/{quiz_id}"
    }

@app.get("/api/quiz/{quiz_id}/check")
def check_quiz_exists(quiz_id: str):
    """Public endpoint to check if a quiz exists (for join page)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, started FROM quizzes WHERE id = ?
    """, (quiz_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    return {
        "id": row[0],
        "started": bool(row[1])
    }

@app.get("/api/quiz/{quiz_id}")
def get_quiz(quiz_id: str, user_data: dict = Depends(verify_token)):
    """Get quiz details - requires authentication and ownership"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, user_id, created_at, started, question_set_id
        FROM quizzes WHERE id = ?
    """, (quiz_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Verify ownership
    if row[1] != user_data["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied - not the quiz owner")
    
    return {
        "quiz_id": row[0],
        "user_id": row[1],
        "created_at": row[2],
        "started": bool(row[3]),
        "question_set_id": row[4]
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
            "player_id": row[0],
            "player_name": row[1],
            "id": row[0],  # Keep for backward compatibility
            "username": row[1],  # Keep for backward compatibility
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

# Custom Question Set Endpoints
@app.post("/api/question-sets")
def create_question_set(data: CustomQuestionSetCreate, user_data: dict = Depends(verify_token)):
    """Create a new custom question set for a user"""
    question_set_id = str(uuid.uuid4())
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO custom_question_sets (id, user_id, name, created_at)
        VALUES (?, ?, ?, ?)
    """, (question_set_id, user_data["user_id"], data.name, datetime.now()))
    
    conn.commit()
    conn.close()
    
    return {
        "question_set_id": question_set_id,
        "name": data.name,
        "user_id": user_data["user_id"]
    }

@app.get("/api/images")
def list_available_images():
    """Get list of available images in the images directory"""
    images = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.webp']:
        images.extend([f.name for f in IMAGES_DIR.glob(ext)])
    
    return {
        "images": [
            {
                "name": img,
                "url": f"/api/image/{img}"
            }
            for img in sorted(images)
        ]
    }

@app.get("/api/image/{filename}")
def get_image(filename: str):
    """Serve an image file from the images directory"""
    file_path = IMAGES_DIR / filename
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Security check - make sure the file is actually in the images directory
    if not str(file_path.resolve()).startswith(str(IMAGES_DIR.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return FileResponse(file_path)

@app.get("/api/question-sets")
def get_user_question_sets(user_data: dict = Depends(verify_token)):
    """Get all question sets for the current user"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, is_default, created_at,
               (SELECT COUNT(*) FROM custom_questions WHERE question_set_id = custom_question_sets.id) as question_count
        FROM custom_question_sets 
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_data["user_id"],))
    
    rows = cursor.fetchall()
    conn.close()
    
    question_sets = [
        {
            "id": row[0],
            "name": row[1],
            "is_default": bool(row[2]),
            "created_at": row[3],
            "question_count": row[4]
        }
        for row in rows
    ]
    
    return {"question_sets": question_sets}

@app.post("/api/question-sets/{set_id}/questions")
def create_custom_question(set_id: str, question: Question, user_data: dict = Depends(verify_token)):
    """Add a question to a custom question set"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verify the question set belongs to the user
    cursor.execute("""
        SELECT id FROM custom_question_sets WHERE id = ? AND user_id = ?
    """, (set_id, user_data["user_id"]))
    
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question set not found"
        )
    
    # Check if question already exists for this day
    cursor.execute("""
        SELECT id, question_text FROM custom_questions 
        WHERE question_set_id = ? AND day_number = ?
    """, (set_id, question.day_number))
    
    existing = cursor.fetchone()
    if existing:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Question for day {question.day_number} already exists in this set (ID: {existing[0]}). Delete it first or choose a different day."
        )
    
    try:
        cursor.execute("""
            INSERT INTO custom_questions 
            (question_set_id, day_number, question_text, correct_answer, image_1, image_2, image_3, image_4, image_5)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (set_id, question.day_number, question.question_text, question.correct_answer,
              question.image_1, question.image_2, question.image_3, question.image_4, question.image_5))
        
        conn.commit()
        question_id = cursor.lastrowid
        conn.close()
        
        return {"message": "Custom question created", "id": question_id}
    except sqlite3.IntegrityError as e:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database constraint error: {str(e)}"
        )

@app.get("/api/question-sets/{set_id}/questions")
def get_custom_questions(set_id: str, request: Request, user_data: dict = Depends(verify_token)):
    """Get all questions in a custom question set"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verify the question set belongs to the user
    cursor.execute("""
        SELECT id FROM custom_question_sets WHERE id = ? AND user_id = ?
    """, (set_id, user_data["user_id"]))
    
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question set not found"
        )
    
    cursor.execute("""
        SELECT id, day_number, question_text, correct_answer, image_1, image_2, image_3, image_4, image_5
        FROM custom_questions
        WHERE question_set_id = ?
        ORDER BY day_number
    """, (set_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    questions = [
        {
            "id": row[0],
            "day_number": row[1],
            "question_text": row[2],
            "correct_answer": row[3],
            "image_1": row[4],
            "image_2": row[5],
            "image_3": row[6],
            "image_4": row[7],
            "image_5": row[8],
            "images": [get_full_image_url(img, request) for img in [row[4], row[5], row[6], row[7], row[8]] if img]
        }
        for row in rows
    ]
    
    return {"questions": questions}

@app.put("/api/question-sets/{set_id}/questions/{day_number}")
def update_custom_question(set_id: str, day_number: int, data: Question, user_data: dict = Depends(verify_token)):
    """Update a specific question in a custom question set"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verify the question set belongs to the user
    cursor.execute("""
        SELECT id FROM custom_question_sets WHERE id = ? AND user_id = ?
    """, (set_id, user_data["user_id"]))
    
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question set not found"
        )
    
    # Check if question exists
    cursor.execute("""
        SELECT id FROM custom_questions 
        WHERE question_set_id = ? AND day_number = ?
    """, (set_id, day_number))
    
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question for day {day_number} not found in this set"
        )
    
    # Update the question
    cursor.execute("""
        UPDATE custom_questions 
        SET question_text = ?, correct_answer = ?,
            image_1 = ?, image_2 = ?, image_3 = ?, image_4 = ?, image_5 = ?
        WHERE question_set_id = ? AND day_number = ?
    """, (
        data.question_text,
        data.correct_answer,
        data.image_1 or None,
        data.image_2 or None,
        data.image_3 or None,
        data.image_4 or None,
        data.image_5 or None,
        set_id,
        day_number
    ))
    
    conn.commit()
    conn.close()
    
    return {"message": "Question updated successfully"}

@app.delete("/api/question-sets/{set_id}/questions/{day_number}")
def delete_custom_question(set_id: str, day_number: int, user_data: dict = Depends(verify_token)):
    """Delete a specific question from a custom question set"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verify the question set belongs to the user
    cursor.execute("""
        SELECT id FROM custom_question_sets WHERE id = ? AND user_id = ?
    """, (set_id, user_data["user_id"]))
    
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question set not found"
        )
    
    # Delete the question
    cursor.execute("""
        DELETE FROM custom_questions 
        WHERE question_set_id = ? AND day_number = ?
    """, (set_id, day_number))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question for day {day_number} not found in this set"
        )
    
    conn.commit()
    conn.close()
    
    return {"message": f"Question for day {day_number} deleted successfully"}

@app.delete("/api/question-sets/{set_id}")
def delete_question_set(set_id: str, user_data: dict = Depends(verify_token)):
    """Delete a custom question set and all its questions"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verify the question set belongs to the user
    cursor.execute("""
        SELECT id FROM custom_question_sets WHERE id = ? AND user_id = ?
    """, (set_id, user_data["user_id"]))
    
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question set not found"
        )
    
    # Delete all questions in the set
    cursor.execute("DELETE FROM custom_questions WHERE question_set_id = ?", (set_id,))
    
    # Delete the question set
    cursor.execute("DELETE FROM custom_question_sets WHERE id = ?", (set_id,))
    
    conn.commit()
    conn.close()
    
    return {"message": "Question set deleted"}

@app.put("/api/question-sets/{set_id}/default")
def set_default_question_set(set_id: str, user_data: dict = Depends(verify_token)):
    """Set a question set as the default for this user"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verify the question set belongs to the user
    cursor.execute("""
        SELECT id FROM custom_question_sets WHERE id = ? AND user_id = ?
    """, (set_id, user_data["user_id"]))
    
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question set not found"
        )
    
    # Remove default from all user's question sets
    cursor.execute("""
        UPDATE custom_question_sets SET is_default = 0 WHERE user_id = ?
    """, (user_data["user_id"],))
    
    # Set this one as default
    cursor.execute("""
        UPDATE custom_question_sets SET is_default = 1 WHERE id = ?
    """, (set_id,))
    
    conn.commit()
    conn.close()
    
    return {"message": "Default question set updated"}

# Quiz History Endpoints
@app.get("/api/user/quiz-history")
def get_quiz_history(user_data: dict = Depends(verify_token)):
    """Get all quizzes hosted by the current user"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get the total number of questions available
    cursor.execute("SELECT COUNT(*) FROM questions")
    total_questions = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT q.id, q.created_at, q.started, q.completed,
               COUNT(DISTINCT p.id) as player_count,
               MAX(p.score) as top_score,
               cqs.name as question_set_name,
               q.question_set_id
        FROM quizzes q
        LEFT JOIN players p ON q.id = p.quiz_id
        LEFT JOIN custom_question_sets cqs ON q.question_set_id = cqs.id
        WHERE q.user_id = ?
        GROUP BY q.id
        ORDER BY q.created_at DESC
    """, (user_data["user_id"],))
    
    rows = cursor.fetchall()
    
    quizzes = []
    for row in rows:
        quiz_id = row[0]
        player_count = row[4]
        question_set_id = row[7]
        
        # Determine number of questions for this quiz
        if question_set_id:
            cursor.execute("SELECT COUNT(*) FROM custom_questions WHERE question_set_id = ?", (question_set_id,))
            num_questions = cursor.fetchone()[0]
        else:
            num_questions = total_questions
        
        # Check if all players have answered all questions
        all_completed = False
        if player_count > 0 and num_questions > 0:
            cursor.execute("""
                SELECT COUNT(*) FROM players p
                WHERE p.quiz_id = ?
                AND (SELECT COUNT(*) FROM player_answers WHERE player_id = p.id AND quiz_id = p.quiz_id) = ?
            """, (quiz_id, num_questions))
            completed_players = cursor.fetchone()[0]
            all_completed = completed_players == player_count
        
        quizzes.append({
            "quiz_id": row[0],
            "created_at": row[1],
            "started": bool(row[2]),
            "completed": bool(row[3]),
            "player_count": player_count,
            "top_score": row[5] or 0,
            "question_set_name": row[6] or "Standard Questions",
            "all_completed": all_completed
        })
    
    conn.close()
    return {"quizzes": quizzes}

@app.delete("/api/quiz/{quiz_id}")
def delete_quiz(quiz_id: str, user_data: dict = Depends(verify_token)):
    """Delete a quiz and all associated data"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verify the quiz belongs to the user
    cursor.execute("""
        SELECT id FROM quizzes WHERE id = ? AND user_id = ?
    """, (quiz_id, user_data["user_id"]))
    
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    # Delete all player answers for this quiz
    cursor.execute("DELETE FROM player_answers WHERE quiz_id = ?", (quiz_id,))
    
    # Delete all players for this quiz
    cursor.execute("DELETE FROM players WHERE quiz_id = ?", (quiz_id,))
    
    # Delete the quiz itself
    cursor.execute("DELETE FROM quizzes WHERE id = ?", (quiz_id,))
    
    conn.commit()
    conn.close()
    
    return {"message": "Quiz deleted successfully"}

@app.get("/api/quiz/{quiz_id}/results")
def get_quiz_results(quiz_id: str, user_data: dict = Depends(verify_token)):
    """Get detailed results for a specific quiz"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verify the quiz belongs to the user
    cursor.execute("""
        SELECT id FROM quizzes WHERE id = ? AND user_id = ?
    """, (quiz_id, user_data["user_id"]))
    
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    # Get player results
    cursor.execute("""
        SELECT p.id, p.username, p.score,
               COUNT(pa.id) as questions_answered,
               SUM(CASE WHEN pa.is_correct = 1 THEN 1 ELSE 0 END) as correct_answers
        FROM players p
        LEFT JOIN player_answers pa ON p.id = pa.player_id AND p.quiz_id = pa.quiz_id
        WHERE p.quiz_id = ?
        GROUP BY p.id
        ORDER BY p.score DESC
    """, (quiz_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    players = [
        {
            "player_id": row[0],
            "username": row[1],
            "score": row[2],
            "questions_answered": row[3] or 0,
            "correct_answers": row[4] or 0
        }
        for row in rows
    ]
    
    return {"players": players}

@app.get("/api/quiz/{quiz_id}/player/{player_id}/answers")
def get_player_answers(quiz_id: str, player_id: str, user_data: dict = Depends(verify_token)):
    """Get all answers for a specific player in a quiz"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verify the quiz belongs to the user
    cursor.execute("""
        SELECT id, question_set_id FROM quizzes WHERE id = ? AND user_id = ?
    """, (quiz_id, user_data["user_id"]))
    
    quiz_row = cursor.fetchone()
    if not quiz_row:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    question_set_id = quiz_row[1]
    
    # Get player answers with question details
    cursor.execute("""
        SELECT pa.day_number, pa.answer, pa.is_correct, pa.points_earned, pa.answered_at,
               COALESCE(cq.question_text, q.question_text) as question_text,
               COALESCE(cq.correct_answer, q.correct_answer) as correct_answer,
               pa.ai_verified, pa.ai_confidence, pa.ai_reasoning
        FROM player_answers pa
        LEFT JOIN custom_questions cq ON pa.day_number = cq.day_number AND cq.question_set_id = ?
        LEFT JOIN questions q ON pa.day_number = q.day_number
        WHERE pa.player_id = ? AND pa.quiz_id = ?
        ORDER BY pa.day_number
    """, (question_set_id, player_id, quiz_id))
    
    rows = cursor.fetchall()
    conn.close()
    
    answers = [
        {
            "day_number": row[0],
            "player_answer": row[1],
            "is_correct": bool(row[2]),
            "points_earned": row[3],
            "answered_at": row[4],
            "question_text": row[5],
            "correct_answer": row[6],
            "ai_verified": bool(row[7]) if row[7] is not None else False,
            "ai_confidence": row[8],
            "ai_reasoning": row[9]
        }
        for row in rows
    ]
    
    return {"answers": answers}

class ScoreUpdate(BaseModel):
    score: int

@app.put("/api/quiz/{quiz_id}/player/{player_id}/score")
def update_player_score(quiz_id: str, player_id: str, score_update: ScoreUpdate, user_data: dict = Depends(verify_token)):
    """Update a player's total score"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verify the quiz belongs to the user
    cursor.execute("""
        SELECT id FROM quizzes WHERE id = ? AND user_id = ?
    """, (quiz_id, user_data["user_id"]))
    
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    # Update player score
    cursor.execute("""
        UPDATE players SET score = ? WHERE id = ? AND quiz_id = ?
    """, (score_update.score, player_id, quiz_id))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player not found"
        )
    
    conn.commit()
    conn.close()
    
    return {"message": "Score updated successfully", "new_score": score_update.score}

class AnswerUpdate(BaseModel):
    is_correct: bool
    points_earned: int

@app.get("/api/quiz/{quiz_id}/player/{player_id}/answer/{day_number}")
def check_player_answer(quiz_id: str, player_id: str, day_number: int):
    """Check if a player has answered a specific day"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id FROM player_answers 
        WHERE quiz_id = ? AND player_id = ? AND day_number = ?
    """, (quiz_id, player_id, day_number))
    
    answer = cursor.fetchone()
    conn.close()
    
    if answer:
        return {"has_answered": True}
    else:
        raise HTTPException(status_code=404, detail="No answer found")

@app.put("/api/quiz/{quiz_id}/player/{player_id}/answer/{day_number}")
def update_player_answer(quiz_id: str, player_id: str, day_number: int, answer_update: AnswerUpdate, user_data: dict = Depends(verify_token)):
    """Update a player's answer (toggle correctness and points)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verify the quiz belongs to the user
    cursor.execute("""
        SELECT id FROM quizzes WHERE id = ? AND user_id = ?
    """, (quiz_id, user_data["user_id"]))
    
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    # Get old points to calculate score difference
    cursor.execute("""
        SELECT points_earned FROM player_answers 
        WHERE player_id = ? AND quiz_id = ? AND day_number = ?
    """, (player_id, quiz_id, day_number))
    
    old_row = cursor.fetchone()
    if not old_row:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Answer not found"
        )
    
    old_points = old_row[0]
    points_difference = answer_update.points_earned - old_points
    
    # Update the answer
    cursor.execute("""
        UPDATE player_answers 
        SET is_correct = ?, points_earned = ?
        WHERE player_id = ? AND quiz_id = ? AND day_number = ?
    """, (answer_update.is_correct, answer_update.points_earned, player_id, quiz_id, day_number))
    
    # Update player's total score
    cursor.execute("""
        UPDATE players 
        SET score = score + ?
        WHERE id = ? AND quiz_id = ?
    """, (points_difference, player_id, quiz_id))
    
    conn.commit()
    conn.close()
    
    return {
        "message": "Answer updated successfully",
        "is_correct": answer_update.is_correct,
        "points_earned": answer_update.points_earned,
        "points_difference": points_difference
    }

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
def get_question(day_number: int, request: Request, quiz_id: Optional[str] = None):
    """Get question for a specific day (from custom set if quiz uses one, otherwise standard)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    question_set_id = None
    
    # If quiz_id provided, check if it uses a custom question set
    if quiz_id:
        cursor.execute("""
            SELECT question_set_id FROM quizzes WHERE id = ?
        """, (quiz_id,))
        quiz_row = cursor.fetchone()
        if quiz_row:
            question_set_id = quiz_row[0]
    
    # Try to get question from custom set first
    if question_set_id:
        cursor.execute("""
            SELECT day_number, question_text, image_1, image_2, image_3, image_4, image_5
            FROM custom_questions WHERE question_set_id = ? AND day_number = ?
        """, (question_set_id, day_number))
        row = cursor.fetchone()
    else:
        row = None
    
    # Fall back to standard questions if no custom question found
    if not row:
        cursor.execute("""
            SELECT day_number, question_text, image_1, image_2, image_3, image_4, image_5
            FROM questions WHERE day_number = ?
        """, (day_number,))
        row = cursor.fetchone()
    
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Collect images that are not null and convert to full URLs
    raw_images = [img for img in [row[2], row[3], row[4], row[5], row[6]] if img]
    images = [get_full_image_url(img, request) for img in raw_images]
    
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
    
    # Get the quiz's question_set_id
    cursor.execute("SELECT question_set_id FROM quizzes WHERE id = ?", (submission.quiz_id,))
    quiz_row = cursor.fetchone()
    question_set_id = quiz_row[0] if quiz_row else None
    
    # Get the correct answer (try custom questions first, then standard)
    if question_set_id:
        cursor.execute("""
            SELECT correct_answer FROM custom_questions 
            WHERE question_set_id = ? AND day_number = ?
        """, (question_set_id, day_number))
        row = cursor.fetchone()
    else:
        row = None
    
    # Fall back to standard questions
    if not row:
        cursor.execute("SELECT correct_answer FROM questions WHERE day_number = ?", (day_number,))
        row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Question not found")
    
    correct_answer = row[0]
    user_answer = submission.answer
    
    # Use rule-based validation first, then AI if needed
    check_result = check_answer_with_ai(user_answer, correct_answer, day_number)
    is_correct = check_result["is_match"]
    points_earned = 10 if is_correct else 0
    
    # Extract AI metadata
    ai_verified = check_result["method"] == "ai"
    ai_confidence = check_result["confidence"] if ai_verified else None
    ai_reasoning = check_result["reasoning"] if ai_verified else None
    
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
        INSERT INTO player_answers (player_id, quiz_id, day_number, answer, is_correct, points_earned, ai_verified, ai_confidence, ai_reasoning)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (submission.player_id, submission.quiz_id, day_number, submission.answer, is_correct, points_earned, ai_verified, ai_confidence, ai_reasoning))
    
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

