# Raspberry Pi Temperature API Service

A background service for Raspberry Pi 4 that provides an API to monitor system statistics.

## Features

- Automatically starts on boot
- Runs continuously in the background
- Hosts an API on port 8585
- Provides multiple monitoring endpoints:
  - `/temp` - Get the current CPU temperature
  - `/stats` - Get comprehensive system statistics (CPU, memory, disk, network, etc.)
  - `/` - List available endpoints

## Installation

1. Clone this repository or copy the files to your Raspberry Pi:

```bash
git clone https://github.com/yourusername/piStat.git
cd piStat
```

2. Run the installation script:

```bash
bash install.sh
```

Alternatively, you can manually install the service:

```bash
# Install dependencies
pip3 install -r requirements.txt

# Copy the script to your home directory
cp pi_temp_service.py ~/
chmod +x ~/pi_temp_service.py

# Set up the service
sudo cp pi-temp-service.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pi-temp-service.service
sudo systemctl start pi-temp-service.service
```

## Usage

Once the service is running, you can access the API endpoints:

### List Available Endpoints
```bash
curl http://raspberry-pi-ip:8585/
```

### Get CPU Temperature
```bash
curl http://raspberry-pi-ip:8585/temp
```

Example response:
```json
{
  "temperature": 42.8,
  "unit": "Celsius",
  "timestamp": 1621234567.89
}
```

### Get Comprehensive System Statistics
```bash
curl http://raspberry-pi-ip:8585/stats
```

Example response:
```json
{
  "cpu_temp": 42.8,
  "cpu_freq": 1500.0,
  "cpu_usage": 23.5,
  "memory": {
    "total": 8589934592,
    "available": 6442450944,
    "used": 2147483648,
    "percent": 27.0
  },
  "disk": {
    "total": 32212254720,
    "used": 8053063680,
    "free": 24159191040,
    "percent": 28.8
  },
  "uptime": 86400.5,
  "load_avg": [0.5, 0.7, 0.9],
  "timestamp": 1621234567.89
}
```

## Managing the Service

### Checking Service Status

To check if the service is running:

```bash
sudo systemctl status pi-temp-service.service
```

To view the logs:

```bash
sudo journalctl -u pi-temp-service.service
```

### Stopping the Service

To temporarily stop the service:

```bash
sudo systemctl stop pi-temp-service.service
```

To prevent the service from starting at boot:

```bash
sudo systemctl disable pi-temp-service.service
```

### Restarting the Service

To restart the service:

```bash
sudo systemctl restart pi-temp-service.service
```

### Uninstalling the Service

To completely remove the service from your system:

```bash
# Stop and disable the service
sudo systemctl stop pi-temp-service.service
sudo systemctl disable pi-temp-service.service

# Remove the service file
sudo rm /etc/systemd/system/pi-temp-service.service

# Reload systemd to recognize the changes
sudo systemctl daemon-reload
sudo systemctl reset-failed

# Optionally, remove the Python script
rm ~/pi_temp_service.py
```

## Troubleshooting

If the service fails to start, check the logs for errors:

```bash
sudo journalctl -u pi-temp-service.service -e
```

Common issues:
- Make sure Flask and psutil are installed (`pip3 install flask psutil werkzeug==2.0.1`)
- Ensure the script path in the service file is correct
- Verify the script has execute permissions 