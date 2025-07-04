# scripts/lint.sh
# ===================================
#!/bin/bash

# Code linting and formatting script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default values
FIX=false
CHECK_ONLY=false

show_help() {
    cat << EOF
DroneSphere Code Linter

Usage: $0 [OPTIONS]

Options:
    --fix           Auto-fix issues where possible
    --check         Check only (no fixes)
    -h, --help      Show this help message

This script runs:
  • black (code formatting)
  • ruff (linting)
  • mypy (type checking)
  • isort (import sorting)

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --fix)
            FIX=true
            shift
            ;;
        --check)
            CHECK_ONLY=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

echo -e "${BLUE}🔍 DroneSphere Code Linter${NC}"
echo "========================="
echo "Fix mode: $FIX"
echo "Check only: $CHECK_ONLY"
echo "========================="

cd "$PROJECT_DIR"

# Activate virtual environment
if [[ -f .venv/bin/activate ]]; then
    source .venv/bin/activate
elif [[ -f .venv/Scripts/activate ]]; then
    source .venv/Scripts/activate
fi

FAILED=false

# Run black
echo -e "${YELLOW}🎨 Running black (code formatting)...${NC}"
if [[ "$CHECK_ONLY" == "true" ]]; then
    if ! black --check --diff dronesphere/ tests/; then
        FAILED=true
    fi
elif [[ "$FIX" == "true" ]]; then
    black dronesphere/ tests/
else
    if ! black --check dronesphere/ tests/; then
        echo -e "${YELLOW}💡 Run with --fix to auto-format code${NC}"
        FAILED=true
    fi
fi

# Run isort
echo -e "${YELLOW}📦 Running isort (import sorting)...${NC}"
if [[ "$CHECK_ONLY" == "true" ]]; then
    if ! isort --check-only --diff dronesphere/ tests/; then
        FAILED=true
    fi
elif [[ "$FIX" == "true" ]]; then
    isort dronesphere/ tests/
else
    if ! isort --check-only dronesphere/ tests/; then
        echo -e "${YELLOW}💡 Run with --fix to auto-sort imports${NC}"
        FAILED=true
    fi
fi

# Run ruff
echo -e "${YELLOW}🔧 Running ruff (linting)...${NC}"
if [[ "$FIX" == "true" ]]; then
    ruff check --fix dronesphere/ tests/
else
    if ! ruff check dronesphere/ tests/; then
        if [[ "$CHECK_ONLY" != "true" ]]; then
            echo -e "${YELLOW}💡 Run with --fix to auto-fix some issues${NC}"
        fi
        FAILED=true
    fi
fi

# Run mypy
echo -e "${YELLOW}🔍 Running mypy (type checking)...${NC}"
if ! mypy dronesphere/; then
    FAILED=true
fi

# Summary
echo ""
if [[ "$FAILED" == "true" ]]; then
    echo -e "${RED}❌ Linting failed!${NC}"
    echo ""
    echo "Fix issues manually or run:"
    echo "  $0 --fix"
    exit 1
else
    echo -e "${GREEN}✅ All checks passed!${NC}"
fi

# ===================================

# scripts/build.sh
# ===================================
#!/bin/bash

# Build script for Docker images

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default values
VERSION="latest"
PUSH=false
REGISTRY=""
PLATFORM="linux/amd64"

show_help() {
    cat << EOF
DroneSphere Docker Build Script

Usage: $0 [OPTIONS]

Options:
    -v, --version VERSION   Image version tag (default: latest)
    -p, --push             Push images to registry
    -r, --registry REG     Container registry URL
    --platform PLATFORM   Target platform (default: linux/amd64)
    -h, --help             Show this help message

Examples:
    $0                                    # Build latest images
    $0 -v 1.0.0                         # Build version 1.0.0
    $0 -v 1.0.0 -p -r ghcr.io/user     # Build and push to GitHub registry
    $0 --platform linux/arm64          # Build for ARM64

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        -p|--push)
            PUSH=true
            shift
            ;;
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        --platform)
            PLATFORM="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

echo -e "${BLUE}🐳 DroneSphere Docker Build${NC}"
echo "==========================="
echo "Version: $VERSION"
echo "Platform: $PLATFORM"
echo "Push: $PUSH"
if [[ -n "$REGISTRY" ]]; then
    echo "Registry: $REGISTRY"
fi
echo "==========================="

cd "$PROJECT_DIR"

# Image names
if [[ -n "$REGISTRY" ]]; then
    IMAGE_PREFIX="$REGISTRY/dronesphere"
else
    IMAGE_PREFIX="dronesphere"
fi

IMAGES=(
    "server"
    "agent"
)

# Build images
for image in "${IMAGES[@]}"; do
    echo -e "${YELLOW}🔨 Building $image image...${NC}"
    
    full_name="$IMAGE_PREFIX/$image:$VERSION"
    
    docker build \
        --platform "$PLATFORM" \
        -f "docker/Dockerfile.$image" \
        -t "$full_name" \
        .
    
    # Also tag as latest if not already latest
    if [[ "$VERSION" != "latest" ]]; then
        docker tag "$full_name" "$IMAGE_PREFIX/$image:latest"
    fi
    
    echo -e "${GREEN}✅ Built $full_name${NC}"
done

# Build main image (server + agent)
echo -e "${YELLOW}🔨 Building main image...${NC}"
docker build \
    --platform "$PLATFORM" \
    -f "docker/Dockerfile" \
    -t "$IMAGE_PREFIX:$VERSION" \
    .

if [[ "$VERSION" != "latest" ]]; then
    docker tag "$IMAGE_PREFIX:$VERSION" "$IMAGE_PREFIX:latest"
fi

echo -e "${GREEN}✅ Built $IMAGE_PREFIX:$VERSION${NC}"

# Push images if requested
if [[ "$PUSH" == "true" ]]; then
    if [[ -z "$REGISTRY" ]]; then
        echo -e "${RED}❌ Cannot push without registry specified${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}📤 Pushing images...${NC}"
    
    # Push individual images
    for image in "${IMAGES[@]}"; do
        echo "Pushing $IMAGE_PREFIX/$image:$VERSION"
        docker push "$IMAGE_PREFIX/$image:$VERSION"
        
        if [[ "$VERSION" != "latest" ]]; then
            docker push "$IMAGE_PREFIX/$image:latest"
        fi
    done
    
    # Push main image
    echo "Pushing $IMAGE_PREFIX:$VERSION"
    docker push "$IMAGE_PREFIX:$VERSION"
    
    if [[ "$VERSION" != "latest" ]]; then
        docker push "$IMAGE_PREFIX:latest"
    fi
    
    echo -e "${GREEN}✅ Images pushed successfully${NC}"
fi

# List built images
echo ""
echo -e "${BLUE}📋 Built images:${NC}"
docker images | grep dronesphere | head -10

echo ""
echo -e "${GREEN}🎉 Build complete!${NC}"

# ===================================

# .github/workflows/ci.yml
# ===================================

name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  PYTHON_VERSION: "3.10"

jobs:
  lint:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Install uv
      uses: astral-sh/setup-uv@v2
      with:
        version: "latest"
    
    - name: Set up Python
      run: uv python install ${{ env.PYTHON_VERSION }}
    
    - name: Install dependencies
      run: |
        uv sync --all-extras
    
    - name: Run linting
      run: |
        uv run ruff check dronesphere/ tests/
        uv run black --check dronesphere/ tests/
        uv run isort --check-only dronesphere/ tests/
        uv run mypy dronesphere/

  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Install uv
      uses: astral-sh/setup-uv@v2
      with:
        version: "latest"
    
    - name: Set up Python ${{ matrix.python-version }}
      run: uv python install ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        uv sync --all-extras
    
    - name: Run unit tests
      run: |
        uv run pytest tests/unit/ -v --cov=dronesphere --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella

  integration-tests:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Install uv
      uses: astral-sh/setup-uv@v2
      with:
        version: "latest"
    
    - name: Set up Python
      run: uv python install ${{ env.PYTHON_VERSION }}
    
    - name: Install dependencies
      run: |
        uv sync --all-extras
    
    - name: Start SITL environment
      run: |
        docker-compose up -d sitl mavlink2rest
        
        # Wait for SITL to be ready
        timeout 120 bash -c 'until curl -f http://localhost:8080/mavlink/vehicles; do sleep 5; done'
    
    - name: Run integration tests
      run: |
        uv run pytest tests/integration/ -v -m "not sitl"
    
    - name: Run SITL tests
      run: |
        uv run pytest tests/integration/sitl/ -v -m sitl
    
    - name: Stop SITL environment
      run: |
        docker-compose down -v

  build:
    runs-on: ubuntu-latest
    needs: [lint, test]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
    
    - name: Build server image
      uses: docker/build-push-action@v5
      with:
        context: .
        file: ./docker/Dockerfile.server
        push: false
        tags: dronesphere/server:test
        cache-from: type=gha
        cache-to: type=gha,mode=max
    
    - name: Build agent image
      uses: docker/build-push-action@v5
      with:
        context: .
        file: ./docker/Dockerfile.agent
        push: false
        tags: dronesphere/agent:test
        cache-from: type=gha
        cache-to: type=gha,mode=max
    
    - name: Test Docker images
      run: |
        # Test server image
        docker run --rm dronesphere/server:test python -c "import dronesphere; print('Server image OK')"
        
        # Test agent image
        docker run --rm dronesphere/agent:test python -c "import dronesphere; print('Agent image OK')"

  security:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'
    
    - name: Upload Trivy scan results to GitHub Security tab
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: 'trivy-results.sarif'

# ===================================

# .github/workflows/release.yml
# ===================================

name: Release

on:
  push:
    tags:
      - 'v*'

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      packages: write
    
    steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0
    
    - name: Install uv
      uses: astral-sh/setup-uv@v2
      with:
        version: "latest"
    
    - name: Set up Python
      run: uv python install 3.10
    
    - name: Install dependencies
      run: |
        uv sync --all-extras
    
    - name: Run tests
      run: |
        uv run pytest tests/unit/ -v
    
    - name: Get version from tag
      id: get_version
      run: echo "VERSION=${GITHUB_REF#refs/tags/v}" >> $GITHUB_OUTPUT
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
    
    - name: Log in to Container Registry
      uses: docker/login-action@v3
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=semver,pattern={{version}}
          type=semver,pattern={{major}}.{{minor}}
    
    - name: Build and push server image
      uses: docker/build-push-action@v5
      with:
        context: .
        file: ./docker/Dockerfile.server
        push: true
        tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/server:${{ steps.get_version.outputs.VERSION }},${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/server:latest
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
    
    - name: Build and push agent image
      uses: docker/build-push-action@v5
      with:
        context: .
        file: ./docker/Dockerfile.agent
        push: true
        tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/agent:${{ steps.get_version.outputs.VERSION }},${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/agent:latest
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
    
    - name: Build documentation
      run: |
        uv run mkdocs build
    
    - name: Deploy documentation
      uses: peaceiris/actions-gh-pages@v3
      with:
        github_token: ${{ secrets.GITHUB_TOKEN }}
        publish_dir: ./site
    
    - name: Generate changelog
      id: changelog
      run: |
        # Simple changelog generation (you might want to use a more sophisticated tool)
        echo "CHANGELOG<<EOF" >> $GITHUB_OUTPUT
        echo "## Changes" >> $GITHUB_OUTPUT
        git log --pretty=format:"- %s" $(git describe --tags --abbrev=0 HEAD~1)..HEAD >> $GITHUB_OUTPUT
        echo "EOF" >> $GITHUB_OUTPUT
    
    - name: Create GitHub Release
      uses: actions/create-release@v1
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      with:
        tag_name: ${{ github.ref }}
        release_name: Release ${{ steps.get_version.outputs.VERSION }}
        body: |
          ## DroneSphere v${{ steps.get_version.outputs.VERSION }}
          
          ${{ steps.changelog.outputs.CHANGELOG }}
          
          ## Docker Images
          
          - `${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/server:${{ steps.get_version.outputs.VERSION }}`
          - `${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/agent:${{ steps.get_version.outputs.VERSION }}`
          
          ## Installation
          
          ```bash
          # Using Docker Compose
          curl -sSL https://raw.githubusercontent.com/${{ github.repository }}/v${{ steps.get_version.outputs.VERSION }}/docker-compose.prod.yml -o docker-compose.yml
          docker-compose up -d
          
          # Using Python
          pip install git+https://github.com/${{ github.repository }}.git@v${{ steps.get_version.outputs.VERSION }}
          ```
        draft: false
        prerelease: false

