#!/bin/bash
# Script to fix git push issues with large files

echo "🔧 Fixing Git Push Issues"
echo "========================="

# Remove large files from git tracking
echo "Removing large files from git..."

# Remove prometheus files
git rm --cached prometheus-3.5.0.darwin-arm64.tar.gz 2>/dev/null || true
git rm --cached -r prometheus-3.5.0.darwin-arm64/ 2>/dev/null || true

# Remove node_modules cache
git rm --cached -r frontend/node_modules/.cache/ 2>/dev/null || true

# Add to gitignore
echo "Adding to .gitignore..."
cat >> .gitignore << 'EOF'

# Large files to ignore
prometheus-*.tar.gz
prometheus-*/
frontend/node_modules/.cache/
*.pack
EOF

echo "✅ Large files removed from git tracking"
echo "✅ Added entries to .gitignore"

echo ""
echo "Now you can commit and push:"
echo "  git add .gitignore"
echo "  git commit -m 'Remove large files and update gitignore'"
echo "  git push origin main"