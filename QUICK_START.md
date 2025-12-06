# Quick Start Guide - ERP Voice Chat Agent

## Prerequisites

1. **Get a free Deepgram API key** (for Speech-to-Text):
   - Go to: https://console.deepgram.com/signup
   - Sign up for a free account (includes $200 credit)
   - Copy your API key
   - Add it to your `.env` file: `DEEPGRAM_API_KEY=your-key-here`

2. **Get a free Cartesia API key** (for Text-to-Speech):
   - Go to: https://cartesia.ai
   - Sign up for a free account
   - Copy your API key from the dashboard
   - Add it to your `.env` file: `CARTESIA_API_KEY=your-key-here`

3. **Ollama** must be running with Llama 3.1 model:
   ```bash
   ollama pull llama3.1
   ollama run llama3.1
   ```
   Note: We use llama3.1 (8B) which supports function calling (tools). Llama3 and llama3.2 do NOT support tools.

4. **Flask Backend** must be running:
   ```bash
   # In Terminal 1
   uv run python -m src.api.app
   ```

## Starting the Voice Agent

1. **Start the agent in dev mode:**
   ```bash
   # In Terminal 2
   uv run python src/agent.py dev
   ```

2. **Look for the connection URL** in the output. It will look like:
   ```
   Agent running in dev mode. Connect to it at:
   https://agents-playground.livekit.io/#...
   ```

3. **Click the URL** to open the LiveKit Playground in your browser

4. **In the Playground:**
   - Click "Connect" button
   - Allow microphone access when prompted
   - Start speaking in Spanish!

## Example Commands (in Spanish)

### Query ERP Data
- "Muéstrame todos los clientes" - Show me all customers
- "Busca productos" - Search for products
- "Muéstrame las órdenes" - Show me the orders
- "Busca clientes con nombre Juan" - Search for customers named Juan

### Detect Duplicates
- "Detecta duplicados en clientes" - Detect duplicates in customers
- "Busca duplicados" - Find duplicates
- "Muéstrame los duplicados" - Show me the duplicates

### Manage Duplicates
- "Muéstrame los detalles del primer grupo de duplicados" - Show me details of the first duplicate group
- "Combina estos duplicados" - Merge these duplicates

### Detect Inconsistencies
- "Busca inconsistencias" - Find inconsistencies
- "Detecta problemas en los datos" - Detect data problems
- "Muéstrame las inconsistencias" - Show me the inconsistencies

### Fix Inconsistencies
- "Arregla esta inconsistencia" - Fix this inconsistency
- "Corrige este problema" - Correct this problem

## Troubleshooting

### "Connection failed"
- Make sure Flask backend is running on port 5000
- Check that your `.env` file has correct LiveKit credentials

### "No response from agent"
- Verify Ollama is running: `ollama list`
- Check that llama3.1 model is available: `ollama run llama3.1`
- Make sure you have added your Cartesia API key to `.env`
- If you see "does not support tools" error, make sure you're using llama3.1, not llama3 or llama3.2

### "No data found"
- Seed the database with sample data:
  ```bash
  uv run python scripts/reset_and_seed.py
  ```

## Architecture

```
You (Voice) → LiveKit Agent → Flask API → Supabase Database
                    ↓
                 Ollama (LLM)
```

The agent:
1. Listens to your voice (Spanish)
2. Transcribes it using Deepgram (Spanish STT)
3. Processes your request using Llama 3.1 via Ollama (with function calling support)
4. Calls Flask API to get/modify data
5. Responds back in Spanish using Cartesia TTS

## Next Steps

- Try different queries in Spanish
- Test duplicate detection and merging
- Explore inconsistency detection and fixing
- Check the conversation context by referring to previous entities
