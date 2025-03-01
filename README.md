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

2. Install the required Python packages:

```bash
pip3 install -r requirements.txt
```

3. Copy the service file to the systemd directory:

```bash
sudo cp pi-temp-service.service /etc/systemd/system/
```

4. Copy the Python script to your home directory:

```bash
cp pi_temp_service.py /home/pi/
```

5. Make the script executable:

```bash
chmod +x /home/pi/pi_temp_service.py
```

6. Enable and start the service:

```bash
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
  "temperature": 42.8,
  "cpu_usage": 23.5,
  "memory": {
    "total": 3906.25,
    "available": 2853.12,
    "used": 1053.13,
    "percent": 27.0
  },
  "disk": {
    "total": 29.72,
    "used": 8.56,
    "free": 21.16,
    "percent": 28.8
  },
  "uptime": "3 days, 7:45:12",
  "network": {
    "bytes_sent": 1234567,
    "bytes_recv": 7654321,
    "packets_sent": 12345,
    "packets_recv": 54321
  },
  "timestamp": 1621234567.89
}
```

## Checking Service Status

To check if the service is running:

```bash
sudo systemctl status pi-temp-service.service
```

To view the logs:

```bash
sudo journalctl -u pi-temp-service.service
```

## Troubleshooting

If the service fails to start, check the logs for errors:

```bash
sudo journalctl -u pi-temp-service.service -e
```

Common issues:
- Make sure Flask and psutil are installed (`pip3 install flask psutil`)
- Ensure the script path in the service file is correct
- Verify the script has execute permissions 