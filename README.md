<a href="https://livekit.io/">
  <img src="./.github/assets/livekit-mark.png" alt="LiveKit logo" width="100" height="100">
</a>

# ERP Voice Chat System 🎙️

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![LiveKit](https://img.shields.io/badge/LiveKit-Agents-00ADD8)](https://livekit.io/)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A voice-enabled chat interface for Enterprise Resource Planning (ERP) systems built with [LiveKit Agents for Python](https://github.com/livekit/agents), Flask, and Supabase. This system enables administrators to interact with ERP data through natural voice conversations in **Spanish**, with capabilities to detect, report, and resolve duplicated data and inconsistencies.

Built for the **FailFast Hackathon** 🚀

## 🎥 Demo

[Add your demo video or GIF here]

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Quick Start](#quick-start)
- [Database Management](#database-management)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Features

- **🗣️ Voice-First Interface**: Natural voice conversations in Spanish using free, local models
- **🔍 Duplicate Detection**: Automatically identify and merge duplicate records using Levenshtein distance
- **⚠️ Inconsistency Analysis**: Detect and fix data quality issues (referential integrity, calculations, formats, business rules)
- **💰 100% Free Stack**: Uses Ollama (Llama 3), Deepgram STT, and Cartesia TTS - all free tiers
- **🔌 REST API**: Flask backend with comprehensive API for data operations
- **⚡ Real-time Voice**: LiveKit Agents for low-latency voice interaction
- **✅ Property-Based Testing**: Comprehensive test suite with Hypothesis for correctness guarantees

## Architecture

The system consists of three main layers:

- **Voice Layer**: LiveKit Agent handling real-time audio streaming and conversation management
- **Business Logic Layer**: Flask backend with duplicate detection and inconsistency analysis engines
- **Data Layer**: Supabase (PostgreSQL) for ERP data and data quality tracking

## Project Structure

```
src/
├── agent.py              # LiveKit voice agent (main entry point)
├── api/                  # Flask REST API
│   ├── __init__.py
│   └── app.py           # Flask application setup
├── services/            # Business logic services
│   └── __init__.py
├── models/              # Data models
│   └── __init__.py
├── repositories/        # Data access layer
│   └── __init__.py
└── config.py           # Configuration management

.kiro/specs/erp-voice-chat/  # Feature specification
├── requirements.md      # Requirements document
├── design.md           # Design document
└── tasks.md            # Implementation tasks

tests/                  # Test suite
└── test_agent.py

SETUP.md               # Detailed setup instructions
```

## 🚀 Quick Start

See [QUICK_START.md](QUICK_START.md) for a quick guide or [SETUP.md](SETUP.md) for detailed installation instructions.

### Example Voice Commands (in Spanish)

```
🗣️ "Muéstrame todos los clientes"
   → Shows all customers in the database

🗣️ "Detecta duplicados en la tabla de clientes"
   → Identifies duplicate customer records

🗣️ "Busca inconsistencias en los pedidos"
   → Finds data quality issues in orders

🗣️ "Combina los duplicados del primer grupo"
   → Merges duplicate records

🗣️ "Corrige la inconsistencia de cálculo"
   → Fixes calculation errors
```

### 1. Install Dependencies

```bash
uv sync
```

### 2. Install Ollama and Pull Llama 3

```bash
# Install Ollama (see SETUP.md for platform-specific instructions)
ollama pull llama3
```

### 3. Configure Environment

```bash
cp .env.example .env.local
# Edit .env.local with your LiveKit and Supabase credentials
```

### 4. Run the Application

Start the Flask backend:
```bash
uv run python -m src.api.app
```

Start the LiveKit agent:
```bash
uv run python src/agent.py dev
```

## Technology Stack

### Backend
- **Python 3.11+**: Primary programming language
- **Flask 3.x**: Web framework for REST APIs
- **Supabase**: PostgreSQL database service
- **Hypothesis**: Property-based testing framework

### Voice AI Stack (100% Free)
- **LiveKit Agents**: Voice AI framework
- **Ollama + Llama 3.1 (8B)**: Free, local LLM with function calling support
- **Deepgram Nova-2**: Free tier speech-to-text (Spanish)
- **Cartesia**: Free tier text-to-speech (Spanish voices)

### Data Quality
- **Levenshtein Distance**: Fuzzy string matching for duplicate detection
- **Custom Analyzers**: Referential integrity, calculation validation, format checking

## Database Management

The project includes scripts for managing sample ERP data with intentional duplicates and inconsistencies for testing.

### Seed Sample Data

Create sample data including customers, products, orders, and order items:
```bash
uv run python scripts/seed_sample_data.py
```

### Reset Database

Clear all data from ERP and data quality tables:
```bash
uv run python scripts/reset_database.py
```

### Reset and Seed (Recommended)

Clear all data and seed fresh sample data in one command:
```bash
uv run python scripts/reset_and_seed.py --confirm
```

See [scripts/README.md](scripts/README.md) for detailed documentation on the sample data structure and testing scenarios.

## Development

This project uses the `uv` package manager and follows test-driven development practices.

Run tests:
```bash
uv run pytest
```

Format code:
```bash
uv run ruff format
uv run ruff check
```

## Coding agents and MCP

This project is designed to work with coding agents like [Cursor](https://www.cursor.com/) and [Claude Code](https://www.anthropic.com/claude-code). 

To get the most out of these tools, install the [LiveKit Docs MCP server](https://docs.livekit.io/mcp).

For Cursor, use this link:

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en-US/install-mcp?name=livekit-docs&config=eyJ1cmwiOiJodHRwczovL2RvY3MubGl2ZWtpdC5pby9tY3AifQ%3D%3D)

For Claude Code, run this command:

```
claude mcp add --transport http livekit-docs https://docs.livekit.io/mcp
```

For Codex CLI, use this command to install the server:
```
codex mcp add --url https://docs.livekit.io/mcp livekit-docs
```

For Gemini CLI, use this command to install the server:
```
gemini mcp add --transport http livekit-docs https://docs.livekit.io/mcp
```

The project includes a complete [AGENTS.md](AGENTS.md) file for these assistants. You can modify this file  your needs. To learn more about this file, see [https://agents.md](https://agents.md).

## Dev Setup

Clone the repository and install dependencies to a virtual environment:

```console
cd agent-starter-python
uv sync
```

Sign up for [LiveKit Cloud](https://cloud.livekit.io/) then set up the environment by copying `.env.example` to `.env.local` and filling in the required keys:

- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`

You can load the LiveKit environment automatically using the [LiveKit CLI](https://docs.livekit.io/home/cli/cli-setup):

```bash
lk cloud auth
lk app env -w -d .env.local
```

## Run the agent

Before your first run, you must download certain models such as [Silero VAD](https://docs.livekit.io/agents/build/turns/vad/) and the [LiveKit turn detector](https://docs.livekit.io/agents/build/turns/turn-detector/):

```console
uv run python src/agent.py download-files
```

Next, run this command to speak to your agent directly in your terminal:

```console
uv run python src/agent.py console
```

To run the agent for use with a frontend or telephony, use the `dev` command:

```console
uv run python src/agent.py dev
```

In production, use the `start` command:

```console
uv run python src/agent.py start
```

## Frontend & Telephony

Get started quickly with our pre-built frontend starter apps, or add telephony support:

| Platform | Link | Description |
|----------|----------|-------------|
| **Web** | [`livekit-examples/agent-starter-react`](https://github.com/livekit-examples/agent-starter-react) | Web voice AI assistant with React & Next.js |
| **iOS/macOS** | [`livekit-examples/agent-starter-swift`](https://github.com/livekit-examples/agent-starter-swift) | Native iOS, macOS, and visionOS voice AI assistant |
| **Flutter** | [`livekit-examples/agent-starter-flutter`](https://github.com/livekit-examples/agent-starter-flutter) | Cross-platform voice AI assistant app |
| **React Native** | [`livekit-examples/voice-assistant-react-native`](https://github.com/livekit-examples/voice-assistant-react-native) | Native mobile app with React Native & Expo |
| **Android** | [`livekit-examples/agent-starter-android`](https://github.com/livekit-examples/agent-starter-android) | Native Android app with Kotlin & Jetpack Compose |
| **Web Embed** | [`livekit-examples/agent-starter-embed`](https://github.com/livekit-examples/agent-starter-embed) | Voice AI widget for any website |
| **Telephony** | [📚 Documentation](https://docs.livekit.io/agents/start/telephony/) | Add inbound or outbound calling to your agent |

For advanced customization, see the [complete frontend guide](https://docs.livekit.io/agents/start/frontend/).

## Tests and evals

This project includes a complete suite of evals, based on the LiveKit Agents [testing & evaluation framework](https://docs.livekit.io/agents/build/testing/). To run them, use `pytest`.

```console
uv run pytest
```

## Using this template repo for your own project

Once you've started your own project based on this repo, you should:

1. **Check in your `uv.lock`**: This file is currently untracked for the template, but you should commit it to your repository for reproducible builds and proper configuration management. (The same applies to `livekit.toml`, if you run your agents in LiveKit Cloud)

2. **Remove the git tracking test**: Delete the "Check files not tracked in git" step from `.github/workflows/tests.yml` since you'll now want this file to be tracked. These are just there for development purposes in the template repo itself.

3. **Add your own repository secrets**: You must [add secrets](https://docs.github.com/en/actions/how-tos/writing-workflows/choosing-what-your-workflow-does/using-secrets-in-github-actions) for `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET` so that the tests can run in CI.

## Deploying to production

This project is production-ready and includes a working `Dockerfile`. To deploy it to LiveKit Cloud or another environment, see the [deploying to production](https://docs.livekit.io/agents/ops/deployment/) guide.

## Self-hosted LiveKit

You can also self-host LiveKit instead of using LiveKit Cloud. See the [self-hosting](https://docs.livekit.io/home/self-hosting/) guide for more information. If you choose to self-host, you'll need to also use [model plugins](https://docs.livekit.io/agents/models/#plugins) instead of LiveKit Inference and will need to remove the [LiveKit Cloud noise cancellation](https://docs.livekit.io/home/cloud/noise-cancellation/) plugin.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
