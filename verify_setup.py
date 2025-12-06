#!/usr/bin/env python3
"""Verify that the ERP Voice Chat System setup is complete."""

import sys
import os
from pathlib import Path


def check_file_exists(filepath: str, description: str) -> bool:
    """Check if a file exists."""
    if Path(filepath).exists():
        print(f"✓ {description}: {filepath}")
        return True
    else:
        print(f"✗ {description} missing: {filepath}")
        return False


def check_directory_exists(dirpath: str, description: str) -> bool:
    """Check if a directory exists."""
    if Path(dirpath).is_dir():
        print(f"✓ {description}: {dirpath}")
        return True
    else:
        print(f"✗ {description} missing: {dirpath}")
        return False


def check_env_file() -> bool:
    """Check if .env.local exists."""
    if Path(".env.local").exists():
        print("✓ Environment file exists: .env.local")
        return True
    else:
        print("✗ Environment file missing: .env.local")
        print("  Run: cp .env.example .env.local")
        return False


def main():
    """Run all verification checks."""
    print("ERP Voice Chat System - Setup Verification\n")
    print("=" * 50)
    
    checks = []
    
    # Check project structure
    print("\n1. Project Structure:")
    checks.append(check_directory_exists("src/api", "Flask API directory"))
    checks.append(check_directory_exists("src/services", "Services directory"))
    checks.append(check_directory_exists("src/models", "Models directory"))
    checks.append(check_directory_exists("src/repositories", "Repositories directory"))
    
    # Check configuration files
    print("\n2. Configuration Files:")
    checks.append(check_file_exists("pyproject.toml", "Project configuration"))
    checks.append(check_file_exists(".env.example", "Environment template"))
    checks.append(check_file_exists("src/config.py", "Config module"))
    checks.append(check_env_file())
    
    # Check documentation
    print("\n3. Documentation:")
    checks.append(check_file_exists("SETUP.md", "Setup guide"))
    checks.append(check_file_exists("README.md", "README"))
    checks.append(check_file_exists(".kiro/specs/erp-voice-chat/requirements.md", "Requirements"))
    checks.append(check_file_exists(".kiro/specs/erp-voice-chat/design.md", "Design"))
    checks.append(check_file_exists(".kiro/specs/erp-voice-chat/tasks.md", "Tasks"))
    
    # Check main application files
    print("\n4. Application Files:")
    checks.append(check_file_exists("src/agent.py", "LiveKit agent"))
    checks.append(check_file_exists("src/api/app.py", "Flask application"))
    
    # Summary
    print("\n" + "=" * 50)
    passed = sum(checks)
    total = len(checks)
    print(f"\nVerification Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n✓ Setup verification complete! All checks passed.")
        print("\nNext steps:")
        print("1. Install dependencies: uv sync")
        print("2. Install Ollama and pull Llama 3: ollama pull llama3")
        print("3. Configure .env.local with your credentials")
        print("4. Run the Flask backend: uv run python -m src.api.app")
        print("5. Run the LiveKit agent: uv run python src/agent.py dev")
        return 0
    else:
        print(f"\n✗ Setup incomplete. {total - passed} checks failed.")
        print("Please review the errors above and complete the setup.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
