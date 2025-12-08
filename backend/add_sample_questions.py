import requests
import json

# Base URL for the API
BASE_URL = "http://localhost:8000"

# Sample questions for days 1-24
sample_questions = [
    {
        "day_number": 1,
        "question_text": "What is the capital of Sweden?",
        "correct_answer": "Stockholm",
        "image_1": None,
        "image_2": None,
        "image_3": None,
        "image_4": None,
        "image_5": None
    },
    {
        "day_number": 2,
        "question_text": "In what year was the first Christmas card sent?",
        "correct_answer": "1843",
        "image_1": None,
        "image_2": None,
        "image_3": None,
        "image_4": None,
        "image_5": None
    },
    {
        "day_number": 3,
        "question_text": "What type of tree is traditionally used as a Christmas tree in Scandinavia?",
        "correct_answer": "Spruce",
        "image_1": None,
        "image_2": None,
        "image_3": None,
        "image_4": None,
        "image_5": None
    },
    {
        "day_number": 4,
        "question_text": "How many reindeer does Santa Claus have?",
        "correct_answer": "9",
        "image_1": None,
        "image_2": None,
        "image_3": None,
        "image_4": None,
        "image_5": None
    },
    {
        "day_number": 5,
        "question_text": "What is the Swedish word for Christmas?",
        "correct_answer": "Jul",
        "image_1": None,
        "image_2": None,
        "image_3": None,
        "image_4": None,
        "image_5": None
    },
]

# Add more questions for all 24 days
for i in range(6, 25):
    sample_questions.append({
        "day_number": i,
        "question_text": f"Sample question for day {i}. What is 2 + 2?",
        "correct_answer": "4",
        "image_1": None,
        "image_2": None,
        "image_3": None,
        "image_4": None,
        "image_5": None
    })

def add_questions():
    """Add all sample questions to the database"""
    print("Adding sample questions to the database...")
    
    for question in sample_questions:
        try:
            response = requests.post(
                f"{BASE_URL}/api/questions",
                json=question
            )
            
            if response.status_code == 200:
                print(f"✓ Added question for day {question['day_number']}")
            else:
                print(f"✗ Failed to add question for day {question['day_number']}: {response.text}")
        except Exception as e:
            print(f"✗ Error adding question for day {question['day_number']}: {e}")
    
    print("\nDone! All questions have been added.")

if __name__ == "__main__":
    add_questions()
