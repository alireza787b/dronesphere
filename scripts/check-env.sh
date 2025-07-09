#!/bin/bash
# Check DroneSphere Environment Status
# ===================================

echo "🔍 DroneSphere Environment Status"
echo "=================================="
echo ""

# Check agent environment
echo "📱 Agent Environment:"
if [ -d "dronesphere/agent/.venv" ]; then
    echo "  ✅ Virtual environment exists"
    echo "  📦 Location: dronesphere/agent/.venv"
    cd dronesphere/agent
    if source .venv/bin/activate 2>/dev/null && python -c "import dronesphere.agent.main" 2>/dev/null; then
        echo "  ✅ Imports working"
        python -c "
import pkg_resources
pkgs = [d for d in pkg_resources.working_set if d.project_name in ['fastapi', 'mavsdk', 'uvicorn']]
for pkg in pkgs: print(f'    {pkg.project_name}: {pkg.version}')
" 2>/dev/null || echo "  📦 Dependencies installed"
    else
        echo "  ⚠️  Import issues detected"
    fi
    deactivate 2>/dev/null || true
    cd ../..
else
    echo "  ❌ Virtual environment missing"
fi

echo ""

# Check server environment
echo "🖥️  Server Environment:"
if [ -d "dronesphere/server/.venv" ]; then
    echo "  ✅ Virtual environment exists"
    echo "  📦 Location: dronesphere/server/.venv"
    cd dronesphere/server
    if source .venv/bin/activate 2>/dev/null && python -c "import dronesphere.server.main" 2>/dev/null; then
        echo "  ✅ Imports working"
        python -c "
import pkg_resources
pkgs = [d for d in pkg_resources.working_set if d.project_name in ['fastapi', 'mavsdk', 'uvicorn', 'prometheus-client']]
for pkg in pkgs: print(f'    {pkg.project_name}: {pkg.version}')
" 2>/dev/null || echo "  📦 Dependencies installed"
    else
        echo "  ⚠️  Import issues detected"
    fi
    deactivate 2>/dev/null || true
    cd ../..
else
    echo "  ❌ Virtual environment missing"
fi

echo ""
echo "💾 Environment sizes:"
du -sh dronesphere/agent/.venv 2>/dev/null | sed 's/^/  Agent:  /' || echo "  Agent:  Not found"
du -sh dronesphere/server/.venv 2>/dev/null | sed 's/^/  Server: /' || echo "  Server: Not found"
