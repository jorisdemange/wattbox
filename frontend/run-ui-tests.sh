#!/bin/bash

# Create screenshots directory if it doesn't exist
mkdir -p screenshots

# Install Playwright if not already installed
if ! command -v playwright &> /dev/null; then
    echo "Installing Playwright..."
    npm install -D @playwright/test
    npx playwright install
fi

# Clear previous screenshots
rm -f screenshots/*.png

echo "🚀 Starting WattBox UI Tests..."
echo "================================"

# Run the tests
npx playwright test wattbox-ui-test.spec.ts --project=chromium

# Generate HTML report
npx playwright show-report

echo "================================"
echo "✅ Tests completed!"
echo "📸 Screenshots saved in: ./screenshots/"
echo "📊 HTML report opened in browser"