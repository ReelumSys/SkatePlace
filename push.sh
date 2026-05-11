#!/bin/bash
# SkatePlace Auto-Push Script

echo "🚀 Starting Auto-Push to GitHub..."

# 1. Add all changes
git add .

# 2. Commit with a timestamped message
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
git commit -m "Auto-save: $TIMESTAMP"

# 3. Push to main
git push origin main

echo "✅ Project successfully pushed to GitHub!"
