#!/bin/bash

# Exit on error
set -e

echo "Installing Raspberry Pi System Monitor API Service..."

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt --force-reinstall

# Create a backup directory for any existing files
BACKUP_DIR="$HOME/pistat_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
echo "Created backup directory: $BACKUP_DIR"

# Copy the Python script to home directory
echo "Copying script to home directory..."
# Get the current user's home directory
USER_HOME=$(eval echo ~$USER)
echo "Detected home directory: $USER_HOME"

# Backup existing script if it exists
if [ -f "$USER_HOME/pi_system_monitor.py" ]; then
    echo "Backing up existing script..."
    cp "$USER_HOME/pi_system_monitor.py" "$BACKUP_DIR/"
fi

# Also backup old script name if it exists
if [ -f "$USER_HOME/pi_temp_service.py" ]; then
    echo "Backing up old script..."
    cp "$USER_HOME/pi_temp_service.py" "$BACKUP_DIR/"
    # Remove old script to avoid confusion
    rm "$USER_HOME/pi_temp_service.py"
fi

# Copy and set permissions
cp pi_system_monitor.py "$USER_HOME/"
chmod +x "$USER_HOME/pi_system_monitor.py"

# Update the service file with the current username
echo "Configuring service file..."
CURRENT_USER=$(whoami)
sed -i "s/%u/$CURRENT_USER/g" pi-temp-service.service
sed -i "s|%h|$USER_HOME|g" pi-temp-service.service

# Backup existing service if it exists
if [ -f "/etc/systemd/system/pi-temp-service.service" ]; then
    echo "Backing up existing service file..."
    sudo cp "/etc/systemd/system/pi-temp-service.service" "$BACKUP_DIR/"
fi

# Copy and enable the systemd service
echo "Setting up systemd service..."
sudo cp pi-temp-service.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pi-temp-service.service
sudo systemctl restart pi-temp-service.service

# Check service status
echo "Checking service status..."
sudo systemctl status pi-temp-service.service

# Get the IP address
IP_ADDRESS=$(hostname -I | awk '{print $1}')

echo ""
echo "Installation complete! The service is now running."
echo "You can access the API at: http://$IP_ADDRESS:8585/"
echo "Available endpoints:"
echo "  - /        (API documentation and usage guide)"
echo "  - /stats   (Get comprehensive system statistics)"
echo ""
echo "To test the API, run:"
echo "  python3 test_api.py"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u pi-temp-service.service -f" 