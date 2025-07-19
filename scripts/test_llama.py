#!/usr/bin/env python3
"""
Simple test script to verify Llama-3.2-3B is working correctly
"""

import requests
import json
import time

def test_vllm_server():
    """Test if vLLM server is responding"""
    base_url = "http://localhost:4000"
    
    print("🧪 Testing Llama-3.2-3B vLLM Server...")
    
    # Test 1: Health check
    print("\n1. Testing server health...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is healthy")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False
    
    # Test 2: List models
    print("\n2. Testing model availability...")
    try:
        response = requests.get(f"{base_url}/v1/models", timeout=5)
        if response.status_code == 200:
            models = response.json()
            print("✅ Available models:")
            for model in models.get('data', []):
                print(f"   - {model.get('id', 'Unknown')}")
        else:
            print(f"❌ Models list failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Models list error: {e}")
    
    # Test 3: Simple completion
    print("\n3. Testing simple completion...")
    try:
        payload = {
            "model": "/home/user/smart-calendar/Models/meta-llama/Llama-3.2-3B",
            "prompt": "What is 2+2?",
            "max_tokens": 50,
            "temperature": 0.1
        }
        
        response = requests.post(
            f"{base_url}/v1/completions",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            text = result['choices'][0]['text'].strip()
            print(f"✅ Completion successful: '{text}'")
        else:
            print(f"❌ Completion failed: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Completion error: {e}")
    
    # Test 4: Chat completion (expected to fail due to template issues)
    print("\n4. Testing chat completion (expected to fail)...")
    try:
        payload = {
            "model": "/home/user/smart-calendar/Models/meta-llama/Llama-3.2-3B",
            "messages": [
                {"role": "user", "content": "Hello, how are you?"}
            ],
            "max_tokens": 50,
            "temperature": 0.1
        }
        
        response = requests.post(
            f"{base_url}/v1/chat/completions",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            text = result['choices'][0]['message']['content'].strip()
            print(f"✅ Chat completion successful: '{text}'")
        else:
            print(f"⚠️  Chat completion failed: {response.status_code} (This is expected)")
            print("✅ Smart Calendar will use completions endpoint instead")
    except Exception as e:
        print(f"⚠️  Chat completion error: {e} (This is expected)")
        print("✅ Smart Calendar will use completions endpoint instead")
    
    # Test 5: Email parsing test
    print("\n5. Testing email parsing scenario...")
    email_text = "Let's meet tomorrow for 30 minutes to discuss the project with John and Mary."
    prompt = f"""Extract meeting info from email. Return JSON only.

Required format:
{{"participants": ["email1", "email2"], "duration_minutes": 30, "time_constraints": "constraint", "topic": "topic"}}

Rules:
- If names only, add @amd.com
- Default duration: 30 minutes
- Extract time constraints like "tomorrow"

Email: {email_text}

JSON:"""

    try:
        payload = {
            "model": "/home/user/smart-calendar/Models/meta-llama/Llama-3.2-3B",
            "prompt": prompt,
            "max_tokens": 150,
            "temperature": 0.1,
            "stop": ["</s>", "\n\n"]
        }
        
        response = requests.post(
            f"{base_url}/v1/completions",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            text = result['choices'][0]['text'].strip()
            print(f"✅ Email parsing test successful:")
            print(f"Response: {text}")
        else:
            print(f"❌ Email parsing test failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Email parsing test error: {e}")
    
    print("\n🎯 Test Summary:")
    print("If completions work but chat fails, the Smart Calendar will use the completions fallback.")
    print("This is normal for some Llama models with chat template issues.")
    
    return True

if __name__ == "__main__":
    test_vllm_server()