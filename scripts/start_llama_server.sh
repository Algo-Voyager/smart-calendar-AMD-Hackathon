#!/bin/bash

# Optimized vLLM startup script for Llama-3.2-3B
# This script starts the vLLM server with optimal settings for the Llama-3.2-3B model

set -e

# Configuration
MODEL_PATH="/home/user/smart-calendar/Models/meta-llama/Llama-3.2-3B"

echo "Starting Llama-3.2-3B vLLM server..."
echo "Model path: $MODEL_PATH"
echo "Host: 0.0.0.0:4000"
echo "GPU device: 0"

# Check if model directory exists
if [ ! -d "$MODEL_PATH" ]; then
    echo "Error: Model directory not found at $MODEL_PATH"
    echo "Please ensure the Llama-3.2-3B model is downloaded and available"
    exit 1
fi

# Check if GPU is available
if ! command -v nvidia-smi &> /dev/null; then
    echo "Warning: nvidia-smi not found. Continuing anyway..."
else
    echo "GPU Status:"
    nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv,noheader,nounits
fi

# Start vLLM server with specified flags for Llama-3.2-3B
HIP_VISIBLE_DEVICES=0 vllm serve "$MODEL_PATH" \
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