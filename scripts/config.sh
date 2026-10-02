#!/usr/bin/env bash
#
# config.sh — shared settings for the llm-research pipeline.
# Sourced by the other scripts; not meant to be executed directly.
#
# Anything written as ${VAR:-default} can be overridden from the environment,
# e.g.  LLAMA_CPP_DIR=/some/other/llama.cpp scripts/run_one.sh q4_k_m 1
#

# --- Project layout ---------------------------------------------------------
# PROJECT_ROOT = parent of the directory this file lives in (scripts/).
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

MODEL_FAMILY="${MODEL_FAMILY:-qwen3-14b}"

MODELS_DIR="${PROJECT_ROOT}/models/${MODEL_FAMILY}"     # models/<family>/<quant>/*.gguf
PROMPTS_DIR="${PROJECT_ROOT}/prompts"                   # prompt_A.txt, prompt_B.txt, prompt_C.txt
SEED_CSV="${PROJECT_ROOT}/seeds/seed_list.csv"
RUNS_DIR="${PROJECT_ROOT}/runs/${MODEL_FAMILY}"          # runs/<family>/<quant>/<run>/
CACHE_DIR="${PROJECT_ROOT}/.cache"                      # e.g. model sha256 cache

# --- llama.cpp (one build shared by every quant) ----------------------------
LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-${PROJECT_ROOT}/third_party/llama.cpp}"
LLAMA_CLI_BIN="${LLAMA_CLI_BIN:-${LLAMA_CPP_DIR}/build/bin/llama-cli}"

# --- CUDA toolkit (installed manually, not via package manager) -------------
CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.9}"
CUDA_BIN="${CUDA_HOME}/bin"
CUDA_LIB="${CUDA_HOME}/lib64"

# --- Generation parameters (identical for every run) ------------------------
LLAMA_N=512
LLAMA_CONTEXT_SIZE=2048
LLAMA_NGL=28
LLAMA_TEMPERATURE=0.8
LLAMA_TOP_P=0.95
LLAMA_TOP_K=40
LLAMA_REPEAT_PENALTY=1.1

LLAMA_SINGLE_TURN=true
LLAMA_NO_DISPLAY_PROMPT=true
LLAMA_SIMPLE_IO=true
LLAMA_PERF=true
LLAMA_SHOW_TIMINGS=true
LLAMA_VERBOSE=1
