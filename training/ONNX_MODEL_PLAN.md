# TITAN OS — Single ONNX Model Deployment Plan

## VPS Hardware Constraints
- **CPU**: AMD EPYC 9354P (8 vCPU, no GPU)
- **RAM**: 31GB (need ~8GB for OS + services, ~23GB available)
- **ONNX Runtime**: 1.24.2 with CPUExecutionProvider
- **Requirement**: Single tiny model replaces 3 Ollama models (analyst/strategist/fast)

## Model Selection Analysis

### Candidates Compared (CPU-only, INT4 quantized)

| Model | Params | INT4 Size | CPU tok/s | Quality | Verdict |
|-------|--------|-----------|-----------|---------|---------|
| Phi-4-mini-instruct ONNX INT4 | 3.8B | ~2.2GB | 15-25 tok/s | Excellent reasoning, 128K ctx | **WINNER** |
| Qwen2.5-1.5B-Instruct GGUF Q4 | 1.5B | ~1.0GB | 30-50 tok/s | Good for JSON, weaker reasoning | Runner-up for speed |
| SmolLM2-1.7B | 1.7B | ~1.1GB | 35-45 tok/s | Good general, weak specialized | Too weak |
| Phi-3.5-mini ONNX INT4 | 3.8B | ~2.2GB | 15-20 tok/s | Strong but older than Phi-4 | Superseded |
| Qwen2.5-3B-Instruct | 3B | ~1.8GB | 20-30 tok/s | Good JSON output | Close second |

### **RECOMMENDED: Phi-4-mini-instruct ONNX INT4**

**Why Phi-4-mini wins:**
1. **3.8B params INT4 = ~2.2GB RAM** — fits easily in 31GB VPS
2. **MIT license** — no restrictions
3. **Official ONNX INT4 build** from Microsoft (not community conversion)
4. **15-25 tokens/sec on CPU** — fast enough for real-time copilot
5. **128K context** — can process entire operation contexts
6. **Excellent at**: reasoning, JSON output, instruction following, code analysis
7. **Single model replaces all 3** Ollama models (saves ~14GB RAM)
8. Uses `onnxruntime-genai` for optimized CPU inference

### Fallback: Keep Ollama qwen2.5:7b for heavy reasoning tasks
- Phi-4-mini handles 95% of tasks
- For complex multi-step strategy planning, fall back to Ollama qwen2.5:7b (already installed)

## Deployment Commands

```bash
# Install ONNX Runtime GenAI
pip install onnxruntime-genai

# Download Phi-4-mini ONNX INT4 (~2.2GB)
huggingface-cli download microsoft/Phi-4-mini-instruct-onnx \
  --include cpu_and_mobile/cpu-int4-rtn-block-32-acc-level-4/* \
  --local-dir /opt/titan/models/phi4-mini-onnx

# Test
python3 -c "
import onnxruntime_genai as og
model = og.Model('/opt/titan/models/phi4-mini-onnx/cpu_and_mobile/cpu-int4-rtn-block-32-acc-level-4')
tokenizer = og.Tokenizer(model)
print('Phi-4-mini ONNX loaded OK')
"
```

## Training Data Format

Training data uses **ChatML format** (same as existing V9 generators):
```json
{"messages": [
  {"role": "system", "content": "You are TITAN-OPERATOR..."},
  {"role": "user", "content": "<task prompt>"},
  {"role": "assistant", "content": "<chain-of-thought reasoning + structured output>"}
]}
```

## After Fine-tuning
- Export fine-tuned model to ONNX INT4 using `optimum` library
- Deploy to `/opt/titan/models/titan-operator-onnx/`
- Update `llm_config.json` to route tasks to ONNX model
