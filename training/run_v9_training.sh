#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# TITAN V9.0 — Master Training Execution Pipeline
# ═══════════════════════════════════════════════════════════════
# One-command execution: data gen → modelfile rebuild → LoRA fine-tuning
#
# Usage:
#   bash run_v9_training.sh              # Full pipeline (all 3 models)
#   bash run_v9_training.sh --phase 1    # Only generate data
#   bash run_v9_training.sh --phase 2    # Only rebuild Ollama models
#   bash run_v9_training.sh --phase 3    # Only LoRA fine-tune
#   bash run_v9_training.sh --model fast # Only fine-tune titan-fast
#
# Estimated time:
#   Phase 1: ~5 minutes (17,100 examples)
#   Phase 2: ~2 minutes (3 Ollama models)
#   Phase 3: ~72-96 hours (3 LoRA fine-tuning runs)
# ═══════════════════════════════════════════════════════════════

set -e

TITAN_DIR="/opt/titan"
TRAINING_DIR="$TITAN_DIR/training"
DATA_DIR="$TRAINING_DIR/data_v9"
MODELFILE_DIR="$TRAINING_DIR/phase1"
GENERATOR_DIR="$TRAINING_DIR/phase2"
FINETUNE_DIR="$TRAINING_DIR/phase3"
LOG_DIR="$TRAINING_DIR/logs"
EXAMPLES_PER_TASK=300

# Parse args
PHASE="all"
MODEL="all"
while [[ $# -gt 0 ]]; do
    case $1 in
        --phase) PHASE="$2"; shift 2 ;;
        --model) MODEL="$2"; shift 2 ;;
        --count) EXAMPLES_PER_TASK="$2"; shift 2 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

mkdir -p "$LOG_DIR"
LOGFILE="$LOG_DIR/v9_training_$(date +%Y%m%d_%H%M%S).log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOGFILE"; }

# ═══════════════════════════════════════════════════════════════
# BANNER
# ═══════════════════════════════════════════════════════════════
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo " TITAN V9.0 — Master Training Pipeline"
echo "═══════════════════════════════════════════════════════════════"
echo " Phase:           $PHASE"
echo " Model:           $MODEL"
echo " Examples/task:   $EXAMPLES_PER_TASK"
echo " Total tasks:     57"
echo " Total examples:  $((57 * EXAMPLES_PER_TASK))"
echo " Log:             $LOGFILE"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# ═══════════════════════════════════════════════════════════════
# PHASE 1: Generate Training Data
# ═══════════════════════════════════════════════════════════════
if [[ "$PHASE" == "all" || "$PHASE" == "1" ]]; then
    log "═══ PHASE 1: Generating Training Data ═══"
    log "Generating $EXAMPLES_PER_TASK examples per task (57 tasks)..."

    cd "$GENERATOR_DIR"
    python3 generate_training_data_v9.py \
        --count "$EXAMPLES_PER_TASK" \
        --output "$DATA_DIR" \
        --validate \
        --combined \
        2>&1 | tee -a "$LOGFILE"

    # Verify
    TASK_COUNT=$(ls "$DATA_DIR"/*.jsonl 2>/dev/null | grep -v combined | wc -l)
    TOTAL_LINES=$(cat "$DATA_DIR"/*.jsonl 2>/dev/null | wc -l)
    log "Phase 1 complete: $TASK_COUNT task files, $TOTAL_LINES total examples"
    echo ""
fi

# ═══════════════════════════════════════════════════════════════
# PHASE 2: Rebuild Ollama Models with V9 Modelfiles
# ═══════════════════════════════════════════════════════════════
if [[ "$PHASE" == "all" || "$PHASE" == "2" ]]; then
    log "═══ PHASE 2: Rebuilding Ollama Models ═══"

    # Check Ollama is running
    if ! ollama list >/dev/null 2>&1; then
        log "ERROR: Ollama not running. Start with: systemctl start ollama"
        exit 1
    fi

    for model_name in analyst strategist fast; do
        if [[ "$MODEL" != "all" && "$MODEL" != "$model_name" ]]; then
            continue
        fi

        modelfile="$MODELFILE_DIR/titan-${model_name}-v9.modelfile"
        if [[ ! -f "$modelfile" ]]; then
            log "WARNING: $modelfile not found, skipping"
            continue
        fi

        log "Creating titan-${model_name} from V9 Modelfile..."
        ollama create "titan-${model_name}" -f "$modelfile" 2>&1 | tee -a "$LOGFILE"
        log "titan-${model_name} rebuilt successfully"
    done

    # Verify
    log "Verifying Ollama models..."
    ollama list | tee -a "$LOGFILE"
    echo ""
fi

# ═══════════════════════════════════════════════════════════════
# PHASE 3: LoRA Fine-Tuning
# ═══════════════════════════════════════════════════════════════
if [[ "$PHASE" == "all" || "$PHASE" == "3" ]]; then
    log "═══ PHASE 3: LoRA Fine-Tuning ═══"

    # Check training data exists
    if [[ ! -d "$DATA_DIR" ]] || [[ $(ls "$DATA_DIR"/*.jsonl 2>/dev/null | wc -l) -lt 10 ]]; then
        log "ERROR: Training data not found in $DATA_DIR. Run phase 1 first."
        exit 1
    fi

    cd "$FINETUNE_DIR"

    for model_name in analyst strategist fast; do
        if [[ "$MODEL" != "all" && "$MODEL" != "$model_name" ]]; then
            continue
        fi

        MODEL_LOG="$LOG_DIR/v9_lora_${model_name}_$(date +%Y%m%d_%H%M%S).log"
        log "Starting LoRA fine-tuning for titan-${model_name}..."
        log "  Log: $MODEL_LOG"

        python3 lora_finetune_v9.py \
            --task "$model_name" \
            2>&1 | tee -a "$MODEL_LOG" "$LOGFILE"

        log "titan-${model_name} fine-tuning complete"
        echo ""
    done
fi

# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════
log "═══════════════════════════════════════════════════════════════"
log " TITAN V9.0 Training Pipeline Complete"
log "═══════════════════════════════════════════════════════════════"
log " Training data: $DATA_DIR"
log " LoRA adapters: $TITAN_DIR/training/models_v9/"
log " ONNX models:   $TITAN_DIR/training/onnx_v9/"
log " Logs:          $LOG_DIR"
log ""
log " Next steps to deploy:"
log "   1. Merge LoRA adapters into base models"
log "   2. Convert to GGUF format"
log "   3. Rebuild Ollama models with fine-tuned weights"
log "   4. Run evaluation suite"
log "═══════════════════════════════════════════════════════════════"
