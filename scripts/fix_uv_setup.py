#!/usr/bin/env python3
"""Fix UV setup with proper pyproject.toml format."""

from pathlib import Path
import subprocess
import sys

def create_proper_pyproject():
    """Create properly formatted pyproject.toml for UV."""
    print("📝 Creating proper UV-compatible pyproject.toml...")
    
    content = '''[project]
name = "dronesphere"
version = "0.1.0"
description = "AI-powered drone control system with natural language interface"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.10"
authors = [
    {name = "Alireza Ghaderi", email = "p30planets@gmail.com"}
]

dependencies = [
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "fastapi>=0.108.0",
    "uvicorn[standard]>=0.25.0",
    "aiofiles>=23.2.1",
    "httpx>=0.25.2",
    "mavsdk>=2.0.1",
    "pymavlink>=2.4.41",
    "ollama>=0.1.7",
    "openai>=1.6.1",
    "anthropic>=0.8.1",
    "sqlalchemy>=2.0.23",
    "alembic>=1.13.1",
    "asyncpg>=0.29.0",
    "redis>=5.0.1",
    "aio-pika>=9.3.1",
    "pyyaml>=6.0.1",
    "orjson>=3.9.10",
    "loguru>=0.7.2",
    "jsonschema>=4.20.0",
    "typer>=0.9.0",
    "rich>=13.7.0",
    "prometheus-client>=0.19.0",
    "spacy>=3.7.2",
    "structlog>=24.0.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.3",
    "pytest-asyncio>=0.21.1",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.12.0",
    "black>=23.12.1",
    "ruff>=0.1.0",
    "mypy>=1.8.0",
    "bandit[toml]>=1.7.6",
    "pre-commit>=3.6.0",
    "faker>=22.0.0",
    "factory-boy>=3.3.0",
    "testcontainers>=3.7.1",
    "ipython>=8.19.0",
    "ipdb>=0.13.13",
]

docs = [
    "mkdocs>=1.5.3",
    "mkdocs-material>=9.5.3",
    "mkdocstrings[python]>=0.24.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=7.4.3",
    "pytest-asyncio>=0.21.1",
    "pytest-cov>=4.1.0",
    "black>=23.12.1",
    "ruff>=0.1.0",
    "mypy>=1.8.0",
    "pre-commit>=3.6.0",
]

[build-system]
requires = ["setuptools>=69.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
packages = ["src"]

[tool.black]
line-length = 88
target-version = ['py310', 'py311', 'py312']
include = '\.pyi?$'

[tool.ruff]
line-length = 88
target-version = "py310"
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
    "ARG", # flake8-unused-arguments
    "SIM", # flake8-simplify
]
ignore = ["E501"]  # line too long
fix = true

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
addopts = "-ra -q --strict-markers --cov=src"
asyncio_mode = "auto"

[tool.coverage.run]
source = ["src"]
omit = ["*/tests/*", "*/test_*.py"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
'''
    
    # Backup existing if it exists
    if Path("pyproject.toml").exists():
        Path("pyproject.toml.backup").write_text(Path("pyproject.toml").read_text())
    
    # Write new pyproject.toml
    Path("pyproject.toml").write_text(content)
    print("✅ Created proper pyproject.toml")


def create_setup_py():
    """Create setup.py for editable installs."""
    print("📝 Creating setup.py for compatibility...")
    
    content = '''"""Setup configuration for DroneSphere."""

from setuptools import setup, find_packages

setup(
    name="dronesphere",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
)
'''
    
    Path("setup.py").write_text(content)
    print("✅ Created setup.py")


def create_uv_lock():
    """Initialize UV and create lock file."""
    print("\n🔒 Creating UV lock file...")
    
    try:
        # Remove old lock files
        for lockfile in ["poetry.lock", "uv.lock", "requirements.txt"]:
            if Path(lockfile).exists():
                Path(lockfile).unlink()
                print(f"  Removed old {lockfile}")
        
        # Initialize UV project
        subprocess.run(["uv", "sync"], check=True)
        print("✅ UV lock file created")
        
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Warning: Could not create lock file: {e}")
        print("   You may need to run 'uv sync' manually")


def setup_venv():
    """Set up virtual environment with UV."""
    print("\n🐍 Setting up virtual environment...")
    
    # Remove old venv if exists
    if Path("venv").exists():
        print("  Removing old venv...")
        import shutil
        shutil.rmtree("venv", ignore_errors=True)
    
    if Path(".venv").exists():
        print("  Removing old .venv...")
        import shutil
        shutil.rmtree(".venv", ignore_errors=True)
    
    # Create new venv
    subprocess.run(["uv", "venv"], check=True)
    print("✅ Virtual environment created")


def install_dependencies():
    """Install all dependencies with UV."""
    print("\n📦 Installing dependencies...")
    
    # Install main dependencies
    subprocess.run(["uv", "pip", "install", "-e", "."], check=True)
    
    # Install dev dependencies
    subprocess.run(["uv", "pip", "install", "-e", ".[dev]"], check=True)
    
    print("✅ Dependencies installed")


def download_spacy_model():
    """Download spaCy language model."""
    print("\n🤖 Downloading spaCy language model...")
    
    try:
        subprocess.run([
            sys.executable, "-m", "spacy", "download", "en_core_web_sm"
        ], check=True)
        print("✅ spaCy model downloaded")
    except subprocess.CalledProcessError:
        print("⚠️  Could not download spaCy model. Run manually:")
        print("   python -m spacy download en_core_web_sm")


def verify_installation():
    """Verify everything is working."""
    print("\n🔍 Verifying installation...")
    
    # Test imports
    test_script = '''
import sys
print(f"Python: {sys.version}")

try:
    import fastapi
    print("✅ FastAPI imported")
except ImportError as e:
    print(f"❌ FastAPI import failed: {e}")

try:
    import spacy
    print("✅ spaCy imported")
except ImportError as e:
    print(f"❌ spaCy import failed: {e}")

try:
    from src.core.domain.entities.drone import Drone
    print("✅ Domain models imported")
except ImportError as e:
    print(f"❌ Domain import failed: {e}")

print("\\n✅ Basic imports working!")
'''
    
    Path("test_imports_temp.py").write_text(test_script)
    subprocess.run([sys.executable, "test_imports_temp.py"])
    Path("test_imports_temp.py").unlink()


def update_gitignore():
    """Update .gitignore for UV."""
    print("\n📝 Updating .gitignore...")
    
    gitignore_additions = """
# UV
.venv/
uv.lock
.python-version

# Old package managers
poetry.lock
Pipfile
Pipfile.lock
"""
    
    current = Path(".gitignore").read_text() if Path(".gitignore").exists() else ""
    
    if "uv.lock" not in current:
        Path(".gitignore").write_text(current + gitignore_additions)
        print("✅ Updated .gitignore")


def create_env_template():
    """Create .env.template file."""
    print("\n📝 Creating .env.template...")
    
    env_template = '''# DroneSphere Environment Configuration

# Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_PREFIX=/api/v1

# Database
DATABASE_URL=postgresql+asyncpg://dronesphere:dronesphere@localhost:5432/dronesphere

# Redis
REDIS_URL=redis://localhost:6379/0

# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@localhost:5672/

# LLM Configuration
LLM_PROVIDER=ollama  # ollama, openai, anthropic
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
OPENAI_API_KEY=your-api-key-here
ANTHROPIC_API_KEY=your-api-key-here

# Drone Configuration (Server)
DRONE_CONNECTION_TIMEOUT=30
DRONE_HEARTBEAT_INTERVAL=1

# Drone Controller (Raspberry Pi)
MAVSDK_SERVER_ADDRESS=localhost
MAVSDK_SERVER_PORT=50051
PIXHAWK_CONNECTION=serial:///dev/ttyACM0:921600
SERVER_WEBSOCKET_URL=ws://your-server:8000/ws

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
'''
    
    Path(".env.template").write_text(env_template)
    print("✅ Created .env.template")


def main():
    """Run complete UV setup fix."""
    print("🚀 Fixing UV Setup for DroneSphere\n")
    
    # Check UV is installed
    try:
        subprocess.run(["uv", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ UV not installed. Install with:")
        print("   curl -LsSf https://astral.sh/uv/install.sh | sh")
        return 1
    
    # Run fixes
    create_proper_pyproject()
    create_setup_py()
    update_gitignore()
    create_env_template()
    
    # Set up environment
    print("\n🔧 Setting up UV environment...")
    setup_venv()
    
    # Install in venv
    print("\n📦 Installing in virtual environment...")
    subprocess.run([".venv/bin/python", "-m", "pip", "install", "-e", ".[dev]"], 
                   shell=True, check=True)
    
    # Download spaCy model
    subprocess.run([".venv/bin/python", "-m", "spacy", "download", "en_core_web_sm"], 
                   shell=True, check=True)
    
    print("\n✅ UV setup complete!")
    print("\n📝 Next steps:")
    print("  1. Activate environment: source .venv/bin/activate")
    print("  2. Copy .env.template to .env and configure")
    print("  3. Run domain tests: python scripts/test_domain_models.py")
    print("  4. Start Step 4: NLP implementation")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())