#!/bin/bash

# add-hosts.sh
# Adds DNS entries to /etc/hosts for local development
# Requires sudo privileges

set -euo pipefail

HOSTS_FILE="/etc/hosts"
ENTRIES=(
    "127.0.0.1 dashboard.local.store"
    "127.0.0.1 api.local.store"
)

echo "==================================="
echo "Add DNS Entries to /etc/hosts"
echo "==================================="
echo ""

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "❌ Error: This script requires sudo privileges."
    echo ""
    echo "Please run with sudo:"
    echo "  sudo bash add-hosts.sh"
    echo ""
    exit 1
fi

echo "📝 Adding the following entries to $HOSTS_FILE:"
echo ""
for entry in "${ENTRIES[@]}"; do
    echo "  $entry"
done
echo ""

# Backup hosts file
BACKUP_FILE="${HOSTS_FILE}.backup-$(date +%Y%m%d-%H%M%S)"
echo "💾 Creating backup: $BACKUP_FILE"
cp "$HOSTS_FILE" "$BACKUP_FILE"
echo ""

# Add entries
echo "➕ Adding entries..."
for entry in "${ENTRIES[@]}"; do
    # Check if entry already exists
    if grep -qF "$entry" "$HOSTS_FILE"; then
        echo "  ℹ️  Entry already exists: $entry"
    else
        echo "$entry" >> "$HOSTS_FILE"
        echo "  ✅ Added: $entry"
    fi
done
echo ""

echo "==================================="
echo "✅ Complete!"
echo "==================================="
echo ""
echo "DNS entries added successfully."
echo ""
echo "You can now access:"
echo "  • Dashboard: http://dashboard.local.store"
echo "  • API: http://api.local.store"
echo ""
echo "📌 Note: For individual store URLs (e.g., mystore-abc123.local.store),"
echo "you'll need to either:"
echo "  1. Add them manually to /etc/hosts as they're created, or"
echo "  2. Set up wildcard DNS with dnsmasq (see docs/LOCAL_DNS_SETUP.md)"
echo ""
