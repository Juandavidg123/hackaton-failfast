# ERP Voice Chat System - Setup Guide

## Prerequisites

- Python 3.9 or higher
- uv package manager (install from https://docs.astral.sh/uv/getting-started/installation/)
- Ollama (for local LLM)

### Installing uv

If you don't have `uv` installed, install it using one of these methods:

#### Windows (PowerShell)
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### macOS/Linux
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Using pip
```bash
pip install uv
```

## Installation Steps

### 1. Install Dependencies

```bash
uv sync
```

### 2. Install and Configure Ollama

#### Windows
1. Download Ollama from https://ollama.ai/download
2. Run the installer
3. Open a terminal and verify installation:
   ```bash
   ollama --version
   ```

#### macOS
```bash
brew install ollama
```

#### Linux
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### 3. Pull Llama 3 Model

After installing Ollama, pull the Llama 3 model:

```bash
ollama pull llama3
```

This will download the free Llama 3 model (approximately 4.7GB).

### 4. Verify Ollama is Running

Start the Ollama service (if not already running):

```bash
ollama serve
```

Test the model:

```bash
ollama run llama3 "Hola, ¿cómo estás?"
```

### 5. Configure Environment Variables

1. Copy `.env.example` to `.env.local`:
   ```bash
   cp .env.example .env.local
   ```

2. Update the following variables in `.env.local`:
   - `LIVEKIT_URL`: Your LiveKit server URL
   - `LIVEKIT_API_KEY`: Your LiveKit API key
   - `LIVEKIT_API_SECRET`: Your LiveKit API secret
   - `SUPABASE_URL`: Your Supabase project URL
   - `SUPABASE_KEY`: Your Supabase anon key
   - `FLASK_SECRET_KEY`: Generate a secure random key

### 6. Set Up Supabase Database

1. Create a new Supabase project at https://supabase.com
2. Copy your project URL and anon key to `.env.local`
3. Run the database migrations:
   ```bash
   uv run python scripts/apply_migrations.py
   ```
4. Seed sample data for testing:
   ```bash
   uv run python scripts/seed_sample_data.py
   ```

The sample data includes intentional duplicates and inconsistencies for testing the duplicate detection and inconsistency analysis features. See [scripts/README.md](scripts/README.md) for details.

### 7. Install Whisper Dependencies

Whisper requires ffmpeg for audio processing:

#### Windows
Download from https://ffmpeg.org/download.html and add to PATH

#### macOS
```bash
brew install ffmpeg
```

#### Linux
```bash
sudo apt-get install ffmpeg
```

### 8. Install Piper TTS

Piper TTS is not available via pip. For now, we'll use alternative TTS solutions:

**Option 1: Use LiveKit's built-in TTS providers**
- The LiveKit agent can use Cartesia, ElevenLabs, or other TTS providers
- Configure in the agent code

**Option 2: Use gTTS (Google Text-to-Speech)**
```bash
uv pip install gtts
```

**Option 3: Install Piper manually**
- Download from https://github.com/rhasspy/piper/releases
- Follow platform-specific installation instructions

Note: For the initial implementation, we'll use LiveKit's inference TTS which supports multiple providers.

## Running the Application

### Start the Flask Backend
```bash
uv run python -m src.api.app
```

### Start the LiveKit Agent
```bash
uv run python src/agent.py dev
```

## Database Management

### Seed Sample Data

The project includes scripts to populate the database with sample ERP data:

```bash
# Seed sample data (customers, products, orders)
uv run python scripts/seed_sample_data.py

# Reset database to empty state
uv run python scripts/reset_database.py

# Reset and seed in one command (recommended)
uv run python scripts/reset_and_seed.py --confirm
```

The sample data includes:
- 10 customers (with 3 groups of intentional duplicates)
- 10 products (with 2 groups of intentional duplicates)
- 6 orders (with calculation and referential integrity issues)
- 10 order items (with various inconsistencies)

See [scripts/README.md](scripts/README.md) for detailed documentation.

## Testing

Run tests with:
```bash
uv run pytest
```

## Troubleshooting

### Ollama Connection Issues
- Ensure Ollama is running: `ollama serve`
- Check the Ollama URL in `.env.local` (default: http://localhost:11434)

### Whisper Model Download
- On first use, Whisper will download the model (base: ~140MB)
- Ensure you have a stable internet connection

### Piper TTS Voice Model
- Spanish voice models will be downloaded automatically on first use
- Check available voices at https://github.com/rhasspy/piper

## Free Model Configuration

This project uses entirely free and open-source models:

- **LLM**: Llama 3 via Ollama (local, free)
- **STT**: OpenAI Whisper (local, free)
- **TTS**: Piper TTS (local, free, open-source)

All models run locally, ensuring privacy and no API costs.
