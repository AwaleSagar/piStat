from flask import Flask, jsonify, render_template_string, request, make_response
import psutil
import time
import subprocess
import os
import re
import json
import logging
import platform
import sys
from functools import lru_cache
from dotenv import load_dotenv
from collections import defaultdict, deque
import threading
import gzip
from typing import Dict, List, Union, Tuple, Optional, Any, Callable
from datetime import datetime

# Load environment variables from .env file if it exists
load_dotenv()

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('pi_system_monitor')

# Detect platform
IS_RASPBERRY_PI = False
PLATFORM_SYSTEM = platform.system()
if PLATFORM_SYSTEM == "Linux":
    try:
        with open('/proc/device-tree/model', 'r') as f:
            model = f.read().strip()
            IS_RASPBERRY_PI = "Raspberry Pi" in model
    except:
        # Not a Raspberry Pi or file doesn't exist
        pass

logger.info(f"Platform detected: {PLATFORM_SYSTEM}, Is Raspberry Pi: {IS_RASPBERRY_PI}")

# Improved configuration management with validation
def get_env_int(name: str, default: int, min_val: int = None, max_val: int = None) -> int:
    """Get integer environment variable with validation."""
    try:
        value = int(os.environ.get(name, default))
        if min_val is not None and value < min_val:
            logger.warning(f"{name} value {value} below minimum {min_val}, using minimum")
            return min_val
        if max_val is not None and value > max_val:
            logger.warning(f"{name} value {value} above maximum {max_val}, using maximum")
            return max_val
        return value
    except ValueError:
        logger.warning(f"Invalid {name} value, using default: {default}")
        return default

def get_env_bool(name: str, default: bool) -> bool:
    """Get boolean environment variable."""
    val = os.environ.get(name, str(default)).lower()
    return val in ('true', 't', '1', 'yes', 'y')

# Configuration with validation
PORT = get_env_int('PISTAT_PORT', 8585, 1, 65535)
HOST = os.environ.get('PISTAT_HOST', '0.0.0.0')
CACHE_SECONDS = get_env_int('PISTAT_CACHE_SECONDS', 2, 0, 3600)
DEBUG_MODE = get_env_bool('PISTAT_DEBUG', False)
LOG_LEVEL = os.environ.get('PISTAT_LOG_LEVEL', 'INFO').upper()
# Rate limiting configuration
RATE_LIMIT_ENABLED = get_env_bool('PISTAT_RATE_LIMIT_ENABLED', True)
RATE_LIMIT_REQUESTS = get_env_int('PISTAT_RATE_LIMIT_REQUESTS', 60, 1, 1000)
RATE_LIMIT_WINDOW = get_env_int('PISTAT_RATE_LIMIT_WINDOW', 60, 1, 3600)
# Compression
ENABLE_COMPRESSION = get_env_bool('PISTAT_COMPRESSION', True)
# Response size limit (in bytes)
MIN_SIZE_TO_COMPRESS = get_env_int('PISTAT_MIN_COMPRESS_SIZE', 500, 0, 10000)

# Update log level from configuration
if hasattr(logging, LOG_LEVEL):
    logger.setLevel(getattr(logging, LOG_LEVEL))
else:
    logger.warning(f"Invalid log level: {LOG_LEVEL}, using INFO")
    logger.setLevel(logging.INFO)

# Initialize Flask app
app = Flask(__name__)

# Improved rate limiting implementation using sliding window with deque
class RateLimiter:
    def __init__(self, window_size: int, max_requests: int):
        self.window_size = window_size
        self.max_requests = max_requests
        self.clients: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_requests))
        self.lock = threading.Lock()
    
    def is_rate_limited(self, client_id: str) -> bool:
        """Check if the client has exceeded the rate limit using sliding window"""
        if not RATE_LIMIT_ENABLED:
            return False
            
        with self.lock:
            now = time.time()
            client_history = self.clients[client_id]
            
            # Remove requests older than the window
            while client_history and now - client_history[0] > self.window_size:
                client_history.popleft()
            
            # Check if rate limit is exceeded
            if len(client_history) >= self.max_requests:
                return True
                
            # Record this request
            client_history.append(now)
            return False

# Create a rate limiter instance
rate_limiter = RateLimiter(RATE_LIMIT_WINDOW, RATE_LIMIT_REQUESTS)

# Custom request logging middleware
@app.before_request
def before_request():
    """Log request info and apply rate limiting"""
    # Apply rate limiting
    ip_address = request.remote_addr
    
    if rate_limiter.is_rate_limited(ip_address):
        logger.warning(f"Rate limit exceeded for IP: {ip_address}, endpoint: {request.path}")
        return jsonify({
            'error': 'Rate limit exceeded',
            'message': f'Maximum {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW} seconds'
        }), 429  # 429 Too Many Requests
    
    # Log request details in debug mode
    if DEBUG_MODE:
        logger.debug(f"Request from {ip_address}: {request.method} {request.path}")

# Response compression and additional headers
@app.after_request
def after_request(response):
    """Add security headers and compress response if needed"""
    # Add security headers
    response.headers.add('X-Content-Type-Options', 'nosniff')
    response.headers.add('X-Frame-Options', 'DENY')
    response.headers.add('X-XSS-Protection', '1; mode=block')
    response.headers.add('Cache-Control', f'public, max-age={CACHE_SECONDS}')
    
    # Add response timestamp
    response.headers.add('X-Response-Time', datetime.utcnow().isoformat())
    
    # Apply compression if enabled and response is large enough
    if (ENABLE_COMPRESSION and 
        response.status_code == 200 and
        not response.direct_passthrough and
        (response.content_length is None or response.content_length > MIN_SIZE_TO_COMPRESS) and
        'gzip' in request.headers.get('Accept-Encoding', '')):
        
        compressed_data = gzip.compress(response.data)
        response.data = compressed_data
        response.headers['Content-Encoding'] = 'gzip'
        response.headers['Content-Length'] = len(compressed_data)
    
    return response

# HTML template for the root page
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Raspberry Pi System Monitor API</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }
        h1 {
            color: #e74c3c;
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
        }
        h2 {
            color: #3498db;
            margin-top: 30px;
        }
        code {
            background-color: #f8f8f8;
            padding: 2px 5px;
            border-radius: 3px;
            font-family: monospace;
            border: 1px solid #ddd;
        }
        pre {
            background-color: #f8f8f8;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            border: 1px solid #ddd;
        }
        .endpoint {
            margin-bottom: 30px;
            padding: 15px;
            background-color: #f9f9f9;
            border-left: 4px solid #3498db;
        }
        .example {
            margin-top: 10px;
        }
        .params {
            margin-top: 10px;
            background-color: #f0f8ff;
            padding: 10px;
            border-radius: 5px;
        }
        .param-name {
            font-weight: bold;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
        }
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
    </style>
</head>
<body>
    <h1>Raspberry Pi System Monitor API</h1>
    <p>Welcome to the Raspberry Pi System Monitoring API. This service provides real-time system statistics for your Raspberry Pi.</p>
    
    <h2>Available Endpoints</h2>
    
    <div class="endpoint">
        <h3><code>GET /stats</code></h3>
        <p>Returns comprehensive system statistics including CPU temperature, CPU usage, memory usage, disk usage, uptime, and load averages.</p>
        
        <div class="params">
            <h4>Query Parameters:</h4>
            <table>
                <tr>
                    <th>Parameter</th>
                    <th>Type</th>
                    <th>Description</th>
                    <th>Default</th>
                </tr>
                <tr>
                    <td>block</td>
                    <td>boolean</td>
                    <td>Whether to block for 1 second to get more accurate CPU measurements</td>
                    <td>false</td>
                </tr>
                <tr>
                    <td>cache</td>
                    <td>boolean</td>
                    <td>Whether to use cached results if available</td>
                    <td>true</td>
                </tr>
                <tr>
                    <td>fields</td>
                    <td>string</td>
                    <td>Comma-separated list of fields to include in the response</td>
                    <td>All fields</td>
                </tr>
            </table>
        </div>
        
        <div class="example">
            <h4>Example Response:</h4>
            <pre>
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
    "memory": 134217728
  },
  "power": {
    "core_voltage": 1.35,
    "under_voltage": false,
    "throttled": false
  },
  "clocks": {
    "arm": 1500000000,
    "core": 500000000,
    "sdram": 400000000
  },
  "network": {
    "eth0": {
      "bytes_sent": 12345678,
      "bytes_recv": 87654321
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
    "usb_devices": 3
  }
}
            </pre>
        </div>
    </div>

    <div class="endpoint">
        <h3><code>GET /health</code></h3>
        <p>Simple health check endpoint to verify the service is up and running.</p>
        
        <div class="example">
            <h4>Example Response:</h4>
            <pre>
{
  "status": "healthy",
  "uptime": 86400.5
}
            </pre>
        </div>
    </div>

    <div class="endpoint">
        <h3><code>GET /processes</code></h3>
        <p>Returns information about running processes, sorted by CPU usage by default.</p>
        
        <div class="params">
            <h4>Query Parameters:</h4>
            <table>
                <tr>
                    <th>Parameter</th>
                    <th>Type</th>
                    <th>Description</th>
                    <th>Default</th>
                </tr>
                <tr>
                    <td>sort</td>
                    <td>string</td>
                    <td>Field to sort processes by (cpu, memory, name, pid, time)</td>
                    <td>cpu</td>
                </tr>
                <tr>
                    <td>limit</td>
                    <td>integer</td>
                    <td>Maximum number of processes to return</td>
                    <td>10</td>
                </tr>
            </table>
        </div>
        
        <div class="example">
            <h4>Example Response:</h4>
            <pre>
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
            </pre>
        </div>
    </div>

    <div class="endpoint">
        <h3><code>GET /network/interfaces</code></h3>
        <p>Provides detailed information about network interfaces and connections.</p>
        
        <div class="example">
            <h4>Example Response:</h4>
            <pre>
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
            </pre>
        </div>
    </div>

    <div class="endpoint">
        <h3><code>GET /storage/devices</code></h3>
        <p>Returns information about storage devices and partitions.</p>
        
        <div class="example">
            <h4>Example Response:</h4>
            <pre>
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
            </pre>
        </div>
    </div>
    
    <h2>Usage Examples</h2>
    
    <h3>Using curl</h3>
    <pre>curl http://YOUR_PI_IP:8585/stats</pre>
    <pre>curl "http://YOUR_PI_IP:8585/stats?fields=cpu_usage,memory,uptime"</pre>
    <pre>curl "http://YOUR_PI_IP:8585/processes?sort=memory&limit=5"</pre>
    
    <h3>Using Python</h3>
    <pre>
import requests

# Basic stats request
response = requests.get('http://YOUR_PI_IP:8585/stats')
data = response.json()
print(f"CPU Temperature: {data['cpu_temp']}°C")
print(f"CPU Usage: {data['cpu_usage']}%")

# Get only specific fields
fields = "cpu_usage,memory,uptime"
response = requests.get(f'http://YOUR_PI_IP:8585/stats?fields={fields}')
data = response.json()
print(f"CPU Usage: {data['cpu_usage']}%")
print(f"Memory Used: {data['memory']['percent']}%")
print(f"Uptime: {data['uptime'] / 86400:.1f} days")

# Get top memory-consuming processes
response = requests.get('http://YOUR_PI_IP:8585/processes?sort=memory&limit=5')
processes = response.json()['processes']
for proc in processes:
    print(f"{proc['name']} (PID {proc['pid']}): {proc['memory_percent']:.1f}% memory")
    </pre>
    
    <h2>Notes</h2>
    <ul>
        <li>All temperature values are in Celsius</li>
        <li>Memory and disk values are in bytes</li>
        <li>CPU frequency is in MHz</li>
        <li>Clock values are in Hz</li>
        <li>Uptime is in seconds</li>
        <li>Timestamp is Unix time (seconds since epoch)</li>
        <li>Rate limiting is enabled by default (60 requests per minute)</li>
    </ul>
    
    <p>For more information, visit the <a href="https://github.com/AwaleSagar/piStat">GitHub repository</a>.</p>
</body>
</html>
"""

# Improved caching mechanism
class StatCache:
    def __init__(self, ttl_seconds: int):
        self.cache = {}
        self.ttl = ttl_seconds
        self.lock = threading.Lock()
    
    def get(self, key: str, fields: List[str] = None):
        """Get cached data, optionally filtered by fields"""
        with self.lock:
            if key not in self.cache:
                return None
                
            data, timestamp = self.cache[key]
            
            if time.time() - timestamp > self.ttl:
                return None
                
            if fields:
                filtered_data = {}
                for field in fields:
                    field = field.strip()
                    if field in data:
                        filtered_data[field] = data[field]
                return filtered_data
            
            return data
    
    def set(self, key: str, data: Dict):
        """Store data in cache with current timestamp"""
        with self.lock:
            self.cache[key] = (data, time.time())
            
    def clear(self):
        """Clear all cached data"""
        with self.lock:
            self.cache.clear()

# Initialize cache with configured TTL
stats_cache = StatCache(CACHE_SECONDS)

def run_command(command: Union[str, List[str]], args: List[str] = None, 
                timeout: int = 5) -> Optional[str]:
    """
    Execute a shell command and return its output with timeout.
    
    Args:
        command: The command to execute (string or list)
        args: List of arguments for the command
        timeout: Maximum execution time in seconds
    
    Returns:
        Command output or None if execution failed
    """
    try:
        if isinstance(command, list) or args:
            cmd = command if isinstance(command, list) else [command]
            if args:
                cmd.extend(args)
            # Safer execution without shell=True
            result = subprocess.run(
                cmd, 
                shell=False, 
                check=True, 
                text=True, 
                capture_output=True,
                timeout=timeout
            )
        else:
            # Some commands might still need shell=True, but we're careful about inputs
            result = subprocess.run(
                command, 
                shell=True, 
                check=True, 
                text=True, 
                capture_output=True,
                timeout=timeout
            )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.warning(f"Command timed out after {timeout}s: {command} {args if args else ''}")
        return None
    except subprocess.CalledProcessError as e:
        logger.warning(f"Command failed: {command} {args if args else ''}, return code: {e.returncode}")
        return None
    except Exception as e:
        logger.error(f"Error executing command '{command}': {str(e)}")
        return None

# Apply LRU cache to expensive operations that don't change often
@lru_cache(maxsize=32, typed=True)
def get_hardware_info_cached() -> Dict:
    """
    Cached version of hardware info - doesn't change during runtime
    """
    return get_hardware_info()

def get_gpu_info():
    """
    Get GPU information from vcgencmd.
    
    Returns:
        dict: Dictionary containing GPU metrics or empty dict if unavailable
    """
    gpu_info = {}
    
    if not IS_RASPBERRY_PI:
        logger.debug("GPU info not available - not running on Raspberry Pi")
        return gpu_info
    
    try:
        # GPU temperature
        gpu_temp = run_command("vcgencmd", ["measure_temp"])
        if gpu_temp:
            match = re.search(r'temp=(\d+\.\d+)', gpu_temp)
            if match:
                gpu_info['temperature'] = float(match.group(1))
        
        # GPU memory
        gpu_mem = run_command("vcgencmd", ["get_mem", "gpu"])
        if gpu_mem:
            match = re.search(r'(\d+)M', gpu_mem)
            if match:
                gpu_info['memory'] = int(match.group(1)) * 1024 * 1024  # Convert MB to bytes
        
        # V3D utilization
        v3d_freq = run_command("vcgencmd", ["measure_clock", "v3d"])
        if v3d_freq:
            match = re.search(r'=(\d+)', v3d_freq)
            if match:
                gpu_info['v3d_clock'] = int(match.group(1))
    except Exception as e:
        logger.error(f"Error getting GPU info: {str(e)}")
    
    return gpu_info

def get_power_info():
    """
    Get power information from vcgencmd.
    
    Returns:
        dict: Dictionary containing power metrics or empty dict if unavailable
    """
    power_info = {}
    
    if not IS_RASPBERRY_PI:
        logger.debug("Power info not available - not running on Raspberry Pi")
        return power_info
    
    try:
        # Current voltage
        voltage = run_command("vcgencmd", ["measure_volts", "core"])
        if voltage:
            match = re.search(r'(\d+\.\d+)V', voltage)
            if match:
                power_info['core_voltage'] = float(match.group(1))
        
        # Throttling status
        throttled = run_command("vcgencmd", ["get_throttled"])
        if throttled:
            match = re.search(r'0x(\w+)', throttled)
            if match:
                throttle_value = int(match.group(1), 16)
                power_info['under_voltage'] = bool(throttle_value & 0x1)
                power_info['freq_capped'] = bool(throttle_value & 0x2)
                power_info['throttled'] = bool(throttle_value & 0x4)
    except Exception as e:
        logger.error(f"Error getting power info: {str(e)}")
    
    return power_info

def get_clock_info():
    """
    Get various clock frequencies from vcgencmd.
    
    Returns:
        dict: Dictionary containing clock frequencies or empty dict if unavailable
    """
    clock_info = {}
    
    if not IS_RASPBERRY_PI:
        logger.debug("Clock info not available - not running on Raspberry Pi")
        return clock_info
    
    try:
        # ARM clock
        arm_freq = run_command("vcgencmd", ["measure_clock", "arm"])
        if arm_freq:
            match = re.search(r'=(\d+)', arm_freq)
            if match:
                clock_info['arm'] = int(match.group(1))
        
        # Core clock
        core_freq = run_command("vcgencmd", ["measure_clock", "core"])
        if core_freq:
            match = re.search(r'=(\d+)', core_freq)
            if match:
                clock_info['core'] = int(match.group(1))
        
        # SDRAM clock
        sdram_freq = run_command("vcgencmd", ["measure_clock", "sdram"])
        if sdram_freq:
            match = re.search(r'=(\d+)', sdram_freq)
            if match:
                clock_info['sdram'] = int(match.group(1))
    except Exception as e:
        logger.error(f"Error getting clock info: {str(e)}")
    
    return clock_info

def get_network_details():
    """
    Get detailed network interface information.
    
    Returns:
        dict: Dictionary containing network interface statistics
    """
    network_info = {}
    
    try:
        # Get all network interfaces
        for interface, stats in psutil.net_io_counters(pernic=True).items():
            # Skip loopback
            if interface == 'lo':
                continue
                
            network_info[interface] = {
                'bytes_sent': stats.bytes_sent,
                'bytes_recv': stats.bytes_recv,
                'packets_sent': stats.packets_sent,
                'packets_recv': stats.packets_recv,
                'errin': stats.errin,
                'errout': stats.errout,
                'dropin': stats.dropin,
                'dropout': stats.dropout
            }
            
            # Add WiFi signal info if available and it's a wireless interface
            if interface.startswith('wlan'):
                try:
                    wifi_signal = run_command(f"iwconfig {interface} | grep 'Signal level'")
                    if wifi_signal:
                        match = re.search(r'Signal level=(-\d+) dBm', wifi_signal)
                        if match:
                            network_info[interface]['signal_strength'] = int(match.group(1))
                except Exception as e:
                    logger.warning(f"Could not get WiFi signal for {interface}: {str(e)}")
        
        # Count active connections
        connections = len(psutil.net_connections())
        network_info['active_connections'] = connections
    except Exception as e:
        logger.error(f"Error getting network details: {str(e)}")
        return {}
    
    return network_info

def get_hardware_info():
    """
    Get Raspberry Pi hardware information.
    
    Returns:
        dict: Dictionary containing hardware information
    """
    hardware_info = {}
    
    try:
        # Model information
        model_info = run_command("cat /proc/device-tree/model")
        if model_info:
            hardware_info['model'] = model_info
        
        # Serial number
        serial = run_command("cat /proc/cpuinfo | grep Serial | cut -d ' ' -f 2")
        if serial:
            hardware_info['serial'] = serial
        
        # Firmware version
        firmware = run_command("vcgencmd", ["version"])
        if firmware:
            hardware_info['firmware'] = firmware
        
        # Check for connected devices
        usb_devices = run_command("lsusb")
        if usb_devices:
            hardware_info['usb_devices'] = len(usb_devices.splitlines())
    except Exception as e:
        logger.error(f"Error getting hardware info: {str(e)}")
    
    return hardware_info

def get_swap_info():
    """
    Get swap memory usage.
    
    Returns:
        dict: Dictionary containing swap memory statistics
    """
    try:
        swap = psutil.swap_memory()
        return {
            'total': swap.total,
            'used': swap.used,
            'free': swap.free,
            'percent': swap.percent
        }
    except Exception as e:
        logger.error(f"Error getting swap info: {str(e)}")
        return {}

def get_disk_io():
    """
    Get disk I/O statistics.
    
    Returns:
        dict: Dictionary containing disk I/O statistics
    """
    try:
        disk_io = psutil.disk_io_counters()
        if disk_io:
            return {
                'read_count': disk_io.read_count,
                'write_count': disk_io.write_count,
                'read_bytes': disk_io.read_bytes,
                'write_bytes': disk_io.write_bytes,
                'read_time': disk_io.read_time,
                'write_time': disk_io.write_time
            }
    except Exception as e:
        logger.error(f"Error getting disk I/O info: {str(e)}")
    
    return {}

def get_cpu_usage(block=False):
    """
    Get CPU usage percentage.
    
    Args:
        block (bool): Whether to block for 1 second for more accurate readings
    
    Returns:
        float: CPU usage percentage
        list: Per-CPU usage percentages
    """
    try:
        if block:
            cpu_usage = psutil.cpu_percent(interval=1)
            per_cpu_usage = psutil.cpu_percent(interval=0, percpu=True)
        else:
            cpu_usage = psutil.cpu_percent(interval=0)
            per_cpu_usage = psutil.cpu_percent(interval=0, percpu=True)
        return cpu_usage, per_cpu_usage
    except Exception as e:
        logger.error(f"Error getting CPU usage: {str(e)}")
        return 0.0, []

@app.route('/', methods=['GET'])
def index():
    """
    Root endpoint that displays a simple webpage explaining the API usage.
    
    Returns:
        str: HTML documentation page
    """
    return render_template_string(HTML_TEMPLATE)

@app.route('/health', methods=['GET'])
def health_check():
    """
    Simple health check endpoint.
    
    Returns:
        JSON: Health status and uptime
    """
    try:
        uptime = time.time() - psutil.boot_time()
        memory = psutil.virtual_memory()
        
        health_data = {
            'status': 'healthy',
            'uptime': uptime,
            'memory_usage': memory.percent,
            'timestamp': time.time(),
            'version': '1.0.0'  # Add version info
        }
        
        return jsonify(health_data)
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': time.time()
        }), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    """
    Endpoint to retrieve real-time Raspberry Pi system statistics.
    Returns a JSON object with CPU, memory, disk, and other system metrics.
    
    Query Parameters:
        block (bool): Whether to block for CPU measurements (default: false)
        cache (bool): Whether to use cached results if available (default: true)
        fields (str): Comma-separated list of fields to include (default: all)
    
    Returns:
        JSON: System statistics
    """
    # Parse query parameters
    block = request.args.get('block', 'false').lower() == 'true'
    use_cache = request.args.get('cache', 'true').lower() == 'true'
    fields = request.args.get('fields')
    fields_list = fields.split(',') if fields else None
    
    # Check cache first
    if use_cache and fields_list:
        cached_stats = stats_cache.get('system_stats', fields_list)
        if cached_stats:
            return jsonify(cached_stats)
    elif use_cache:
        cached_stats = stats_cache.get('system_stats')
        if cached_stats:
            return jsonify(cached_stats)
    
    try:
        stats = {}
        
        # Get CPU temperature
        try:
            temps = psutil.sensors_temperatures()
            cpu_temp = None
            if 'cpu_thermal' in temps:
                cpu_temp = temps['cpu_thermal'][0].current  # Temperature in Celsius
            stats['cpu_temp'] = cpu_temp
        except Exception as e:
            logger.debug(f"Failed to get CPU temperature: {str(e)}")
            stats['cpu_temp'] = None

        # Get CPU frequency (in MHz)
        try:
            cpu_freq_info = psutil.cpu_freq()
            cpu_freq = cpu_freq_info.current if cpu_freq_info else None
            stats['cpu_freq'] = cpu_freq
        except Exception as e:
            logger.debug(f"Failed to get CPU frequency: {str(e)}")
            stats['cpu_freq'] = None

        # Get CPU usage percentage
        try:
            cpu_usage, per_cpu_usage = get_cpu_usage(block=block)
            stats['cpu_usage'] = cpu_usage
            stats['per_cpu_usage'] = per_cpu_usage
        except Exception as e:
            logger.warning(f"Failed to get CPU usage: {str(e)}")
            stats['cpu_usage'] = None
            stats['per_cpu_usage'] = []

        # Get memory usage
        try:
            memory = psutil.virtual_memory()
            stats['memory'] = {
                'total': memory.total,      # Total memory in bytes
                'available': memory.available,  # Available memory in bytes
                'used': memory.used,        # Used memory in bytes
                'percent': memory.percent   # Percentage used
            }
        except Exception as e:
            logger.warning(f"Failed to get memory info: {str(e)}")
            stats['memory'] = {}

        # Add other metrics
        stats['swap'] = get_swap_info()
        stats['disk'] = get_disk_usage()
        stats['disk_io'] = get_disk_io()
        stats['uptime'] = get_system_uptime()
        stats['load_avg'] = get_load_averages()
        stats['timestamp'] = time.time()
        
        # Add additional metrics that might be expensive - consider making them optional
        stats['gpu'] = get_gpu_info()
        stats['power'] = get_power_info()
        stats['clocks'] = get_clock_info()
        stats['network'] = get_network_details()
        stats['hardware'] = get_hardware_info_cached()

        # Update cache
        stats_cache.set('system_stats', stats)
        
        # Filter by requested fields if specified
        if fields_list:
            filtered_stats = {}
            for field in fields_list:
                field = field.strip()
                if field in stats:
                    filtered_stats[field] = stats[field]
            return jsonify(filtered_stats)
        
        # Return all stats as JSON
        return jsonify(stats)
    
    except Exception as e:
        logger.error(f"Error collecting system stats: {str(e)}")
        return jsonify({
            'error': 'Failed to collect system statistics',
            'details': str(e),
            'timestamp': time.time()
        }), 500

# Helper functions to modularize the stats collection
def get_disk_usage() -> Dict:
    """Get disk usage for the root filesystem"""
    try:
        disk = psutil.disk_usage('/')
        return {
            'total': disk.total,
            'used': disk.used,
            'free': disk.free,
            'percent': disk.percent
        }
    except Exception as e:
        logger.warning(f"Failed to get disk usage: {str(e)}")
        return {}

def get_system_uptime() -> float:
    """Get system uptime in seconds"""
    try:
        return time.time() - psutil.boot_time()
    except Exception as e:
        logger.warning(f"Failed to get uptime: {str(e)}")
        return 0

def get_load_averages() -> List[float]:
    """Get system load averages"""
    try:
        return list(psutil.getloadavg())
    except Exception as e:
        logger.warning(f"Failed to get load averages: {str(e)}")
        return []

@app.route('/processes', methods=['GET'])
def get_processes():
    """
    Endpoint to retrieve information about running processes.
    
    Query Parameters:
        sort (str): Sort processes by this field (default: 'cpu')
        limit (int): Number of processes to return (default: 10)
        
    Returns:
        JSON: List of processes with details
    """
    try:
        # Parse query parameters
        sort_by = request.args.get('sort', 'cpu').lower()
        limit = min(int(request.args.get('limit', 10)), 100)  # Cap at 100 to prevent excessive response sizes
        
        processes_list = []
        valid_sort_fields = ['cpu', 'memory', 'name', 'pid', 'time']
        
        # Default to CPU if invalid sort field
        if sort_by not in valid_sort_fields:
            sort_by = 'cpu'
            
        sort_mapping = {
            'cpu': lambda p: p['cpu_percent'],
            'memory': lambda p: p['memory_percent'],
            'name': lambda p: p['name'].lower(),
            'pid': lambda p: p['pid'],
            'time': lambda p: p['running_time']
        }
        
        # Get all processes
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'create_time']):
            try:
                process_info = proc.info
                # Calculate running time
                process_info['running_time'] = time.time() - process_info['create_time']
                processes_list.append({
                    'pid': process_info['pid'],
                    'name': process_info['name'],
                    'user': process_info['username'],
                    'cpu_percent': process_info['cpu_percent'],
                    'memory_percent': process_info['memory_percent'],
                    'running_time': process_info['running_time']
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Sort processes by the selected field (descending for cpu and memory)
        reverse_sort = sort_by in ['cpu', 'memory', 'time']
        processes_list.sort(key=sort_mapping[sort_by], reverse=reverse_sort)
        
        # Limit the number of results
        processes_list = processes_list[:limit]
        
        return jsonify({
            'processes': processes_list,
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Error getting process information: {str(e)}")
        return jsonify({
            'error': 'Failed to get process information',
            'details': str(e)
        }), 500

@app.route('/network/interfaces', methods=['GET'])
def get_network_interfaces():
    """
    Endpoint to retrieve detailed information about network interfaces.
    
    Returns:
        JSON: Network interface details
    """
    try:
        return jsonify({
            'interfaces': get_network_details(),
            'timestamp': time.time()
        })
    except Exception as e:
        logger.error(f"Error getting network interface information: {str(e)}")
        return jsonify({
            'error': 'Failed to get network interface information',
            'details': str(e)
        }), 500

@app.route('/storage/devices', methods=['GET'])
def get_storage_devices():
    """
    Endpoint to retrieve information about storage devices.
    
    Returns:
        JSON: Storage device information
    """
    try:
        storage_info = []
        
        # Get all disk partitions
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                storage_info.append({
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'filesystem': partition.fstype,
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': usage.percent
                })
            except PermissionError:
                # Some mountpoints might not be accessible
                storage_info.append({
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'filesystem': partition.fstype,
                    'access_error': True
                })
        
        return jsonify({
            'devices': storage_info,
            'disk_io': get_disk_io(),
            'timestamp': time.time()
        })
    except Exception as e:
        logger.error(f"Error getting storage device information: {str(e)}")
        return jsonify({
            'error': 'Failed to get storage device information', 
            'details': str(e)
        }), 500

# Add a new endpoint for system metrics over time
@app.route('/metrics/history', methods=['GET'])
def get_metric_history():
    """
    Endpoint to retrieve historical metrics.
    
    Query Parameters:
        metric (str): The metric to return history for (cpu, memory, temp)
        duration (int): Duration in minutes to look back (default: 10)
        
    Returns:
        JSON: Historical metric data
    """
    # This would require a proper time-series storage implementation
    # For now, return a placeholder
    return jsonify({
        'message': 'Historical metrics not implemented yet. Consider using a time-series database.',
        'timestamp': time.time()
    })

# Add a system config endpoint
@app.route('/system/config', methods=['GET'])
def get_system_config():
    """
    Endpoint to retrieve system configuration information.
    
    Returns:
        JSON: System configuration details
    """
    try:
        config_info = {
            'platform': PLATFORM_SYSTEM,
            'is_raspberry_pi': IS_RASPBERRY_PI,
            'hostname': platform.node(),
            'python_version': platform.python_version(),
            'server': {
                'port': PORT,
                'host': HOST,
                'debug_mode': DEBUG_MODE,
                'cache_seconds': CACHE_SECONDS,
                'rate_limiting': {
                    'enabled': RATE_LIMIT_ENABLED,
                    'requests': RATE_LIMIT_REQUESTS,
                    'window': RATE_LIMIT_WINDOW
                },
                'compression': {
                    'enabled': ENABLE_COMPRESSION,
                    'min_size': MIN_SIZE_TO_COMPRESS
                }
            },
            'timestamp': time.time()
        }
        return jsonify(config_info)
    except Exception as e:
        logger.error(f"Error getting system config: {str(e)}")
        return jsonify({
            'error': 'Failed to get system configuration',
            'details': str(e)
        }), 500

# Graceful shutdown handler
def graceful_shutdown(signal_number, frame):
    """Handle graceful shutdown on SIGTERM/SIGINT"""
    logger.info(f"Received signal {signal_number}, shutting down...")
    # Clean up resources
    stats_cache.clear()
    sys.exit(0)

# Run the Flask app
if __name__ == '__main__':
    # Register signal handlers for graceful shutdown
    import signal
    signal.signal(signal.SIGTERM, graceful_shutdown)
    signal.signal(signal.SIGINT, graceful_shutdown)
    
    logger.info(f"Starting Pi System Monitor on {HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=DEBUG_MODE)