#!/bin/bash

echo "🚀 Starting Auto-Push to GitHub..."

git add .

git commit -m "Auto-push: $(date '+%Y-%m-%d %H:%M:%S')" || true

if git push origin main; then
    echo "✅ Project successfully pushed to GitHub!"
else
    echo "❌ Push failed!"
fi