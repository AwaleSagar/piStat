# Raspberry Pi System Monitor API

A background service for Raspberry Pi that provides a comprehensive API to monitor system statistics in real-time.

## Features

- Automatically starts on boot
- Runs continuously in the background
- Hosts an API on port 8585 (configurable)
- Provides the following endpoints:
  - `/stats` - Get comprehensive system statistics
  - `/health` - Simple health check endpoint
  - `/` - Interactive API documentation and usage guide
- Supports caching for improved performance
- Configurable via environment variables

## System Metrics

The API provides detailed metrics including:

- **CPU**: Temperature, frequency, usage (overall and per-core)
- **Memory**: RAM and swap usage
- **Disk**: Storage usage and I/O statistics
- **GPU**: Temperature, memory allocation, and V3D clock
- **Power**: Core voltage and throttling status
- **Network**: Interface statistics, WiFi signal strength, connections
- **Hardware**: Model info, serial number, and connected devices
- **System**: Uptime, load averages, and timestamps

## Installation

1. Clone this repository or copy the files to your Raspberry Pi:

```bash
git clone https://github.com/yourusername/piStat.git
cd piStat
```

2. Install dependencies:

```bash
pip3 install -r requirements.txt
```

3. Set up the service:

```bash
# Copy the script to your home directory
cp pi_system_monitor.py ~/
chmod +x ~/pi_system_monitor.py

# Set up the service
sudo cp pi-stat.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pi-stat.service
sudo systemctl start pi-stat.service
```

## Configuration

The application can be configured using environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| PISTAT_PORT | Port to run the server on | 8585 |
| PISTAT_HOST | Host address to bind to | 0.0.0.0 |
| PISTAT_CACHE_SECONDS | Cache duration in seconds | 2 |
| PISTAT_DEBUG | Enable debug mode | False |

You can set these variables in your environment or create a `.env` file.

## Usage

Once the service is running, you can access the API endpoints:

### API Documentation
```bash
curl http://raspberry-pi-ip:8585/
```
Or simply open `http://raspberry-pi-ip:8585/` in a web browser to view the interactive documentation.

### Health Check
```bash
curl http://raspberry-pi-ip:8585/health
```

Example response:
```json
{
  "status": "healthy",
  "uptime": 86400.5
}
```

### Get System Statistics
```bash
curl http://raspberry-pi-ip:8585/stats
```

Optional query parameters:
- `block=true` - Block for 1 second to get accurate CPU measurements
- `cache=false` - Bypass the cache to get fresh data

Example response:
```json
{
  "cpu_temp": 45.8,
  "cpu_freq": 1500.0,
  "cpu_usage": 12.5,
  "per_cpu_usage": [10.5, 14.2, 11.8, 13.5],
  "memory": {
    "total": 8589934592,
    "available": 6442450944,
    "used": 2147483648,
    "percent": 25.0
  },
  "swap": {
    "total": 1073741824,
    "used": 268435456,
    "free": 805306368,
    "percent": 25.0
  },
  "disk": {
    "total": 32212254720,
    "used": 8053063680,
    "free": 24159191040,
    "percent": 25.0
  },
  "disk_io": {
    "read_count": 12345,
    "write_count": 67890,
    "read_bytes": 123456789,
    "write_bytes": 987654321
  },
  "uptime": 86400.5,
  "load_avg": [0.5, 0.7, 0.9],
  "timestamp": 1646092800.0,
  "gpu": {
    "temperature": 44.2,
    "memory": 134217728,
    "v3d_clock": 500000000
  },
  "power": {
    "core_voltage": 1.35,
    "under_voltage": false,
    "throttled": false,
    "freq_capped": false
  },
  "clocks": {
    "arm": 1500000000,
    "core": 500000000,
    "sdram": 400000000
  },
  "network": {
    "eth0": {
      "bytes_sent": 12345678,
      "bytes_recv": 87654321,
      "packets_sent": 1234,
      "packets_recv": 5678,
      "errin": 0,
      "errout": 0,
      "dropin": 0,
      "dropout": 0
    },
    "wlan0": {
      "bytes_sent": 1234567,
      "bytes_recv": 7654321,
      "signal_strength": -58
    },
    "active_connections": 12
  },
  "hardware": {
    "model": "Raspberry Pi 4 Model B Rev 1.2",
    "serial": "10000000abcdef",
    "firmware": "Sep 3 2020 13:11:43",
    "usb_devices": 3
  }
}
```

## Response Fields Explained

- **CPU Metrics**:
  - `cpu_temp`: CPU temperature in Celsius
  - `cpu_freq`: CPU frequency in MHz
  - `cpu_usage`: Overall CPU usage percentage
  - `per_cpu_usage`: Usage percentage for each CPU core

- **Memory Metrics**:
  - `memory`: RAM usage statistics in bytes
  - `swap`: Swap memory usage statistics in bytes

- **Storage Metrics**:
  - `disk`: Disk usage statistics in bytes
  - `disk_io`: Disk I/O statistics (reads/writes)

- **GPU Metrics**:
  - `gpu.temperature`: GPU temperature in Celsius
  - `gpu.memory`: Allocated GPU memory in bytes
  - `gpu.v3d_clock`: VideoCore VI 3D clock frequency in Hz

- **Power Metrics**:
  - `power.core_voltage`: Core voltage in volts
  - `power.under_voltage`: Whether the Pi is experiencing undervoltage
  - `power.throttled`: Whether the Pi is being throttled
  - `power.freq_capped`: Whether the frequency is being capped

- **Clock Metrics**:
  - `clocks.arm`: ARM CPU clock frequency in Hz
  - `clocks.core`: Core clock frequency in Hz
  - `clocks.sdram`: SDRAM clock frequency in Hz

- **Network Metrics**:
  - Interface statistics (bytes sent/received, packets, errors)
  - WiFi signal strength (if available)
  - Active connection count

- **Hardware Info**:
  - Pi model information
  - Serial number
  - Firmware version
  - USB device count

- **System Metrics**:
  - `uptime`: System uptime in seconds
  - `load_avg`: System load averages for 1, 5, and 15 minutes
  - `timestamp`: Unix timestamp when the data was collected

## Testing the API

To test if the API is working correctly:

```bash
# Test on the local machine
curl http://localhost:8585/health

# Test on a remote Raspberry Pi
curl http://raspberry-pi-ip:8585/health
```

## Managing the Service

### Checking Service Status

To check if the service is running:

```bash
sudo systemctl status pi-stat.service
```

To view the logs:

```bash
sudo journalctl -u pi-stat.service
```

### Stopping the Service

To temporarily stop the service:

```bash
sudo systemctl stop pi-stat.service
```

To prevent the service from starting at boot:

```bash
sudo systemctl disable pi-stat.service
```

### Restarting the Service

To restart the service:

```bash
sudo systemctl restart pi-stat.service
```

### Uninstalling the Service

To completely remove the service from your system:

```bash
# Stop and disable the service
sudo systemctl stop pi-stat.service
sudo systemctl disable pi-stat.service

# Remove the service file
sudo rm /etc/systemd/system/pi-stat.service

# Reload systemd to recognize the changes
sudo systemctl daemon-reload
sudo systemctl reset-failed

# Optionally, remove the Python script
rm ~/pi_system_monitor.py
```

## Troubleshooting

If the service fails to start, check the logs for errors:

```bash
sudo journalctl -u pi-stat.service -e
```

Common issues:
- Make sure all dependencies are installed (`pip3 install -r requirements.txt`)
- Ensure the script path in the service file is correct
- Verify the script has execute permissions
- Check if port 8585 is already in use by another application
- Ensure `vcgencmd` and other system tools are available 