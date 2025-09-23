#!/bin/bash
# Simple onboarding wrapper that accepts auth key as argument

if [ -z "$1" ]; then
    echo "❌ Usage: $0 <tailscale-auth-key>"
    echo ""
    echo "🔑 Generate a new auth key at: https://login.tailscale.com/admin/settings/keys"
    echo "   Example: tskey-auth-kPG8GC23ct11CNTRL-7YYCnDFbHS5wugRzh4VwS5EUdmYbHKUP"
    echo ""
    echo "📋 Usage:"
    echo "   curl -fsSL https://raw.githubusercontent.com/ashzansoc/Zansoc-v5/main/cli/onboard.sh | bash -s tskey-auth-YOUR-KEY"
    echo ""
    exit 1
fi

TAILSCALE_AUTH_KEY="$1"
echo "🔑 Using provided Tailscale auth key: ${TAILSCALE_AUTH_KEY:0:20}..."

# Download and run the main onboarding script with the auth key
curl -fsSL https://raw.githubusercontent.com/ashzansoc/Zansoc-v5/main/cli/manual_onboarding.sh | bash -s "$TAILSCALE_AUTH_KEY"