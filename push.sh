#!/bin/bash
echo "🚀 Starting Auto-Push to GitHub..."

# In das Projektverzeichnis wechseln
cd /mnt/c/Users/DreadLappy/source/repos/SkatePlace || exit 1

git add .
git commit -m "Auto-push: $(date '+%Y-%m-%d %H:%M:%S')"
git push origin main

echo "✅ Project successfully pushed to GitHub!"
