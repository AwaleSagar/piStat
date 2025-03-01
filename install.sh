#!/bin/bash

# Exit on error
set -e

echo "Installing Raspberry Pi System Monitoring API Service..."

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt --force-reinstall

# Copy the Python script to home directory
echo "Copying script to home directory..."
# Get the current user's home directory
USER_HOME=$(eval echo ~$USER)
echo "Detected home directory: $USER_HOME"
cp pi_temp_service.py $USER_HOME/
chmod +x $USER_HOME/pi_temp_service.py

# Update the service file with the current username
echo "Configuring service file..."
CURRENT_USER=$(whoami)
sed -i "s/%u/$CURRENT_USER/g" pi-temp-service.service
sed -i "s|%h|$USER_HOME|g" pi-temp-service.service

# Copy and enable the systemd service
echo "Setting up systemd service..."
sudo cp pi-temp-service.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pi-temp-service.service
sudo systemctl start pi-temp-service.service

# Check service status
echo "Checking service status..."
sudo systemctl status pi-temp-service.service

echo ""
echo "Installation complete! The service is now running."
echo "You can access the API at: http://$(hostname -I | awk '{print $1}'):8585/"
echo "Available endpoints:"
echo "  - /stats   (Get comprehensive system statistics)" 