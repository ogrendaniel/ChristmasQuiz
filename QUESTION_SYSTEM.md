# Question System Setup

## Database Structure

The system uses SQLite with two tables:

### `questions` table:
- `day_number` (1-24) - The advent calendar day
- `question_text` - The actual question
- `correct_answer` - The correct answer (case-insensitive matching)
- `image_1` to `image_5` - Optional image URLs/paths

### `player_answers` table:
- Tracks which questions each player has answered
- Records if answer was correct
- Stores points earned
- Prevents duplicate answers

## Setup Instructions

1. **Make sure backend is running:**
   ```bash
   cd backend
   python -m uvicorn main:app --reload
   ```

2. **Add sample questions:**
   ```bash
   cd backend
   pip install requests
   python add_sample_questions.py
   ```

3. **Frontend will now load questions!**

## API Endpoints

- `POST /api/questions` - Create a question (admin)
- `GET /api/questions/{day_number}` - Get question (excludes correct answer)
- `POST /api/questions/{day_number}/answer` - Submit answer and get result
- `GET /api/player/{player_id}/quiz/{quiz_id}/answered` - Get answered questions

## Question Page Features

✅ **Dynamic image grid:**
- 1 image: Full width
- 2 images: Side by side
- 3 images: 2 top, 1 bottom
- 4 images: 2x2 grid
- 5 images: 3 top, 2 bottom

✅ **Answer checking:**
- Case-insensitive matching
- 10 points per correct answer
- Shows popup with result
- Prevents duplicate answers

✅ **Score tracking:**
- Updates player's total score
- Shows in result popup
- Syncs with main player list

## Adding Your Own Questions

You can add questions via the API or by directly modifying `add_sample_questions.py`:

```python
{
    "day_number": 1,
    "question_text": "Your question here?",
    "correct_answer": "The answer",
    "image_1": "https://example.com/image1.jpg",  # Optional
    "image_2": "https://example.com/image2.jpg",  # Optional
    "image_3": None,
    "image_4": None,
    "image_5": None
}
```

Images can be:
- URLs (http://... or https://...)
- Paths to files in the public folder (/images/myimage.jpg)
- Base64 encoded images (for embedding)
