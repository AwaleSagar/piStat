# Raspberry Pi System Monitor API

A background service for Raspberry Pi that provides an API to monitor system statistics in real-time.

## Features

- Automatically starts on boot
- Runs continuously in the background
- Hosts an API on port 8585
- Provides the following endpoints:
  - `/stats` - Get comprehensive system statistics (CPU, memory, disk, etc.)
  - `/` - Interactive API documentation and usage guide

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

### API Documentation
```bash
curl http://raspberry-pi-ip:8585/
```
Or simply open `http://raspberry-pi-ip:8585/` in a web browser to view the interactive documentation.

### Get System Statistics
```bash
curl http://raspberry-pi-ip:8585/stats
```

Example response:
```json
{
  "cpu_temp": 45.8,
  "cpu_freq": 1500.0,
  "cpu_usage": 12.5,
  "memory": {
    "total": 8589934592,
    "available": 6442450944,
    "used": 2147483648,
    "percent": 25.0
  },
  "disk": {
    "total": 32212254720,
    "used": 8053063680,
    "free": 24159191040,
    "percent": 25.0
  },
  "uptime": 86400.5,
  "load_avg": [0.5, 0.7, 0.9],
  "timestamp": 1646092800.0
}
```

### Response Fields Explained

- `cpu_temp`: CPU temperature in Celsius
- `cpu_freq`: CPU frequency in MHz
- `cpu_usage`: CPU usage percentage
- `memory`: Memory usage statistics in bytes
- `disk`: Disk usage statistics in bytes
- `uptime`: System uptime in seconds
- `load_avg`: System load averages for 1, 5, and 15 minutes
- `timestamp`: Unix timestamp when the data was collected

## Testing the API

The repository includes a test script that can verify the API is working correctly:

```bash
# Test on the local machine
python3 test_api.py

# Test on a remote Raspberry Pi
python3 test_api.py -H 192.168.1.100 -p 8585
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
- Make sure all dependencies are installed (`pip3 install flask psutil werkzeug==2.0.1 tabulate`)
- Ensure the script path in the service file is correct
- Verify the script has execute permissions
- Check if port 8585 is already in use by another application 