# docker/sitl/Dockerfile
# ===================================
# Docker image for SITL environment

FROM jonasvautherin/px4-gazebo-headless:latest

# Install additional dependencies
RUN apt-get update && apt-get install -y \
    curl \
    netcat \
    && rm -rf /var/lib/apt/lists/*

# Create workspace
WORKDIR /workspace

# Copy entrypoint script
COPY entrypoint.sh /workspace/entrypoint.sh
RUN chmod +x /workspace/entrypoint.sh

# Expose MAVLink ports
EXPOSE 14540/udp 14550/udp

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=5 \
    CMD nc -u -z localhost 14540 || exit 1

ENTRYPOINT ["/workspace/entrypoint.sh"]
