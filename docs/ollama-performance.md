# Ollama Performance Guide

## Overview

This guide helps you choose Ollama models for Hired. based on your hardware and tolerance for wait times. Model speed varies significantly based on CPU, GPU, and RAM.

## Recommended Models

### Fast (10-20s per request) — **Best for most users**
- **`llama3.2:3b`** (1.7 GB)
  - 3 billion parameters
  - Fastest inference (~15-20s on CPU)
  - Minimal quality tradeoff for job-related tasks
  - Recommended for laptops or systems with <8GB RAM
  - **Pull command**: `ollama pull llama3.2:3b`

### Medium (30-50s per request)
- **`llama3.2:8b`** (4.9 GB)
  - 8 billion parameters
  - ~30-40s inference on CPU, ~3-5s with GPU
  - Better reasoning; good for complex CVs or interviews
  - Requires 8GB+ RAM
  - **Pull command**: `ollama pull llama3.2:8b`

### Slow (40-60s+ per request)
- **`llama3.1:8b`** (4.6 GB)
  - 8 billion parameters, earlier version of llama3.2:8b
  - ~40-50s inference on CPU
  - Similar quality to llama3.2:8b but slightly slower
  - Use llama3.2:8b instead if available
  - **Current status**: Already pulled in your environment

## Switching Models

1. **Stop the Hired app** (quit Tauri window)
2. **Start Ollama** (if not already running): `ollama serve`
3. **Pull a new model**: `ollama pull llama3.2:3b`
4. **Restart Hired app**
5. **Go to Settings → Switch Provider**
6. Select **Ollama** from the provider list
7. Choose the new model from the dropdown
8. Click **Test Provider** to verify
9. Click **Select Provider** to save

## Performance Tips

### CPU-only Systems
- Use `llama3.2:3b` for fast inference
- Close other applications to free RAM
- Inference speed depends on CPU cores (4 cores: ~40s, 8 cores: ~20s, 16 cores: ~10s)

### With GPU Acceleration
- Excellent news! Ollama auto-detects NVIDIA/AMD/Apple Silicon GPUs
- `llama3.2:8b` runs in ~3-5 seconds on GPU
- See [Ollama GPU documentation](https://github.com/ollama/ollama#gpu-support)

### With Limited RAM (<8GB)
- Use `llama3.2:3b` (requires ~2-3 GB)
- Avoid `llama3.1:8b` or `llama3.2:8b` (require ~5-6 GB)

## Timeout Configuration

- Frontend timeout: **180 seconds** (set in `frontend/src/lib/api.ts`)
- Backend timeout per request: **180 seconds** (set in `backend/llm/ollama.py`)
- These should cover all models listed above, even on CPU-only systems

## Troubleshooting Slow Requests

**Symptom**: "Internal Server Error" or "Request timeout" when uploading CV

**Causes & Solutions**:
1. Model is legitimately slow (expected for `llama3.1:8b` on CPU)
   - Switch to `llama3.2:3b` for 2-3x speedup
   - Or wait 60+ seconds for response
2. Ollama is not responding
   - Check Ollama is running: `ollama serve` in terminal
   - Verify with `curl http://localhost:11434/api/tags`
3. System is low on RAM
   - Close other applications
   - Restart Ollama and Hired app

## Measuring Your System's Speed

To measure how fast *your* system runs a specific model:

```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Time a single inference (run a 100-token generation)
time curl -X POST http://localhost:11434/api/generate \
  -d '{"model": "llama3.2:3b", "prompt": "Tell me about your capabilities:", "stream": false}' \
  | jq '.response' | wc -c
```

Typical times:
- `llama3.2:3b`: 10-20 seconds
- `llama3.2:8b`: 25-40 seconds (CPU), 3-5 seconds (GPU)
- `llama3.1:8b`: 40-60 seconds (CPU), 3-5 seconds (GPU)

## Model Recommendations by Use Case

| Use Case | Recommended | Reason |
|----------|-------------|--------|
| **Quick test** | `llama3.2:3b` | Minimal resources, instant feedback |
| **Production (no GPU)** | `llama3.2:3b` | Good balance of speed and quality |
| **Production (GPU available)** | `llama3.2:8b` | Better reasoning, fast with GPU |
| **Interview prep** | `llama3.2:8b` or better | Complex coaching needs accuracy |
| **Legacy (already have)** | Keep `llama3.1:8b` | Works fine; just wait 60s |

## See Also
- [Backend LLM configuration](../backend/llm/README.md) (if exists)
- [Ollama official docs](https://github.com/ollama/ollama)
- [LLM provider comparison](../docs/PROJECT_DOC.md#llm-providers)
