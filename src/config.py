"""Configuration management for ERP Voice Chat System."""

import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration."""

    # Flask Configuration
    FLASK_ENV: str = os.getenv("FLASK_ENV", "development")
    FLASK_SECRET_KEY: str = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
    FLASK_PORT: int = int(os.getenv("FLASK_PORT", "5000"))
    FLASK_BACKEND_URL: str = os.getenv("FLASK_BACKEND_URL", "http://localhost:5000")

    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_DB_URL: str = os.getenv("SUPABASE_DB_URL", "")

    # LiveKit Configuration
    LIVEKIT_URL: str = os.getenv("LIVEKIT_URL", "")
    LIVEKIT_API_KEY: str = os.getenv("LIVEKIT_API_KEY", "")
    LIVEKIT_API_SECRET: str = os.getenv("LIVEKIT_API_SECRET", "")

    # LLM Configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama3")
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")

    # Language Configuration
    VOICE_LANGUAGE: str = os.getenv("VOICE_LANGUAGE", "es")

    # STT Configuration
    STT_PROVIDER: str = os.getenv("STT_PROVIDER", "whisper")
    STT_MODEL: str = os.getenv("STT_MODEL", "base")
    STT_LANGUAGE: str = os.getenv("STT_LANGUAGE", "es")

    # TTS Configuration
    TTS_PROVIDER: str = os.getenv("TTS_PROVIDER", "piper")
    TTS_VOICE: str = os.getenv("TTS_VOICE", "es_ES-davefx-medium")
    TTS_LANGUAGE: str = os.getenv("TTS_LANGUAGE", "es")

    # Duplicate Detection Configuration
    DUPLICATE_SIMILARITY_THRESHOLD: int = int(
        os.getenv("DUPLICATE_SIMILARITY_THRESHOLD", "80")
    )

    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration values.

        Returns:
            True if all required values are present
        """
        required_fields = [
            ("SUPABASE_URL", cls.SUPABASE_URL),
            ("SUPABASE_KEY", cls.SUPABASE_KEY),
            ("LIVEKIT_URL", cls.LIVEKIT_URL),
            ("LIVEKIT_API_KEY", cls.LIVEKIT_API_KEY),
            ("LIVEKIT_API_SECRET", cls.LIVEKIT_API_SECRET),
        ]

        missing = [name for name, value in required_fields if not value]

        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")

        return True

    @classmethod
    def get_supabase_config(cls) -> tuple[str, str]:
        """Get Supabase configuration.

        Returns:
            Tuple of (url, key)
        """
        return cls.SUPABASE_URL, cls.SUPABASE_KEY

    @classmethod
    def get_livekit_config(cls) -> tuple[str, str, str]:
        """Get LiveKit configuration.

        Returns:
            Tuple of (url, api_key, api_secret)
        """
        return cls.LIVEKIT_URL, cls.LIVEKIT_API_KEY, cls.LIVEKIT_API_SECRET
