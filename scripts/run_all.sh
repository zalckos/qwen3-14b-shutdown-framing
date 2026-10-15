#!/usr/bin/env bash

set -e

cd /home/avocado/llm-research

# Generate seed list
/home/avocado/llm-research/scripts/generate_seed_list.py --master-seed 345653453 --order-seed 566345634 -o seeds/seed_list.csv

# Run 300 experiments for each quantization
for i in {1..300}; do
    /home/avocado/llm-research/scripts/run_one.sh q4_k_m "$i"
done

for i in {1..300}; do
    /home/avocado/llm-research/scripts/run_one.sh q5_0 "$i"
done

for i in {1..300}; do
    /home/avocado/llm-research/scripts/run_one.sh q5_k_m "$i"
done

for i in {1..300}; do
    /home/avocado/llm-research/scripts/run_one.sh q6_k "$i"
done

for i in {1..300}; do
    /home/avocado/llm-research/scripts/run_one.sh q8_0 "$i"
done

# Analyze all runs
/home/avocado/llm-research/scripts/analyze_runs.py

# Start llama-server in a detached screen session
screen -dmS llama-server \
    /home/avocado/llm-research/third_party/llama.cpp/build/bin/llama-server \
    -m /home/avocado/llm-research/models/qwen3-14b/q8_0/Qwen3-14B-Q8_0.gguf \
    -ngl 28 \
    -c 4096 \
    --temp 0 \
    --port 8080

# Wait for llama-server to accept connections
echo "Waiting for llama-server on port 8080..."

TIMEOUT=300
ELAPSED=0

while ! nc -z 127.0.0.1 8080; do
    if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
        echo "ERROR: llama-server did not start within ${TIMEOUT} seconds."
        echo "Check the server with: screen -r llama-server"
        exit 1
    fi

    sleep 2
    ELAPSED=$((ELAPSED + 2))
done

echo "llama-server is accepting connections on port 8080."

# Classify bullets
python3 /home/avocado/llm-research/scripts/classify_bullets.py \
    --bullets /home/avocado/llm-research/results/qwen3-14b/q4_k_m/raw/bullets.jsonl \
    --model-path /home/avocado/llm-research/models/qwen3-14b/q8_0/Qwen3-14B-Q8_0.gguf \
    --backend server \
    --no-think \
    --seed 6456376

python3 /home/avocado/llm-research/scripts/classify_bullets.py \
    --bullets /home/avocado/llm-research/results/qwen3-14b/q5_0/raw/bullets.jsonl \
    --model-path /home/avocado/llm-research/models/qwen3-14b/q8_0/Qwen3-14B-Q8_0.gguf \
    --backend server \
    --no-think \
    --seed 6456376

python3 /home/avocado/llm-research/scripts/classify_bullets.py \
    --bullets /home/avocado/llm-research/results/qwen3-14b/q5_k_m/raw/bullets.jsonl \
    --model-path /home/avocado/llm-research/models/qwen3-14b/q8_0/Qwen3-14B-Q8_0.gguf \
    --backend server \
    --no-think \
    --seed 6456376

python3 /home/avocado/llm-research/scripts/classify_bullets.py \
    --bullets /home/avocado/llm-research/results/qwen3-14b/q6_k/raw/bullets.jsonl \
    --model-path /home/avocado/llm-research/models/qwen3-14b/q8_0/Qwen3-14B-Q8_0.gguf \
    --backend server \
    --no-think \
    --seed 6456376

python3 /home/avocado/llm-research/scripts/classify_bullets.py \
    --bullets /home/avocado/llm-research/results/qwen3-14b/q8_0/raw/bullets.jsonl \
    --model-path /home/avocado/llm-research/models/qwen3-14b/q8_0/Qwen3-14B-Q8_0.gguf \
    --backend server \
    --no-think \
    --seed 6456376

