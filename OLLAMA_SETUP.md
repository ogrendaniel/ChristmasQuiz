# Ollama AI Answer Checking Setup

## Overview
The Christmas Quiz now includes AI-powered answer checking using Ollama! This allows the quiz to intelligently match player answers even with spelling mistakes, synonyms, or slight variations.

## How It Works

### Hybrid Checking System
1. **Exact Match First** - If the answer exactly matches (case-insensitive), it's marked correct immediately (fast and free)
2. **AI Evaluation** - If no exact match, Ollama evaluates whether the answer is semantically correct
3. **Confidence Threshold** - AI must be 80%+ confident to mark an answer as correct
4. **Fallback** - If Ollama is unavailable or errors occur, it falls back to exact matching

### AI Verification Tracking
- Every AI-checked answer stores:
  - `ai_verified` - Whether this answer was checked by AI
  - `ai_confidence` - Confidence percentage (0-100)
  - `ai_reasoning` - Explanation of why AI marked it correct/incorrect
- Host can see AI badges in quiz history showing which answers were AI-verified

## Setup Instructions

### 1. Install Ollama
1. Download Ollama from https://ollama.ai/
2. Install Ollama on your system
3. Open a terminal/command prompt

### 2. Download the AI Model
```bash
ollama pull llama3.2
```

This downloads the default model (llama3.2). You can use other models by changing the `OLLAMA_MODEL` environment variable.

### 3. Start Ollama
Ollama should start automatically after installation. If not:
- **Windows**: Ollama runs as a service automatically
- **Mac/Linux**: Run `ollama serve` in a terminal

### 4. Install Python Package
In the backend directory:
```bash
cd backend
pip install ollama
```

### 5. Configure (Optional)
Create a `.env` file in the backend directory to customize:

```env
# Enable/disable AI checking (default: true)
USE_OLLAMA=true

# AI model to use (default: llama3.2)
OLLAMA_MODEL=llama3.2

# Minimum confidence required to mark as correct (default: 80)
OLLAMA_CONFIDENCE_THRESHOLD=80
```

### 6. Start the Backend
```bash
cd backend
python main.py
```

## Testing

Try submitting answers with variations:
- **Correct Answer**: "Santa Claus"
- **Accepted Variations**:
  - "santa" ✓
  - "Sata Claus" ✓ (spelling mistake)
  - "Saint Nicholas" ✓ (synonym)
  - "Father Christmas" ✓ (alternative name)
  - "santa clause" ✓ (common misspelling)

- **Rejected**:
  - "Christmas Tree" ✗ (wrong answer)
  - "Rudolf" ✗ (wrong answer)

## UI Features

### Quiz History
- AI-verified answers show a purple badge: **🤖 AI 95%**
- Hover over the badge to see:
  - Confidence percentage
  - AI's reasoning for the decision

### Example Badge
```
🤖 AI 92%
↓ (hover)
AI Verified (92% confidence)
The answer "Sata Claus" is a close misspelling 
of the correct answer "Santa Claus"
```

## Configuration Options

### `USE_OLLAMA` (true/false)
- `true`: Use AI checking when exact match fails
- `false`: Only use exact matching (faster, but strict)

### `OLLAMA_MODEL` (string)
Available models:
- `llama3.2` (default) - Good balance of speed and accuracy
- `llama3.1` - More powerful, slower
- `mistral` - Alternative model
- See https://ollama.ai/library for more models

### `OLLAMA_CONFIDENCE_THRESHOLD` (0-100)
Minimum confidence required to mark as correct:
- `80` (default) - Balanced
- `90` - Stricter (fewer false positives)
- `70` - More lenient (more variations accepted)

## Troubleshooting

### "Connection refused" Error
- Ollama is not running
- Solution: Start Ollama service

### "Model not found" Error
- Model not downloaded
- Solution: Run `ollama pull llama3.2`

### Slow Response Times
- AI checking takes 1-3 seconds per answer
- Solution: Consider using faster model or only AI-check incorrect answers

### All Answers Marked Wrong
- Confidence threshold too high
- Solution: Lower `OLLAMA_CONFIDENCE_THRESHOLD` to 70-75

## Performance Notes

- **Exact Match**: < 1ms
- **AI Check**: 1-3 seconds (depending on model and hardware)
- **Recommendation**: Exact match happens first, so correct answers are still instant
- **Cost**: Ollama runs locally - completely free!

## Database Schema

The `player_answers` table now includes:
```sql
ai_verified BOOLEAN DEFAULT 0      -- Whether AI was used
ai_confidence INTEGER              -- Confidence % (0-100)
ai_reasoning TEXT                  -- AI's explanation
```

Old quiz data will have these fields as NULL/0, meaning they were exact-matched.
