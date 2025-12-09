# Whisper Model Configuration Guide

## The Out-of-Memory Issue (Fixed!)

### What Happened
The Celery worker was killed with `SIGKILL` because the Whisper **large** model (2.88GB) required ~10GB of RAM to load and run, causing an Out-of-Memory (OOM) error.

### The Fix
Changed the default Whisper model from `"large"` to `"base"` which is much more memory-efficient while still providing good transcription quality.

## Whisper Model Comparison

| Model    | Size   | RAM Required | Speed      | Accuracy | Recommended For              |
|----------|--------|--------------|------------|----------|------------------------------|
| `tiny`   | 39M    | ~1GB         | Very Fast  | Low      | Quick testing, low resources |
| `base`   | 74M    | ~1GB         | Fast       | Good     | **Default - Best balance**   |
| `small`  | 244M   | ~2GB         | Medium     | Better   | Higher quality needed        |
| `medium` | 769M   | ~5GB         | Slower     | High     | Professional use             |
| `large`  | 2.88GB | ~10GB        | Slow       | Highest  | Maximum accuracy (needs RAM) |
| `turbo`  | 809M   | ~6GB         | Fast       | High     | Best of both worlds          |

## How to Change the Model

### Method 1: Environment Variable (Easiest)

Add to your `.env` file:

```bash
# Use a different Whisper model
WHISPER_MODEL=base  # Options: tiny, base, small, medium, large, turbo

# If you have CUDA/GPU available
WHISPER_DEVICE=cuda
```

Then restart:
```bash
docker-compose restart celery-worker
```

### Method 2: Edit Config File

Edit `backend/app/config.py`:

```python
# Whisper model
whisper_model: str = "base"  # Change this
whisper_device: str = "cpu"  # or "cuda" if you have GPU
```

Then rebuild:
```bash
docker-compose up -d --build celery-worker
```

## Recommendations

### For Development / Limited RAM (< 8GB)
```bash
WHISPER_MODEL=base
```
Good transcription quality, low memory usage. **This is the default now.**

### For Production / Normal Use (8-16GB RAM)
```bash
WHISPER_MODEL=small
```
Better accuracy, reasonable memory usage.

### For Maximum Accuracy (16GB+ RAM)
```bash
WHISPER_MODEL=medium
```
High accuracy without the extreme memory requirements of "large".

### If You Have a GPU
```bash
WHISPER_MODEL=turbo
WHISPER_DEVICE=cuda
```
Fast and accurate! Best option if you have NVIDIA GPU with CUDA.

## Testing Your Video Now

1. Go to **http://localhost:5173/admin**
2. Click the **"Restart Processing"** button next to your video
3. Monitor progress:
   ```bash
   docker-compose logs -f celery-worker
   ```

You should see:
- ✅ Model downloading (much smaller: ~74MB for base)
- ✅ Transcription progress
- ✅ LightRAG processing
- ✅ Status changes to "completed"

## Troubleshooting

### Still Getting Killed?
If you still see `SIGKILL` with the `base` model:

1. **Increase Docker memory limit**:
   - Docker Desktop → Settings → Resources → Memory
   - Set to at least 4GB

2. **Use the tiny model**:
   ```bash
   WHISPER_MODEL=tiny
   ```

3. **Check system resources**:
   ```bash
   docker stats
   ```

### Model Already Downloaded?
Whisper caches models in `~/.cache/whisper/`. If you already downloaded "large", it won't be used anymore. The "base" model will download on first use (~74MB).

### Want to Use OpenAI Whisper API Instead?
If local processing is too resource-intensive, you can switch to OpenAI's cloud API (requires credits but no local RAM):

```python
# In backend/app/tasks/video_tasks.py
from openai import OpenAI

client = OpenAI(api_key=settings.openai_api_key)
audio_file = open(video.file_path, "rb")
transcript = client.audio.transcriptions.create(
    model="whisper-1",
    file=audio_file
)
```

This would eliminate local memory issues entirely, but would cost ~$0.006 per minute of audio.

## Current Configuration

**Default Model**: `base` (74MB, ~1GB RAM)  
**Override via**: `.env` file with `WHISPER_MODEL` variable  
**Device**: CPU (set `WHISPER_DEVICE=cuda` if you have GPU)

---

**The issue is fixed!** Your video should now process successfully with the smaller, more memory-efficient model. 🎉

