#!/usr/bin/env bash
#
# run_one.sh — run one seeded llama.cpp generation for a given quantization.
#
# Usage:
#   scripts/run_one.sh <quant> <run_nr>
#   e.g.  scripts/run_one.sh q4_k_m 1
#
#   <quant>   directory name under models/<family>/  (q4_k_m, q5_k_m, q6_k, ...)
#   <run_nr>  execution_order value from seeds/seed_list.csv  (1..N)
#
# Output: runs/<quant>/<NNNN>_triplet<ID>_<COND>/
#
# Output streams (llama-cli's two streams are captured SEPARATELY and directly
# to files by the shell -- no tee chain, no concurrent writers, no interleaving):
#   output.txt : llama-cli stdout, byte-exact (generated text, but it also 
#                contains the banner, prompt echo and performance line.)
#   run.log    : llama-cli stderr, byte-exact  (llama.cpp logging / perf / verbose)
#   raw.txt    : both streams concatenated after the run, with BEGIN/END
#                delimiters (a deterministic combined archive, not interleaved)
#   prompt.txt : the exact prompt text fed to llama-cli
#   gpu.csv, system.csv : 1 Hz resource monitors running during generation
#   manifest.json       : parameters, provenance, timings, diagnostics
# Manifest diagnostics (finish_reason, stop_type, truncated, timings, token
# counts) are parsed from run.log, never from the generated text.
#
# Shared paths and generation parameters live in scripts/config.sh.
#
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=config.sh
source "${SCRIPT_DIR}/config.sh"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

die() {
    echo "ERROR: $*" >&2
    exit 1
}

# llama.cpp writes its logging / perf / verbose-JSON lines to stderr (captured
# in run.log) and the generated text to stdout (captured in output.txt), so
# diagnostic values are parsed from run.log. If some build emits a particular
# line on stdout instead, fall back to the stdout capture rather than silently
# recording "unknown" / empty values. Usage: diag_grep <grep args...>
# (RUN_LOG and OUTPUT_TXT are defined before this is first called.)
diag_grep() {
    local out
    out="$(grep "$@" "$RUN_LOG" 2>/dev/null)"
    if [ -z "$out" ]; then
        out="$(grep "$@" "$OUTPUT_TXT" 2>/dev/null)"
    fi
    printf '%s\n' "$out"
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

if [ $# -ne 2 ]; then
    die "usage: $0 <quant> <run_nr>   (e.g. $0 q4_k_m 1)"
fi

QUANT="$1"
EXEC_ORDER="$2"

case "$QUANT" in
    ''|*[!a-z0-9_]*) die "quant must be lowercase letters/digits/underscores (e.g. q4_k_m), got: '${QUANT}'" ;;
esac

case "$EXEC_ORDER" in
    ''|*[!0-9]*) die "run_nr must be a positive integer, got: '${EXEC_ORDER}'" ;;
esac
EXEC_ORDER=$((10#$EXEC_ORDER))    # accept 007 as 7

# ---------------------------------------------------------------------------
# Resolve the model for this quant
# ---------------------------------------------------------------------------

MODEL_DIR="${MODELS_DIR}/${QUANT}"
[ -d "$MODEL_DIR" ] || die "no model directory for quant '${QUANT}': $MODEL_DIR"

shopt -s nullglob
MODEL_CANDIDATES=("${MODEL_DIR}"/*.gguf)
shopt -u nullglob

case "${#MODEL_CANDIDATES[@]}" in
    0) die "no .gguf file found in $MODEL_DIR" ;;
    1) MODEL_PATH="${MODEL_CANDIDATES[0]}" ;;
    *) die "expected exactly one .gguf in $MODEL_DIR, found ${#MODEL_CANDIDATES[@]}" ;;
esac

# ---------------------------------------------------------------------------
# Sanity checks
# ---------------------------------------------------------------------------

[ -f "$SEED_CSV" ]        || die "seed list not found: $SEED_CSV"
[ -x "$LLAMA_CLI_BIN" ]   || die "llama-cli binary not found/executable: $LLAMA_CLI_BIN (set LLAMA_CPP_DIR or LLAMA_CLI_BIN)"
[ -x "${CUDA_BIN}/nvcc" ] || die "missing nvcc at ${CUDA_BIN}/nvcc"

# ---------------------------------------------------------------------------
# Environment (CUDA toolkit + llama.cpp shared libs)
# ---------------------------------------------------------------------------

export PATH="${CUDA_BIN}:${PATH}"

LLAMA_BIN_DIR="$(dirname "${LLAMA_CLI_BIN}")"
export LD_LIBRARY_PATH="${CUDA_LIB}:${LLAMA_BIN_DIR}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"

# ---------------------------------------------------------------------------
# Look up the row for this run number
# ---------------------------------------------------------------------------

# Columns: execution_order,triplet_id,condition,seed  (matched by position, so
# the header name -- pair_id or triplet_id -- doesn't matter).
# strip possible CR (CRLF file) and find the matching data row
ROW="$(tr -d '\r' < "$SEED_CSV" | awk -F',' -v eo="$EXEC_ORDER" 'NR>1 && ($1+0)==(eo+0) {print; exit}')"

[ -n "$ROW" ] || die "run_nr '${EXEC_ORDER}' not found in $SEED_CSV"

IFS=',' read -r ROW_EXEC_ORDER TRIPLET_ID CONDITION SEED <<< "$ROW"

case "$CONDITION" in
    A|B|C) : ;;
    *) die "unrecognized condition '${CONDITION}' for run_nr ${EXEC_ORDER} (expected A, B or C)" ;;
esac

PROMPT_FILE="${PROMPTS_DIR}/prompt_${CONDITION}.txt"
[ -f "$PROMPT_FILE" ] || die "prompt file not found: $PROMPT_FILE"

# ---------------------------------------------------------------------------
# Project git state (recorded in the manifest). Only *tracked* files count
# toward "dirty", so new run output never flips the flag.
# ---------------------------------------------------------------------------

if git -C "$PROJECT_ROOT" rev-parse HEAD >/dev/null 2>&1; then
    SCRIPT_GIT_COMMIT="$(git -C "$PROJECT_ROOT" rev-parse HEAD)"
    if [ -n "$(git -C "$PROJECT_ROOT" status --porcelain --untracked-files=no 2>/dev/null)" ]; then
        SCRIPT_GIT_DIRTY=true
    else
        SCRIPT_GIT_DIRTY=false
    fi
else
    SCRIPT_GIT_COMMIT="unknown"
    SCRIPT_GIT_DIRTY="unknown"
fi

# ---------------------------------------------------------------------------
# Set up the run directory
# ---------------------------------------------------------------------------

RUN_LABEL="$(printf '%04d' "$EXEC_ORDER")_triplet${TRIPLET_ID}_${CONDITION}"
RUNDIR="${RUNS_DIR}/${QUANT}/${RUN_LABEL}"

if [ -e "$RUNDIR" ]; then
    die "run directory already exists (refusing to overwrite): $RUNDIR"
fi
mkdir -p "$RUNDIR"

# Create the exact prompt text that will be fed to llama-cli.
# Remove only trailing newline characters introduced by the text editor;
# preserve all other prompt content exactly.
PROMPT_TMP="${RUNDIR}/prompt.txt"

python3 - "$PROMPT_FILE" "$PROMPT_TMP" <<'PY'
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

text = text.rstrip("\r\n")

with open(dst, "w", encoding="utf-8") as f:
    f.write(text)
PY

echo "== run_one.sh =="
echo "quant           : $QUANT"
echo "run_nr          : $EXEC_ORDER"
echo "triplet_id      : $TRIPLET_ID"
echo "condition       : $CONDITION"
echo "seed            : $SEED"
echo "model           : $MODEL_PATH"
echo "prompt_file     : $PROMPT_FILE"
echo "output dir      : $RUNDIR"
echo

# ---------------------------------------------------------------------------
# Background monitors: gpu.csv and system.csv
# ---------------------------------------------------------------------------

GPU_CSV="${RUNDIR}/gpu.csv"
SYS_CSV="${RUNDIR}/system.csv"

GPU_PID=""
if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi \
        --query-gpu=timestamp,utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu,power.draw \
        --format=csv -l 1 > "$GPU_CSV" 2>/dev/null &
    GPU_PID=$!
else
    echo "timestamp,utilization.gpu [%],utilization.memory [%],memory.used [MiB],memory.total [MiB],temperature.gpu,power.draw [W]" > "$GPU_CSV"
    echo "# nvidia-smi not found on this system" >> "$GPU_CSV"
fi

(
    echo "timestamp_utc,load1,load5,load15,mem_used_mb,mem_total_mb"
    while true; do
        ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        read -r l1 l5 l15 _ < /proc/loadavg
        mem="$(free -m | awk '/^Mem:/{print $3","$2}')"
        echo "${ts},${l1},${l5},${l15},${mem}"
        sleep 1
    done
) > "$SYS_CSV" &
SYS_PID=$!

cleanup_monitors() {
    [ -n "$GPU_PID" ] && kill "$GPU_PID" >/dev/null 2>&1
    kill "$SYS_PID" >/dev/null 2>&1
    [ -n "$GPU_PID" ] && wait "$GPU_PID" 2>/dev/null
    wait "$SYS_PID" 2>/dev/null
    return 0
}
trap cleanup_monitors EXIT

# ---------------------------------------------------------------------------
# Run llama-cli
# ---------------------------------------------------------------------------

RAW_TXT="${RUNDIR}/raw.txt"
OUTPUT_TXT="${RUNDIR}/output.txt"
RUN_LOG="${RUNDIR}/run.log"

# Generation parameters come from config.sh.
ARGS=(
    -m "$MODEL_PATH"
    -f "$PROMPT_TMP"
    -n "$LLAMA_N"
    -c "$LLAMA_CONTEXT_SIZE"
    -ngl "$LLAMA_NGL"
    --seed "$SEED"
    --temp "$LLAMA_TEMPERATURE"
    --top-p "$LLAMA_TOP_P"
    --top-k "$LLAMA_TOP_K"
    --repeat-penalty "$LLAMA_REPEAT_PENALTY"
    --single-turn
    --no-display-prompt
    --simple-io
    --perf
    --show-timings
    --verbose
)

# Exact command line as executed (shell-quoted), for the manifest.
LLAMA_COMMAND="$(printf '%q ' "${LLAMA_CLI_BIN}" "${ARGS[@]}")"
LLAMA_COMMAND="${LLAMA_COMMAND% }"

START_TIME="$(date +%s.%N)"

# stdout (with --simple-io --no-display-prompt) is just the model's generated
# text; stderr carries llama.cpp's logging/perf/verbose output. Each stream is
# redirected straight to its own file by the shell: nothing is merged, nothing
# is written by two processes, and both files are complete the moment llama-cli
# exits (no background tee left to flush, unlike a process-substitution setup).
"${LLAMA_CLI_BIN}" "${ARGS[@]}" > "$OUTPUT_TXT" 2> "$RUN_LOG"
LLAMA_EXIT=$?

# ---------------------------------------------------------------------------
# Capture generation termination reason
# ---------------------------------------------------------------------------

FINISH_REASON="unknown"
STOP_TYPE="unknown"
GEN_TRUNCATED="unknown"

# The final streamed response chunk contains the authoritative finish_reason.
# Take the LAST occurrence because intermediate streaming chunks have
# finish_reason:null.
PARSED_FINISH_REASON="$(
    diag_grep -o '"finish_reason":"[^"]*"' |
    tail -n1 |
    cut -d'"' -f4
)"

if [ -n "$PARSED_FINISH_REASON" ] && [ "$PARSED_FINISH_REASON" != "null" ]; then
    FINISH_REASON="$PARSED_FINISH_REASON"
fi

# The final Parsed message contains stop_type and truncated.
PARSED_STOP_TYPE="$(
    diag_grep -o '"stop_type":"[^"]*"' |
    tail -n1 |
    cut -d'"' -f4
)"

if [ -n "$PARSED_STOP_TYPE" ]; then
    STOP_TYPE="$PARSED_STOP_TYPE"
fi

PARSED_TRUNCATED="$(
    diag_grep -o '"truncated":[^,}]*' |
    tail -n1 |
    cut -d':' -f2
)"

if [ -n "$PARSED_TRUNCATED" ]; then
    GEN_TRUNCATED="$PARSED_TRUNCATED"
fi

# Classify generation-level problems separately from substantive output
# failures. Hitting the generation limit is not a refusal/deflection.
if [ "$FINISH_REASON" = "length" ] || [ "$STOP_TYPE" = "limit" ]; then
    OUTPUT_MALFORMED_SUBTYPE="generation_length_limit"
elif [ "$LLAMA_EXIT" -ne 0 ]; then
    OUTPUT_MALFORMED_SUBTYPE="process_error"
else
    OUTPUT_MALFORMED_SUBTYPE=""
fi

END_TIME="$(date +%s.%N)"
WALL_ELAPSED="$(awk -v a="$START_TIME" -v b="$END_TIME" 'BEGIN{printf "%.3f", b-a}')"

cleanup_monitors
trap - EXIT

# raw.txt: deterministic combined archive of both streams. output.txt and
# run.log above are the authoritative byte-exact captures; here they are just
# concatenated with delimiters (written once, never appended concurrently).
#   (A newline is added before an END marker only if the stream did not already
#   end with one, so each block is an exact copy of its source file.)
{
    echo "===== BEGIN STDOUT (generated text; identical to output.txt) ====="
    cat "$OUTPUT_TXT"
    [ -n "$(tail -c1 "$OUTPUT_TXT")" ] && echo
    echo "===== END STDOUT ====="
    echo "===== BEGIN STDERR (llama.cpp diagnostics; identical to run.log) ====="
    cat "$RUN_LOG"
    [ -n "$(tail -c1 "$RUN_LOG")" ] && echo
    echo "===== END STDERR ====="
} > "$RAW_TXT"

# Replay llama.cpp's diagnostics on the terminal. Stdout stays off the
# terminal. For a live view while a run is in progress, use:
#   tail -f runs/<quant>/<run>/run.log
cat "$RUN_LOG" >&2

if [ "$LLAMA_EXIT" -ne 0 ]; then
    echo "WARNING: llama-cli exited with status $LLAMA_EXIT (see $RUN_LOG)" >&2
fi

# ---------------------------------------------------------------------------
# Parse timings out of run.log
# ---------------------------------------------------------------------------

extract_ms() {
    # $1 = line; prints the millisecond figure right after "="
    echo "$1" | sed -n 's/.*=\s*\([0-9.]\+\)\s*ms.*/\1/p'
}
extract_tokens() {
    # $1 = line; prints the token count between "/" and "tokens"
    echo "$1" | sed -n 's#.*/\s*\([0-9]\+\)\s*tokens.*#\1#p'
}

# A genuine llama.cpp perf line looks like "<label> = <number> ms / ...".
# With --verbose, the model's own words are also echoed into the stderr log
# (streamed JSON chunks, the final "Parsed message"), so a bare label match
# could hit e.g. "...minimize total time..." before the real perf line.
# Requiring the "= <number> ms" part means only real timing lines qualify.
PERF_NUM='=[[:space:]]*[0-9.]+[[:space:]]*ms'
PROMPT_LINE="$(diag_grep 'prompt eval time' | grep -E "$PERF_NUM" | head -n1)"
GEN_LINE="$(diag_grep 'eval time' | grep -v 'prompt eval time' | grep -E "$PERF_NUM" | head -n1)"
TOTAL_LINE="$(diag_grep 'total time' | grep -E "$PERF_NUM" | head -n1)"

PROMPT_TOKENS=""
PROMPT_TIME_S=""
if [ -n "$PROMPT_LINE" ]; then
    PROMPT_MS="$(extract_ms "$PROMPT_LINE")"
    PROMPT_TOKENS="$(extract_tokens "$PROMPT_LINE")"
    [ -n "$PROMPT_MS" ] && PROMPT_TIME_S="$(awk -v ms="$PROMPT_MS" 'BEGIN{printf "%.6f", ms/1000}')"
fi

OUTPUT_TOKENS=""
GEN_TIME_S=""
if [ -n "$GEN_LINE" ]; then
    GEN_MS="$(extract_ms "$GEN_LINE")"
    OUTPUT_TOKENS="$(extract_tokens "$GEN_LINE")"
    [ -n "$GEN_MS" ] && GEN_TIME_S="$(awk -v ms="$GEN_MS" 'BEGIN{printf "%.6f", ms/1000}')"
fi

TOTAL_ELAPSED_S="$WALL_ELAPSED"
if [ -n "$TOTAL_LINE" ]; then
    TOTAL_MS="$(extract_ms "$TOTAL_LINE")"
    [ -n "$TOTAL_MS" ] && TOTAL_ELAPSED_S="$(awk -v ms="$TOTAL_MS" 'BEGIN{printf "%.6f", ms/1000}')"
fi

# ---------------------------------------------------------------------------
# Environment / provenance info
# ---------------------------------------------------------------------------

LLAMA_CPP_GIT_COMMIT="$(
    git -C "$LLAMA_CPP_DIR" rev-parse HEAD 2>/dev/null || echo unknown
)"

LLAMA_VERSION="$(
    "${LLAMA_CLI_BIN}" --version 2>&1 |
    sed -n '1s/^version: //p'
)"

LLAMA_COMPILER="$(
    "${LLAMA_CLI_BIN}" --version 2>&1 |
    sed -n '2s/^built with //p'
)"

LLAMA_CLI_SHA256="$(
    sha256sum "$LLAMA_CLI_BIN" | awk '{print $1}'
)"

OS_VERSION=""
if [ -f /etc/os-release ]; then
    OS_VERSION="$(. /etc/os-release && echo "$PRETTY_NAME")"
else
    OS_VERSION="$(uname -a)"
fi

KERNEL_VERSION="$(uname -r)"
KERNEL_FULL="$(uname -a)"

GPU_DRIVER_VERSION=""
if command -v nvidia-smi >/dev/null 2>&1; then
    GPU_DRIVER_VERSION="$(nvidia-smi --query-gpu=driver_version --format=csv,noheader -i 0 2>/dev/null | head -n1)"
fi

CUDA_VERSION="$("${CUDA_BIN}/nvcc" --version 2>/dev/null | grep -oE 'release [0-9]+\.[0-9]+' | awk '{print $2}')"
[ -n "$CUDA_VERSION" ] || CUDA_VERSION="$(basename "$CUDA_HOME")"

# Model hash: expensive to compute (large file), so cache it -- one cache entry
# per family+quant, revalidated against the file's size and mtime so a replaced
# model file is re-hashed automatically.
mkdir -p "$CACHE_DIR"
MODEL_HASH_CACHE="${CACHE_DIR}/model_sha256_${MODEL_FAMILY}_${QUANT}.txt"
MODEL_ID="$(stat -c '%s:%Y' "$MODEL_PATH")"
MODEL_SHA256=""
if [ -f "$MODEL_HASH_CACHE" ]; then
    read -r CACHED_ID CACHED_SHA < "$MODEL_HASH_CACHE" || true
    if [ "${CACHED_ID:-}" = "$MODEL_ID" ]; then
        MODEL_SHA256="${CACHED_SHA:-}"
    fi
fi
if [ -z "$MODEL_SHA256" ]; then
    MODEL_SHA256="$(sha256sum "$MODEL_PATH" | awk '{print $1}')"
    echo "${MODEL_ID} ${MODEL_SHA256}" > "$MODEL_HASH_CACHE"
fi

PROMPT_SHA256="$(sha256sum "$PROMPT_FILE" | awk '{print $1}')"

# ---------------------------------------------------------------------------
# Write manifest.json (via python3 for safe JSON escaping of prompt text etc.)
# ---------------------------------------------------------------------------

export RUNDIR
export MANIFEST_run_number="$EXEC_ORDER"
export MANIFEST_quant="$QUANT"
export MANIFEST_triplet_id="$TRIPLET_ID"
export MANIFEST_condition="$CONDITION"
export MANIFEST_prompt_file="$PROMPT_FILE"
export MANIFEST_prompt_sha256="$PROMPT_SHA256"
export MANIFEST_prompt_file_path_for_text="$PROMPT_TMP"
export MANIFEST_model_file="$MODEL_PATH"
export MANIFEST_model_sha256="$MODEL_SHA256"
export MANIFEST_seed="$SEED"
export MANIFEST_prompt_tokens="$PROMPT_TOKENS"
export MANIFEST_output_tokens="$OUTPUT_TOKENS"
export MANIFEST_prompt_time_seconds="$PROMPT_TIME_S"
export MANIFEST_generation_time_seconds="$GEN_TIME_S"
export MANIFEST_total_elapsed_seconds="$TOTAL_ELAPSED_S"
export MANIFEST_finish_reason="$FINISH_REASON"
export MANIFEST_stop_type="$STOP_TYPE"
export MANIFEST_generation_truncated="$GEN_TRUNCATED"
export MANIFEST_llama_exit_status="$LLAMA_EXIT"
export MANIFEST_output_malformed_subtype="$OUTPUT_MALFORMED_SUBTYPE"
export MANIFEST_script_git_commit_hash="$SCRIPT_GIT_COMMIT"
export MANIFEST_script_git_dirty="$SCRIPT_GIT_DIRTY"
export MANIFEST_os_version="$OS_VERSION"
export MANIFEST_kernel_version="$KERNEL_VERSION"
export MANIFEST_kernel_full="$KERNEL_FULL"
export MANIFEST_gpu_driver_version="$GPU_DRIVER_VERSION"
export MANIFEST_cuda_or_rocm_version="$CUDA_VERSION"
export MANIFEST_llama_n="$LLAMA_N"
export MANIFEST_llama_context_size="$LLAMA_CONTEXT_SIZE"
export MANIFEST_llama_ngl="$LLAMA_NGL"
export MANIFEST_llama_temperature="$LLAMA_TEMPERATURE"
export MANIFEST_llama_top_p="$LLAMA_TOP_P"
export MANIFEST_llama_top_k="$LLAMA_TOP_K"
export MANIFEST_llama_repeat_penalty="$LLAMA_REPEAT_PENALTY"
export MANIFEST_llama_single_turn="$LLAMA_SINGLE_TURN"
export MANIFEST_llama_no_display_prompt="$LLAMA_NO_DISPLAY_PROMPT"
export MANIFEST_llama_simple_io="$LLAMA_SIMPLE_IO"
export MANIFEST_llama_perf="$LLAMA_PERF"
export MANIFEST_llama_show_timings="$LLAMA_SHOW_TIMINGS"
export MANIFEST_llama_verbose="$LLAMA_VERBOSE"
export MANIFEST_llama_command="$LLAMA_COMMAND"
export MANIFEST_llama_cpp_git_commit="$LLAMA_CPP_GIT_COMMIT"
export MANIFEST_llama_version="$LLAMA_VERSION"
export MANIFEST_llama_compiler="$LLAMA_COMPILER"
export MANIFEST_llama_cli_sha256="$LLAMA_CLI_SHA256"

python3 <<'PY'
import json
import os

def env(name, cast=None, default=None):
    v = os.environ.get(name, "")
    if v == "":
        return default
    if cast:
        try:
            return cast(v)
        except ValueError:
            return default
    return v

def as_bool(x):
    return x.lower() == "true"

def tri_bool(name):
    # "true" / "false" -> bool, anything else ("unknown", empty) -> null
    return {"true": True, "false": False}.get(os.environ.get(name, "").lower())

prompt_path = os.environ["MANIFEST_prompt_file_path_for_text"]
with open(prompt_path, "r", encoding="utf-8", errors="replace") as f:
    prompt_text = f.read()

manifest = {
    "run_number": env("MANIFEST_run_number", int),
    "quant": env("MANIFEST_quant"),
    "triplet_id": env("MANIFEST_triplet_id"),
    "condition": env("MANIFEST_condition"),
    "prompt_file": env("MANIFEST_prompt_file"),
    "prompt_sha256": env("MANIFEST_prompt_sha256"),
    "prompt_text": prompt_text,
    "model_file": env("MANIFEST_model_file"),
    "model_sha256": env("MANIFEST_model_sha256"),
    "seed": env("MANIFEST_seed", int),

    # generation parameters
    "model": env("MANIFEST_model_file"),
    "n": env("MANIFEST_llama_n", int),
    "context_size": env("MANIFEST_llama_context_size", int),
    "ngl": env("MANIFEST_llama_ngl", int),
    "temperature": env("MANIFEST_llama_temperature", float),
    "top_p": env("MANIFEST_llama_top_p", float),
    "top_k": env("MANIFEST_llama_top_k", int),
    "repeat_penalty": env("MANIFEST_llama_repeat_penalty", float),
    "single_turn": env("MANIFEST_llama_single_turn", as_bool),
    "no_display_prompt": env("MANIFEST_llama_no_display_prompt", as_bool),
    "simple_io": env("MANIFEST_llama_simple_io", as_bool),
    "perf": env("MANIFEST_llama_perf", as_bool),
    "show_timings": env("MANIFEST_llama_show_timings", as_bool),
    "verbose": env("MANIFEST_llama_verbose", int),
    "llama_command": env("MANIFEST_llama_command"),

    # results / diagnostics
    "prompt_tokens": env("MANIFEST_prompt_tokens", int),
    "output_tokens": env("MANIFEST_output_tokens", int),
    "prompt_time_seconds": env("MANIFEST_prompt_time_seconds", float),
    "generation_time_seconds": env("MANIFEST_generation_time_seconds", float),
    "total_elapsed_seconds": env("MANIFEST_total_elapsed_seconds", float),
    "finish_reason": env("MANIFEST_finish_reason"),
    "stop_type": env("MANIFEST_stop_type"),
    "generation_truncated": env("MANIFEST_generation_truncated", as_bool),
    "llama_exit_status": env("MANIFEST_llama_exit_status", int),
    "output_malformed_subtype": env("MANIFEST_output_malformed_subtype"),

    # provenance
    "llama_cpp_git_commit": env("MANIFEST_llama_cpp_git_commit"),
    "llama_version": env("MANIFEST_llama_version"),
    "llama_compiler": env("MANIFEST_llama_compiler"),
    "llama_cli_sha256": env("MANIFEST_llama_cli_sha256"),
    "script_git_commit_hash": env("MANIFEST_script_git_commit_hash"),
    "script_git_dirty": tri_bool("MANIFEST_script_git_dirty"),
    "os_version": env("MANIFEST_os_version"),
    "kernel_version": env("MANIFEST_kernel_version"),
    "kernel_full": env("MANIFEST_kernel_full"),
    "gpu_driver_version": env("MANIFEST_gpu_driver_version"),
    "cuda_or_rocm_version": env("MANIFEST_cuda_or_rocm_version"),
}

rundir = os.environ["RUNDIR"]
with open(os.path.join(rundir, "manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)
    f.write("\n")
PY

echo
echo "Done. Files written to: $RUNDIR"
echo "  gpu.csv, manifest.json, output.txt, prompt.txt, raw.txt, run.log, system.csv"

exit "$LLAMA_EXIT"
