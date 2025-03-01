#!/bin/bash

# Exit on error
set -e

echo "Installing Raspberry Pi System Monitoring API Service..."

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt

# Copy the Python script to home directory
echo "Copying script to home directory..."
cp pi_temp_service.py /home/pi/
chmod +x /home/pi/pi_temp_service.py

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
echo "  - /        (List available endpoints)"
echo "  - /temp    (Get CPU temperature)"
echo "  - /stats   (Get comprehensive system statistics)" 