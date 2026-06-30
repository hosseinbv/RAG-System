#!/usr/bin/env bash
# Launch the model servers (OpenAI-compatible) used by the RAG system.
# Using the GPU with small memory fractions.
# Usage: bash serve_models.sh [embed|rerank|gen|judge|all|eval|status]
#
# Serving uses the base env's vLLM (working torch 2.11). A per-process PYTHONPATH stub
# shadows a broken torchaudio in that env without modifying any shared package. The
# orchestration code runs in the separate `lang` env and only talks HTTP to these ports.
set -euo pipefail
source /home/ubuntu/miniconda3/etc/profile.d/conda.sh
conda activate base
export PYTHONPATH=/home/ubuntu/research/langgraph/_stubs:${PYTHONPATH:-}
LOG=/home/ubuntu/research/langgraph/logs
mkdir -p "$LOG"
GPU=${GPU:-4}
HOST=${HOST:-127.0.0.1}

wait_ready() {
  local port=$1
  local model=$2
  local log=$3
  echo "waiting for $model on :$port ..."
  for _ in $(seq 1 180); do
    if curl -fsS --max-time 2 "http://$HOST:$port/v1/models" 2>/dev/null | grep -q "$model"; then
      echo "$model ready on :$port"
      return 0
    fi
    if grep -qE "EngineCore failed|Engine core initialization failed|ValueError: No available memory|Traceback" "$log" 2>/dev/null; then
      echo "$model failed to start; last log lines:"
      tail -40 "$log"
      return 1
    fi
    sleep 2
  done
  echo "$model did not become ready in time; last log lines:"
  tail -40 "$log"
  return 1
}

status() {
  for port in 8001 8002 8003 8004; do
    printf "port %s: " "$port"
    curl -fsS --max-time 2 "http://$HOST:$port/v1/models" 2>/dev/null || echo "DOWN"
    echo
  done
}

serve_embed() {
  CUDA_VISIBLE_DEVICES=$GPU nohup python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen3-Embedding-0.6B --served-model-name Qwen3-Embedding-0.6B \
    --runner pooling --port 8002 --gpu-memory-utilization 0.10 --max-model-len 2048 \
    > "$LOG/vllm_embed.log" 2>&1 &
  echo "embed -> :8002 (pid $!)"
}
serve_rerank() {
  CUDA_VISIBLE_DEVICES=$GPU nohup python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen3-Reranker-0.6B --served-model-name Qwen3-Reranker-0.6B \
    --runner pooling --port 8003 --gpu-memory-utilization 0.10 --max-model-len 2048 \
    --hf-overrides '{"architectures":["Qwen3ForSequenceClassification"],"classifier_from_token":["no","yes"],"is_original_qwen3_reranker":true}' \
    > "$LOG/vllm_rerank.log" 2>&1 &
  echo "rerank -> :8003 (pid $!)"
}
serve_gen() {
  CUDA_VISIBLE_DEVICES=$GPU nohup python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen3-4B-Instruct-2507 --served-model-name Qwen3-4B-Instruct-2507 \
    --port 8001 --gpu-memory-utilization 0.22 --max-model-len 16384 \
    --generation-config vllm \
    > "$LOG/vllm_gen.log" 2>&1 &
  echo "generator -> :8001 (pid $!)"
}
serve_judge() {
  CUDA_VISIBLE_DEVICES=$GPU nohup python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen3-8B --served-model-name Qwen3-8B \
    --port 8004 --gpu-memory-utilization 0.30 --max-model-len 16384 \
    --generation-config vllm \
    > "$LOG/vllm_judge.log" 2>&1 &
  echo "judge -> :8004 (pid $!)"
}

case "${1:-all}" in
  embed) serve_embed ;;
  rerank) serve_rerank ;;
  gen) serve_gen ;;
  judge) serve_judge ;;
  all)
    serve_gen
    wait_ready 8001 Qwen3-4B-Instruct-2507 "$LOG/vllm_gen.log"
    serve_embed
    wait_ready 8002 Qwen3-Embedding-0.6B "$LOG/vllm_embed.log"
    serve_rerank
    wait_ready 8003 Qwen3-Reranker-0.6B "$LOG/vllm_rerank.log"
    ;;
  eval)
    serve_judge
    wait_ready 8004 Qwen3-8B "$LOG/vllm_judge.log"
    serve_gen
    wait_ready 8001 Qwen3-4B-Instruct-2507 "$LOG/vllm_gen.log"
    serve_embed
    wait_ready 8002 Qwen3-Embedding-0.6B "$LOG/vllm_embed.log"
    serve_rerank
    wait_ready 8003 Qwen3-Reranker-0.6B "$LOG/vllm_rerank.log"
    ;;
  status) status ;;
  *)
    echo "Usage: bash serve_models.sh [embed|rerank|gen|judge|all|eval|status]" >&2
    exit 2
    ;;
esac
echo "logs in $LOG ; status: bash serve_models.sh status"
