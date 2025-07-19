#!/bin/bash

# Optimized vLLM startup script for Llama-3.2-3B
# This script starts the vLLM server with optimal settings for the Llama-3.2-3B model

set -e

# Configuration
MODEL_PATH="/home/user/smart-calendar/Models/meta-llama/Llama-3.2-3B"
HOST="0.0.0.0"
PORT="4000"
GPU_DEVICE="0"

# Optimized parameters for Llama-3.2-3B (3B parameter model)
GPU_MEMORY_UTILIZATION="0.7"   # Conservative for 3B model
SWAP_SPACE="8"                 # Reduced swap for smaller model
MAX_MODEL_LEN="2048"           # Good balance for scheduling tasks
TENSOR_PARALLEL_SIZE="1"       # Single GPU sufficient for 3B model
MAX_NUM_SEQS="64"              # Optimized batch size
MAX_NUM_BATCHED_TOKENS="1024"  # Smaller batch for faster inference

echo "Starting Llama-3.2-3B vLLM server..."
echo "Model path: $MODEL_PATH"
echo "Host: $HOST:$PORT"
echo "GPU device: $GPU_DEVICE"

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

# Start vLLM server with optimized settings for Llama-3.2-3B
HIP_VISIBLE_DEVICES=$GPU_DEVICE vllm serve "$MODEL_PATH" \
    --host "$HOST" \
    --port "$PORT" \
    --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION" \
    --swap-space "$SWAP_SPACE" \
    --disable-log-requests \
    --dtype float16 \
    --max-model-len "$MAX_MODEL_LEN" \
    --tensor-parallel-size "$TENSOR_PARALLEL_SIZE" \
    --max-num-seqs "$MAX_NUM_SEQS" \
    --max-num-batched-tokens "$MAX_NUM_BATCHED_TOKENS" \
    --distributed-executor-backend "mp" \
    --trust-remote-code \
    --enforce-eager \
    --disable-log-stats \
    --served-model-name "llama-3.2-3b"