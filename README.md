# Raspberry Pi System Monitor API

A background service that provides a comprehensive API to monitor system statistics in real-time. While optimized for Raspberry Pi, it now includes cross-platform support.

## Features

- Automatically starts on boot
- Runs continuously in the background
- Hosts an API on port 8585 (configurable)
- Provides the following endpoints:
  - `/stats` - Get comprehensive system statistics
  - `/processes` - List running processes with resource usage
  - `/network/interfaces` - Network interface details
  - `/storage/devices` - Storage device information
  - `/health` - Simple health check endpoint
  - `/` - Interactive API documentation and usage guide
- Cross-platform support (optimized for Raspberry Pi)
- Robust error handling and graceful degradation
- Smart caching for improved performance
- Field filtering capability for optimized responses
- Rate limiting for API protection
- Configurable via environment variables or `.env` file

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

1. Clone this repository or copy the files to your device:

```bash
git clone https://github.com/yourusername/piStat.git
cd piStat
```

2. Install dependencies:

```bash
pip3 install -r requirements.txt
```

3. Set up the service (Linux/Raspberry Pi):

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

The application can be configured using environment variables or a `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| PISTAT_PORT | Port to run the server on | 8585 |
| PISTAT_HOST | Host address to bind to | 0.0.0.0 |
| PISTAT_CACHE_SECONDS | Cache duration in seconds | 2 |
| PISTAT_DEBUG | Enable debug mode | False |
| PISTAT_LOG_LEVEL | Logging level (INFO, DEBUG, etc) | INFO |
| PISTAT_RATE_LIMIT_ENABLED | Enable rate limiting | True |
| PISTAT_RATE_LIMIT_REQUESTS | Request limit per window | 60 |
| PISTAT_RATE_LIMIT_WINDOW | Rate limit window in seconds | 60 |

You can set these variables in your environment or create a `.env` file in the same directory as the script.

## Usage

Once the service is running, you can access the API endpoints:

### API Documentation
```bash
curl http://device-ip:8585/
```
Or simply open `http://device-ip:8585/` in a web browser to view the interactive documentation.

### Health Check
```bash
curl http://device-ip:8585/health
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
curl http://device-ip:8585/stats
```

Optional query parameters:
- `block=true` - Block for 1 second to get accurate CPU measurements
- `cache=false` - Bypass the cache to get fresh data
- `fields=cpu_usage,memory,uptime` - Retrieve only specific fields

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

### Get Running Processes
```bash
curl http://device-ip:8585/processes
```

Optional query parameters:
- `sort=cpu` - Sort by resource usage (cpu, memory, name, pid, time)
- `limit=10` - Maximum number of processes to return

Example response:
```json
{
  "processes": [
    {
      "pid": 1234,
      "name": "python3",
      "user": "pi",
      "cpu_percent": 15.2,
      "memory_percent": 3.5,
      "running_time": 3600.5
    },
    {
      "pid": 5678,
      "name": "nginx",
      "user": "www-data",
      "cpu_percent": 4.8,
      "memory_percent": 1.2,
      "running_time": 86400.2
    }
  ],
  "timestamp": 1646092800.0
}
```

### Get Network Interface Details
```bash
curl http://device-ip:8585/network/interfaces
```

Example response:
```json
{
  "interfaces": {
    "eth0": {
      "bytes_sent": 12345678,
      "bytes_recv": 87654321,
      "packets_sent": 12345,
      "packets_recv": 54321,
      "errin": 0,
      "errout": 0,
      "dropin": 0,
      "dropout": 0
    },
    "wlan0": {
      "bytes_sent": 1234567,
      "bytes_recv": 7654321,
      "packets_sent": 1234,
      "packets_recv": 4321,
      "errin": 0,
      "errout": 0,
      "dropin": 0,
      "dropout": 0,
      "signal_strength": -58
    },
    "active_connections": 12
  },
  "timestamp": 1646092800.0
}
```

### Get Storage Device Information
```bash
curl http://device-ip:8585/storage/devices
```

Example response:
```json
{
  "devices": [
    {
      "device": "/dev/mmcblk0p1",
      "mountpoint": "/boot",
      "filesystem": "vfat",
      "total": 268435456,
      "used": 67108864,
      "free": 201326592,
      "percent": 25.0
    },
    {
      "device": "/dev/mmcblk0p2",
      "mountpoint": "/",
      "filesystem": "ext4",
      "total": 32212254720,
      "used": 8053063680,
      "free": 24159191040,
      "percent": 25.0
    }
  ],
  "disk_io": {
    "read_count": 12345,
    "write_count": 67890,
    "read_bytes": 123456789,
    "write_bytes": 987654321,
    "read_time": 12345,
    "write_time": 67890
  },
  "timestamp": 1646092800.0
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

## Cross-Platform Support

The application will automatically detect if it's running on a Raspberry Pi and adjust functionality accordingly:

- On Raspberry Pi: All features are fully available
- On other Linux systems: Most features work, but Pi-specific metrics are unavailable
- On Windows/macOS: Basic system metrics only (no Pi-specific hardware info)

## Advanced Usage Examples

### Python Client

```python
import requests

# Basic stats request
response = requests.get('http://device-ip:8585/stats')
data = response.json()
print(f"CPU Temperature: {data['cpu_temp']}°C")
print(f"CPU Usage: {data['cpu_usage']}%")

# Get only specific fields
fields = "cpu_usage,memory,uptime"
response = requests.get(f'http://device-ip:8585/stats?fields={fields}')
data = response.json()
print(f"CPU Usage: {data['cpu_usage']}%")
print(f"Memory Used: {data['memory']['percent']}%")
print(f"Uptime: {data['uptime'] / 86400:.1f} days")

# Get top memory-consuming processes
response = requests.get('http://device-ip:8585/processes?sort=memory&limit=5')
processes = response.json()['processes']
for proc in processes:
    print(f"{proc['name']} (PID {proc['pid']}): {proc['memory_percent']:.1f}% memory")
```

## Testing the API

To test if the API is working correctly:

```bash
# Test on the local machine
curl http://localhost:8585/health

# Test on a remote device
curl http://device-ip:8585/health
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
- Ensure `vcgencmd` and other system tools are available (Raspberry Pi only)
- Check if the `.env` file has proper permissions
- Verify rate limit settings are appropriate for your use case

## Rate Limiting

By default, the API is protected by rate limiting (60 requests per minute per IP address). If a client exceeds this limit, they'll receive a 429 Too Many Requests response. You can adjust or disable this feature using the environment variables described in the Configuration section.