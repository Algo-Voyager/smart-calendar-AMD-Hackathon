# Smart Calendar Assistant (Llama-3.2-3B Optimized)

An intelligent AI-powered scheduling system that autonomously coordinates meetings using the Llama-3.2-3B model and Google Calendar integration.

## Features

- **Llama-3.2-3B Integration**: Optimized for the compact 3B parameter model for fast inference
- **Enhanced Email Parsing**: Multi-strategy JSON extraction from Llama responses
- **Google Calendar Integration**: Real-time calendar access with parallel processing
- **Intelligent Scheduling**: AI-powered conflict resolution and optimal time finding
- **Ultra-Fast Processing**: Optimized for <5 second response time with smaller model
- **Robust Fallbacks**: Multiple layers of fallback mechanisms for reliability

## Architecture

```
smart-calendar/
├── config/           # Configuration and settings
├── src/
│   ├── calendar/     # Google Calendar integration
│   ├── ai_agent/     # LLM client and AI logic
│   ├── scheduler/    # Main scheduling coordinator
│   └── api/          # Flask REST API server
├── utils/            # Logging and validation utilities
├── tests/            # Test client and validation
└── main.py           # Main entry point
```

## Quick Start

### Option 1: Automated Setup (Recommended)
```bash
# Install dependencies
pip install -r requirements.txt

# Start everything with automated script
python scripts/start_smart_calendar.py
```

### Option 2: Manual Setup

#### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 2. Start Llama-3.2-3B vLLM Server
```bash
# Option A: Using startup script
./scripts/start_llama_server.sh

# Option B: Manual startup (exact flags specified)
HIP_VISIBLE_DEVICES=0 vllm serve /home/user/smart-calendar/Models/meta-llama/Llama-3.2-3B \
    --gpu-memory-utilization 0.3 \
    --swap-space 16 \
    --disable-log-requests \
    --dtype float16 \
    --max-model-len 2048 \
    --tensor-parallel-size 1 \
    --host 0.0.0.0 \
    --port 4000 \
    --num-scheduler-steps 10 \
    --max-num-seqs 128 \
    --max-num-batched-tokens 2048 \
    --distributed-executor-backend "mp"
```

#### 2a. Test the Model (Optional)
```bash
# Test if Llama server is working correctly
python scripts/test_llama.py
```

#### 3. Run the API Server
```bash
python main.py server --host 0.0.0.0 --port 5000
```

#### 4. Test the System
```bash
python main.py test --url http://localhost:5000
```

#### 5. Analyze User Calendar (Debug/Development)
```bash
# Analyze userone.amd@gmail.com calendar for next 7 days
python main.py analyze --email userone.amd@gmail.com

# Analyze for specific number of days with JSON output
python main.py analyze --email usertwo.amd@gmail.com --days 3 --json
```

## Usage

### API Endpoint
```
POST /receive
Content-Type: application/json
```

### Example Request
```json
{
    "Request_id": "6118b54f-907b-4451-8d48-dd13d76033a5",
    "Datetime": "19-07-2025T12:34:55",
    "Location": "IISc Bangalore",
    "From": "userone.amd@gmail.com",
    "Attendees": [
        {"email": "usertwo.amd@gmail.com"},
        {"email": "userthree.amd@gmail.com"}
    ],
    "Subject": "AI Project Status Update",
    "EmailContent": "Hi team, let's meet on Thursday for 30 minutes to discuss the AI project."
}
```

### Process Single Request
```bash
python main.py process input.json --output output.json
```

### Library Usage
```python
from main import your_meeting_assistant

# For hackathon submission
result = your_meeting_assistant(request_data)
```

### Calendar Analysis Commands
```bash
# Quick analysis using dedicated script
python scripts/analyze_userone_calendar.py

# Advanced analysis using main CLI
python main.py analyze --email userone.amd@gmail.com --days 7

# Available analysis options:
python utils/calendar_slot_analyzer.py --email usertwo.amd@gmail.com --days 5
python utils/calendar_slot_analyzer.py --email userthree.amd@gmail.com --json
```

## Key Optimizations for Llama-3.2-3B

1. **Model-Specific Tuning**: Optimized parameters for 3B model (low temp, reduced tokens)
2. **Enhanced JSON Extraction**: Multiple strategies for parsing Llama-3.2 responses
3. **Parallel Calendar Fetching**: Multiple users' calendars fetched concurrently
4. **Intelligent Caching**: LLM response caching with memory management
5. **Smart Fallbacks**: Multi-tier fallback system (AI → Enhanced Regex → Emergency)
6. **Compact Prompts**: Optimized prompts for smaller model efficiency
7. **Fast Inference**: Conservative GPU memory usage for faster response times

## Configuration

Key settings optimized for Llama-3.2-3B in `config/settings.py`:
- **Model Path**: `/home/user/smart-calendar/Models/meta-llama/Llama-3.2-3B`
- **Server URL**: `http://localhost:4000/v1` 
- **Max Tokens**: 512 (optimized for scheduling tasks)
- **Temperature**: 0.1 (low for consistent results)
- **Timeout**: 15s (faster than larger models)
- **Enhanced prompts**: Compact format for 3B model efficiency

## Testing

The system includes comprehensive testing:
- Health checks
- Response format validation
- Performance benchmarking
- Error handling validation

## Requirements

- Python 3.8+
- vLLM with Llama-3.2-3B model support
- Llama-3.2-3B model downloaded at `/home/user/smart-calendar/Models/meta-llama/Llama-3.2-3B`
- Google Calendar API credentials (optional for basic testing)
- GPU with sufficient VRAM (recommended: 8GB+ for optimal performance)

## Llama-3.2-3B Advantages

- **Faster Inference**: 3B parameters allow for sub-second response times
- **Lower Memory Usage**: Requires less GPU memory than larger models
- **High Quality**: Still maintains excellent performance for scheduling tasks
- **Cost Effective**: Reduced computational requirements
- **Local Deployment**: Perfect for on-premise deployment scenarios

## Troubleshooting

### **Chat Template Errors**
If you see chat template errors in vLLM logs:
1. **This is expected**: Smart Calendar automatically uses completions endpoint
2. **No action needed**: System will auto-fallback seamlessly
3. **Normal behavior**: Some Llama models have chat template compatibility issues

### **Common Issues**
```bash
# Issue: "Model not found"
# Solution: Check model path
ls /home/user/smart-calendar/Models/meta-llama/Llama-3.2-3B

# Issue: "Port already in use"
# Solution: Kill existing process
pkill -f "vllm serve" && sleep 5

# Issue: "GPU memory error"
# Solution: Reduce memory utilization
# Edit start_llama_server.sh: change --gpu-memory-utilization to 0.2
```

### **Testing Steps**
1. **Test model**: `python scripts/test_llama.py`
2. **Test Smart Calendar**: `python scripts/test_smart_calendar_simple.py`  
3. **Test API**: `python main.py test`
4. **Check logs**: Look for "✅" success indicators

### **Important Note About Chat Template Issues**
The Llama-3.2-3B model may not have a compatible chat template, causing chat completions to fail with a 400 error. **This is completely normal and expected.** 

✅ **The Smart Calendar system automatically uses the completions endpoint instead**, which works perfectly for all scheduling tasks.

You'll see this pattern in the logs:
- ⚠️ Chat completion fails (400 error) 
- ✅ Completions endpoint works perfectly
- ✅ Smart Calendar functions normally

## License

This project is developed for the AMD AI Hackathon with Llama-3.2-3B optimization.