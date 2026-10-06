# Configuration Setup Guide

## 📋 Overview

This guide explains how to set up model configurations and API keys for the three-way evaluation system. We support two methods:
1. **Config file** (recommended for production)
2. **Environment variables** (recommended for development)

---

## 🚀 Quick Start

### Method 1: Using Config File (Recommended)

```bash
# 1. Copy example config
copy config.example.json config.json

# 2. Edit config.json with your API keys
#    Open config.json and replace:
#    - "your-openai-api-key-here" → Your OpenAI API key
#    - "your-anthropic-api-key-here" → Your Anthropic API key

# 3. Run evaluation with config file
python mindeval/scripts/run_three_way_evaluation.py \
    --input_dialogues_path data/simpsydial/raw \
    --source_language zh \
    --output_dir data/simpsydial/three_way_comparison \
    --config_path config.json \
    --max_dialogues 5
```

### Method 2: Using Environment Variables

```bash
# 1. Set environment variables (Windows)
set TRANSLATION_MODEL=gpt-4
set TRANSLATION_API_KEY=your-openai-api-key
set JUDGE_MODEL=claude-sonnet-4
set JUDGE_API_KEY=your-anthropic-api-key

# 2. Run evaluation
python mindeval/scripts/run_three_way_evaluation.py \
    --input_dialogues_path data/simpsydial/raw \
    --source_language zh \
    --output_dir data/simpsydial/three_way_comparison \
    --max_dialogues 5
```

---

## 📁 Config File Structure

### Full Example (`config.json`)

The `judges` section supports multiple named judges (`gpt`, `claude`, `qwen`).
Select which judge to use at runtime via `--judge_name <name>`.

```json
{
  "translation": {
    "model": "gpt-5.1",
    "api_key": "sk-...",
    "api_base": "https://api.openai.com/v1",
    "temperature": 0.3,
    "timeout": 60,
    "max_retries": 3
  },
  "judges": {
    "gpt": {
      "model": "gpt-5.1",
      "api_key": "sk-...",
      "api_base": "https://api.openai.com/v1",
      "temperature": 0.3,
      "timeout": 60,
      "max_retries": 3
    },
    "claude": {
      "model": "anthropic/claude-sonnet-4-6",
      "api_key": "sk-ant-...",
      "temperature": 0.3,
      "timeout": 180,
      "max_retries": 3
    },
    "qwen": {
      "model": "qwen3-235b-a22b",
      "api_key": "sk-...",
      "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "temperature": 0.3,
      "timeout": 180,
      "max_retries": 3
    }
  },
  "google_translate": {
    "credentials_path": "C:/path/to/google-credentials.json",
    "project_id": "your-project-id",
    "location": "global"
  }
}
```

### Minimal Example

```json
{
  "translation": {
    "model": "gpt-5.1",
    "api_key": "your-openai-key"
  },
  "judges": {
    "gpt": { "model": "gpt-5.1", "api_key": "your-openai-key" },
    "claude": { "model": "anthropic/claude-sonnet-4-6", "api_key": "your-anthropic-key" },
    "qwen": { "model": "qwen3-235b-a22b", "api_key": "your-dashscope-key", "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1" }
  }
}
```

---

## 🔧 Configuration Options

### Translation Model Options

| Parameter | Description | Default | Required |
|-----------|-------------|---------|----------|
| `model` | Model name | `"gpt-4"` | Yes |
| `api_key` | API key | `""` | Yes |
| `api_base` | API base URL | `null` | No |
| `temperature` | Creativity (0-1) | `0.3` | No |
| `max_tokens` | Max tokens per response | `null` | No |
| `timeout` | Request timeout (seconds) | `60` | No |
| `max_retries` | Max retry attempts | `3` | No |

**Supported models:**
- `gpt-4`, `gpt-4-turbo`, `gpt-4o`
- `claude-3-opus`, `claude-3-sonnet`, `claude-3-haiku`
- `gemini-pro`, `gemini-ultra`
- Any model supported by [litellm](https://docs.litellm.ai/docs/providers)

### Judge Model Options

Same parameters as translation model. Three judges are configured by default:

| Judge key | Provider | Model | API Base |
|-----------|----------|-------|----------|
| `gpt` | OpenAI | `gpt-5.1` | `https://api.openai.com/v1` |
| `claude` | Anthropic | `anthropic/claude-sonnet-4-6` | *(LiteLLM default)* |
| `qwen` | Alibaba DashScope | `qwen3-235b-a22b` | `https://dashscope.aliyuncs.com/compatible-mode/v1` |

**Getting a DashScope API key (Qwen3):**
1. Register at [https://dashscope.aliyuncs.com](https://dashscope.aliyuncs.com)
2. Go to **API-KEY management** → Create a new key
3. The key format is `sk-...` (same format as OpenAI)
4. Fill in `config.json` → `judges.qwen.api_key`

**Alternative Qwen3 models** (replace `model` in config):
- `qwen3-235b-a22b` — flagship MoE, 235B params / 22B active (recommended)
- `qwen3-72b` — dense, strong reasoning
- `qwen3-32b` — balanced speed/quality

**Run with Qwen3 judge:**
```bash
python -m mindeval.scripts.run_eval_matrix --pilot --eval mind-eval --judge_name qwen --max_workers 1 --batch_delay 3
```

### Google Translate Options

| Parameter | Description | Required |
|-----------|-------------|----------|
| `credentials_path` | Path to Google Cloud credentials JSON | Yes |
| `project_id` | Google Cloud project ID | Yes |
| `location` | Translation location | No |

---

## 🌍 Environment Variables

### Translation Model

| Variable | Description | Example |
|----------|-------------|---------|
| `TRANSLATION_MODEL` | Model name | `gpt-4` |
| `TRANSLATION_API_KEY` | API key | `sk-...` |
| `TRANSLATION_API_BASE` | API base URL | `https://api.openai.com/v1` |
| `TRANSLATION_TEMPERATURE` | Temperature | `0.3` |
| `TRANSLATION_MAX_TOKENS` | Max tokens | `4000` |
| `TRANSLATION_TIMEOUT` | Timeout (seconds) | `60` |
| `TRANSLATION_MAX_RETRIES` | Max retries | `3` |

### Judge Model

| Variable | Description | Example |
|----------|-------------|---------|
| `JUDGE_MODEL` | Model name | `claude-sonnet-4` |
| `JUDGE_API_KEY` | API key | `sk-ant-...` |
| `JUDGE_API_BASE` | API base URL | `https://api.anthropic.com` |
| `JUDGE_TEMPERATURE` | Temperature | `0.3` |
| `JUDGE_MAX_TOKENS` | Max tokens | `4000` |
| `JUDGE_TIMEOUT` | Timeout (seconds) | `60` |
| `JUDGE_MAX_RETRIES` | Max retries | `3` |

### Google Translate

| Variable | Description | Example |
|----------|-------------|---------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Credentials path | `C:/path/to/credentials.json` |
| `GOOGLE_CLOUD_PROJECT` | Project ID | `your-project-id` |

---

## 🛠️ Setup Scripts

### Windows Setup Script (`setup_config.bat`)

```batch
@echo off
echo Setting up environment variables...

set TRANSLATION_MODEL=gpt-4
set TRANSLATION_API_KEY=your-openai-key-here
set JUDGE_MODEL=claude-sonnet-4
set JUDGE_API_KEY=your-anthropic-key-here

echo Environment variables set!
echo.
echo To verify, run:
echo python -c "from mindeval.config import print_config_summary; print_config_summary()"
```

### Linux/Mac Setup Script (`setup_config.sh`)

```bash
#!/bin/bash
echo "Setting up environment variables..."

export TRANSLATION_MODEL="gpt-4"
export TRANSLATION_API_KEY="your-openai-key-here"
export JUDGE_MODEL="claude-sonnet-4"
export JUDGE_API_KEY="your-anthropic-key-here"

echo "Environment variables set!"
echo ""
echo "To verify, run:"
echo "python -c 'from mindeval.config import print_config_summary; print_config_summary()'"
```

---

## 🔍 Verification

### Check Configuration

```bash
# Method 1: Using Python
python -c "from mindeval.config import print_config_summary; print_config_summary()"

# Method 2: Using config script
python mindeval/config.py
```

**Expected output:**
```
==================================================
  CONFIGURATION SUMMARY
==================================================

Translation Model:
  Model: gpt-4
  API Base: Default
  Temperature: 0.3
  API Key: ✓ Set

Judge Model:
  Model: claude-sonnet-4
  API Base: Default
  Temperature: 0.3
  API Key: ✓ Set

Validation:
  ✓ Translation
  ✓ Judge
```

### Test API Connectivity

```python
# test_api.py
from mindeval.config import get_translation_config, get_judge_config
from mindeval.inference import InferenceEngine

# Test translation model
translation_config = get_translation_config()
translation_model = InferenceEngine(translation_config)
response = translation_model.generate([{"role": "user", "content": "Hello"}])
print(f"Translation model test: {response[:50]}...")

# Test judge model
judge_config = get_judge_config()
judge_model = InferenceEngine(judge_config)
response = judge_model.generate([{"role": "user", "content": "Hello"}])
print(f"Judge model test: {response[:50]}...")
```

---

## 🔒 Security Best Practices

### 1. Never Commit API Keys

```bash
# Add to .gitignore
echo "config.json" >> .gitignore
echo "*.key" >> .gitignore
echo "*.env" >> .gitignore
```

### 2. Use Different Keys for Different Environments

```json
// config.dev.json (development)
{
  "translation": {
    "model": "gpt-3.5-turbo",  // Cheaper for dev
    "api_key": "dev-key-123"
  }
}

// config.prod.json (production)
{
  "translation": {
    "model": "gpt-4",
    "api_key": "prod-key-456"
  }
}
```

### 3. Rotate Keys Regularly

- Set calendar reminders
- Use key management services
- Monitor usage alerts

### 4. Limit Key Permissions

- Use API keys with minimal permissions
- Set usage quotas
- Enable logging

---

## 🚨 Troubleshooting

### Issue: "API key not set"

**Solution:**
```bash
# Check if keys are set
python -c "from mindeval.config import print_config_summary; print_config_summary()"

# If not set, set them:
# Method 1: Edit config.json
# Method 2: Set environment variables
set TRANSLATION_API_KEY=your-key
set JUDGE_API_KEY=your-key
```

### Issue: "Invalid API key"

**Solution:**
1. Verify key is correct
2. Check if key has expired
3. Verify billing is active
4. Check rate limits

### Issue: "Model not found"

**Solution:**
1. Check model name spelling
2. Verify model is available in your region
3. Check API base URL

### Issue: "Timeout error"

**Solution:**
```json
{
  "translation": {
    "timeout": 120,  // Increase timeout
    "max_retries": 5  // Increase retries
  }
}
```

---

## 📊 Cost Management

### Estimate Costs

```python
# cost_estimator.py
def estimate_cost(num_dialogues: int, avg_tokens: int = 1000):
    """
    Estimate evaluation cost.
    
    GPT-4: ~$0.03/1K tokens input, $0.06/1K tokens output
    Claude Sonnet: ~$3/1M tokens input, $15/1M tokens output
    """
    gpt4_cost = num_dialogues * avg_tokens * 0.03 / 1000
    claude_cost = num_dialogues * avg_tokens * 3 / 1000000
    
    return {
        "gpt4_translation": gpt4_cost,
        "claude_judge": claude_cost,
        "total": gpt4_cost + claude_cost
    }

# Example: 1000 dialogues
cost = estimate_cost(1000)
print(f"Estimated cost: ${cost['total']:.2f}")
```

### Set Budget Limits

```json
{
  "translation": {
    "max_tokens": 2000,  // Limit tokens per request
    "max_retries": 2     // Limit retries to control cost
  }
}
```

---

## 🔄 Switching Between Configurations

### Multiple Projects

```bash
# Project A (SimPsyDial)
python run_three_way_evaluation.py \
    --config_path config_simpsydial.json \
    --output_dir results/simpsydial

# Project B (KMI)
python run_three_way_evaluation.py \
    --config_path config_kmi.json \
    --output_dir results/kmi
```

### Different Model Combinations

```json
// config_fast.json (faster, cheaper)
{
  "translation": {
    "model": "gpt-3.5-turbo"
  },
  "judge": {
    "model": "claude-haiku"
  }
}

// config_accurate.json (slower, more accurate)
{
  "translation": {
    "model": "gpt-4"
  },
  "judge": {
    "model": "claude-opus"
  }
}
```

---

## 📚 Additional Resources

- [OpenAI API Documentation](https://platform.openai.com/docs/api-reference)
- [Anthropic API Documentation](https://docs.anthropic.com/claude/reference/getting-started-with-the-api)
- [Google Cloud Translation API](https://cloud.google.com/translate/docs)
- [LiteLLM Supported Models](https://docs.litellm.ai/docs/providers)

---

## ✅ Checklist

- [ ] Create `config.json` from `config.example.json`
- [ ] Fill in API keys
- [ ] Test configuration with `print_config_summary()`
- [ ] Add `config.json` to `.gitignore`
- [ ] Set up environment variables (optional)
- [ ] Test API connectivity
- [ ] Estimate costs for your dataset size
- [ ] Set budget limits if needed

---

**Configuration is now ready! 🚀**
