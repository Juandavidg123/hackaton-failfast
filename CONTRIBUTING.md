# Contributing to ERP Voice Chat System

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/Juandavidg123/hackaton-failfast.git`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Run tests: `uv run pytest`
6. Commit your changes: `git commit -m "Add your feature"`
7. Push to your fork: `git push origin feature/your-feature-name`
8. Create a Pull Request

## Development Setup

See [SETUP.md](SETUP.md) for detailed setup instructions.

### Quick Setup

```bash
# Install dependencies
uv sync

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# - Get LiveKit credentials from https://cloud.livekit.io
# - Get Supabase credentials from https://supabase.com
# - Get Deepgram API key from https://console.deepgram.com/signup
# - Get Cartesia API key from https://cartesia.ai

# Install Ollama and pull Llama 3
ollama pull llama3

# Run database migrations
uv run python scripts/apply_migrations.py

# Seed sample data
uv run python scripts/reset_and_seed.py --confirm

# Run tests
uv run pytest
```

## Code Style

This project uses:
- **Ruff** for linting and formatting
- **Type hints** for all function signatures
- **Docstrings** for all public functions and classes

Format your code before committing:
```bash
uv run ruff format
uv run ruff check --fix
```

## Testing

All new features must include tests:
- **Unit tests** for individual functions
- **Property-based tests** for correctness properties (using Hypothesis)
- **Integration tests** for API endpoints

Run tests:
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_duplicate_detection.py

# Run with coverage
uv run pytest --cov=src --cov-report=html
```

## Commit Messages

Use clear, descriptive commit messages:
- `feat: Add duplicate detection for products`
- `fix: Correct calculation inconsistency detection`
- `docs: Update API documentation`
- `test: Add property tests for merge operations`
- `refactor: Simplify error handling logic`

## Pull Request Guidelines

1. **Description**: Clearly describe what your PR does and why
2. **Tests**: Include tests for new functionality
3. **Documentation**: Update relevant documentation
4. **Breaking Changes**: Clearly mark any breaking changes
5. **Screenshots**: Include screenshots for UI changes

## Project Structure

```
src/
├── agent.py              # LiveKit voice agent
├── api/                  # Flask REST API
├── services/            # Business logic
├── models/              # Data models
├── repositories/        # Data access layer
└── config.py           # Configuration

tests/                   # Test suite
├── test_agent.py
├── test_duplicate_detection.py
└── ...

.kiro/specs/            # Feature specifications
└── erp-voice-chat/
    ├── requirements.md
    ├── design.md
    └── tasks.md
```

## Questions?

Open an issue or reach out to the maintainers.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
