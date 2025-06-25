#!/bin/bash
echo "Updating Adminer port from 8080 to 8090..."

# Update docker-compose.yaml
sed -i 's/- "8080:8080"/- "8090:8080"/' deploy/docker/docker-compose.yaml

# Update README.md
sed -i 's/http:\/\/localhost:8080/http:\/\/localhost:8090/g' README.md

# Update test scripts
find scripts -name "*.py" -type f -exec sed -i 's/localhost:8080/localhost:8090/g' {} \;

# Update any shell scripts
find scripts -name "*.sh" -type f -exec sed -i 's/localhost:8080/localhost:8090/g' {} \;

echo "✅ Port update complete!"
