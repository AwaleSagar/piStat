#!/bin/bash

# Colors for better readability
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Exit on error, but with proper cleanup
set -e

echo -e "${GREEN}Installing Raspberry Pi System Monitor API Service...${NC}"

# Check if running as root (which is not recommended)
if [ "$(id -u)" = "0" ]; then
   echo -e "${YELLOW}WARNING: Running as root. It's better to run as a regular user with sudo privileges.${NC}"
fi

# Ask for Python path with default
DEFAULT_PYTHON_PATH="/usr/bin/python3"
echo -e "${YELLOW}Enter the path to your Python interpreter [default: $DEFAULT_PYTHON_PATH]:${NC}"
read -r PYTHON_PATH

# Use default if nothing was entered
if [ -z "$PYTHON_PATH" ]; then
    PYTHON_PATH="$DEFAULT_PYTHON_PATH"
    echo "Using default Python path: $PYTHON_PATH"
fi

# Validate that the Python path exists and is executable
if [ ! -x "$PYTHON_PATH" ]; then
    echo -e "${RED}Error: $PYTHON_PATH is not executable or does not exist.${NC}"
    echo -e "${YELLOW}Checking if Python 3 is available at the default location...${NC}"
    
    if [ -x "$DEFAULT_PYTHON_PATH" ]; then
        echo "Found Python at default location, using: $DEFAULT_PYTHON_PATH"
        PYTHON_PATH="$DEFAULT_PYTHON_PATH"
    else
        echo -e "${RED}Python 3 was not found at the default location either.${NC}"
        echo -e "${RED}Please install Python 3 or provide a valid path to your Python interpreter.${NC}"
        exit 1
    fi
fi

# Verify it's Python 3
PYTHON_VERSION=$($PYTHON_PATH --version 2>&1)
if [[ $PYTHON_VERSION != *"Python 3"* ]]; then
    echo -e "${RED}Error: $PYTHON_PATH is not Python 3.${NC}"
    echo -e "${RED}Found: $PYTHON_VERSION${NC}"
    echo -e "${RED}Please provide a valid path to Python 3.${NC}"
    exit 1
fi

echo -e "${GREEN}Using Python: $PYTHON_PATH ($PYTHON_VERSION)${NC}"

# Install dependencies
echo "Installing dependencies..."
$PYTHON_PATH -m pip install -r requirements.txt --force-reinstall || { echo -e "${RED}Failed to install dependencies. Check your internet connection and pip installation.${NC}"; exit 1; }

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

# Update the service file with the current username and home directory
echo "Configuring service file..."
CURRENT_USER=$(whoami)
cp pi-stat.service pi-stat.service.tmp
sed -i "s/%u/$CURRENT_USER/g" pi-stat.service.tmp
sed -i "s|%h|$USER_HOME|g" pi-stat.service.tmp
sed -i "s|/usr/bin/python3|$PYTHON_PATH|g" pi-stat.service.tmp

# Backup existing service files if they exist
echo "Checking for existing service files..."
if [ -f "/etc/systemd/system/pi-temp-service.service" ]; then
    echo "Found old service file (pi-temp-service.service)"
    echo "Backing up old service file..."
    sudo cp "/etc/systemd/system/pi-temp-service.service" "$BACKUP_DIR/"
    
    # Stop and disable the old service if it's running
    if sudo systemctl is-active --quiet pi-temp-service.service; then
        echo "Stopping old service..."
        sudo systemctl stop pi-temp-service.service 2>/dev/null || true
    fi
    
    if sudo systemctl is-enabled --quiet pi-temp-service.service 2>/dev/null; then
        echo "Disabling old service..."
        sudo systemctl disable pi-temp-service.service 2>/dev/null || true
    fi
    
    # Remove the old service file
    echo "Removing old service file..."
    sudo rm "/etc/systemd/system/pi-temp-service.service"
fi

if [ -f "/etc/systemd/system/pi-stat.service" ]; then
    echo "Found existing pi-stat.service"
    echo "Backing up existing service file..."
    sudo cp "/etc/systemd/system/pi-stat.service" "$BACKUP_DIR/"
    
    # Stop the service if it's running
    if sudo systemctl is-active --quiet pi-stat.service; then
        echo "Stopping existing service..."
        sudo systemctl stop pi-stat.service 2>/dev/null || true
    fi
fi

# Copy and enable the systemd service
echo "Setting up systemd service..."
sudo cp pi-stat.service.tmp /etc/systemd/system/pi-stat.service
rm pi-stat.service.tmp

# Reload systemd configuration
echo "Reloading systemd configuration..."
sudo systemctl daemon-reload

# Enable and start the service
echo "Enabling and starting the service..."
sudo systemctl enable pi-stat.service
sudo systemctl start pi-stat.service

# Create .env file for environment variables if it doesn't exist
if [ ! -f "$USER_HOME/.env" ]; then
    echo "Creating default environment configuration file..."
    cat > "$USER_HOME/.env" << EOF
# Raspberry Pi System Monitor configuration
# Uncomment and modify as needed

# PISTAT_PORT=8585          # Port to run the server on
# PISTAT_HOST=0.0.0.0       # Host address to bind to (0.0.0.0 = all interfaces)
# PISTAT_CACHE_SECONDS=2    # How long to cache results in seconds
# PISTAT_DEBUG=False        # Enable debug mode (True/False)
EOF
    echo "Created .env file at $USER_HOME/.env"
fi

# Wait a moment for the service to start
sleep 2

# Check if the service started successfully
if sudo systemctl is-active --quiet pi-stat.service; then
    echo -e "${GREEN}Service started successfully!${NC}"
    # Check service status
    echo "Checking service status..."
    sudo systemctl status pi-stat.service
else
    echo -e "${RED}Service failed to start. Checking logs...${NC}"
    sudo journalctl -u pi-stat.service -n 20
    echo -e "${YELLOW}You can view more logs with: sudo journalctl -u pi-stat.service -f${NC}"
fi

# Get the IP address
IP_ADDRESS=$(hostname -I | awk '{print $1}')

# Display success message and instructions
echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Installation complete!${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo "You can access the API at: http://$IP_ADDRESS:8585/"
echo ""
echo -e "${YELLOW}Available endpoints:${NC}"
echo "  - /        (API documentation and usage guide)"
echo "  - /stats   (Get comprehensive system statistics)"
echo "  - /health  (Simple health check endpoint)"
echo ""
echo -e "${YELLOW}Configuration:${NC}"
echo "  Edit $USER_HOME/.env to customize port, host, and other settings"
echo ""
echo -e "${YELLOW}Quick commands:${NC}"
echo "  Test API:           curl http://$IP_ADDRESS:8585/health"
echo "  View logs:          sudo journalctl -u pi-stat.service -f"
echo "  Restart service:    sudo systemctl restart pi-stat.service"
echo "  Stop service:       sudo systemctl stop pi-stat.service"
echo "  Configuration file: nano $USER_HOME/.env"
echo ""
echo -e "${YELLOW}Backup information:${NC}"
echo "  All previous files were backed up to: $BACKUP_DIR"
echo ""
echo -e "${GREEN}Thank you for installing the Raspberry Pi System Monitor!${NC}" 