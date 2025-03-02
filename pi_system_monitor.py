from flask import Flask, jsonify, render_template_string, request
import psutil
import time
import subprocess
import os
import re
import json
import logging
from functools import lru_cache

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('pi_system_monitor')

# Configuration management
# Get configuration from environment variables with defaults
PORT = int(os.environ.get('PISTAT_PORT', 8585))
HOST = os.environ.get('PISTAT_HOST', '0.0.0.0')
CACHE_SECONDS = int(os.environ.get('PISTAT_CACHE_SECONDS', 2))
DEBUG_MODE = os.environ.get('PISTAT_DEBUG', 'False').lower() == 'true'

# Initialize Flask app
app = Flask(__name__)

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
    </style>
</head>
<body>
    <h1>Raspberry Pi System Monitor API</h1>
    <p>Welcome to the Raspberry Pi System Monitoring API. This service provides real-time system statistics for your Raspberry Pi.</p>
    
    <h2>Available Endpoints</h2>
    
    <div class="endpoint">
        <h3><code>GET /stats</code></h3>
        <p>Returns comprehensive system statistics including CPU temperature, CPU usage, memory usage, disk usage, uptime, and load averages.</p>
        
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
    
    <h2>Usage Examples</h2>
    
    <h3>Using curl</h3>
    <pre>curl http://YOUR_PI_IP:8585/stats</pre>
    
    <h3>Using Python</h3>
    <pre>
import requests
response = requests.get('http://YOUR_PI_IP:8585/stats')
data = response.json()
print(f"CPU Temperature: {data['cpu_temp']}°C")
print(f"CPU Usage: {data['cpu_usage']}%")
    </pre>
    
    <h2>Notes</h2>
    <ul>
        <li>All temperature values are in Celsius</li>
        <li>Memory and disk values are in bytes</li>
        <li>CPU frequency is in MHz</li>
        <li>Clock values are in Hz</li>
        <li>Uptime is in seconds</li>
        <li>Timestamp is Unix time (seconds since epoch)</li>
    </ul>
    
    <p>For more information, visit the <a href="https://github.com/AwaleSagar/piStat">GitHub repository</a>.</p>
</body>
</html>
"""

# Global cache variables
last_stats = None
last_stats_time = 0

def run_command(command, args=None):
    """
    Execute a shell command and return its output.
    
    Args:
        command (str): The command to execute
        args (list, optional): List of arguments for the command
    
    Returns:
        str: Command output or None if execution failed
    """
    try:
        if args:
            # Safer execution without shell=True
            result = subprocess.run([command] + args, shell=False, check=True, text=True, capture_output=True)
        else:
            # Some commands might still need shell=True, but we're careful about inputs
            result = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.warning(f"Command failed: {command} {args if args else ''}, return code: {e.returncode}")
        return None
    except Exception as e:
        logger.error(f"Error executing command '{command}': {str(e)}")
        return None

def get_gpu_info():
    """
    Get GPU information from vcgencmd.
    
    Returns:
        dict: Dictionary containing GPU metrics or empty dict if unavailable
    """
    gpu_info = {}
    
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
        return jsonify({
            'status': 'healthy',
            'uptime': uptime
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    """
    Endpoint to retrieve real-time Raspberry Pi system statistics.
    Returns a JSON object with CPU, memory, disk, and other system metrics.
    
    Query Parameters:
        block (bool): Whether to block for CPU measurements (default: false)
        cache (bool): Whether to use cached results if available (default: true)
    
    Returns:
        JSON: System statistics
    """
    global last_stats, last_stats_time
    
    # Parse query parameters
    block = request.args.get('block', 'false').lower() == 'true'
    use_cache = request.args.get('cache', 'true').lower() == 'true'
    
    current_time = time.time()
    
    # Return cached stats if they're recent enough and caching is enabled
    if use_cache and last_stats and current_time - last_stats_time < CACHE_SECONDS:
        return jsonify(last_stats)
    
    try:
        # Get CPU temperature
        temps = psutil.sensors_temperatures()
        cpu_temp = None
        if 'cpu_thermal' in temps:
            cpu_temp = temps['cpu_thermal'][0].current  # Temperature in Celsius

        # Get CPU frequency (in MHz)
        cpu_freq_info = psutil.cpu_freq()
        cpu_freq = cpu_freq_info.current if cpu_freq_info else None

        # Get CPU usage percentage
        cpu_usage, per_cpu_usage = get_cpu_usage(block=block)

        # Get memory usage
        memory = psutil.virtual_memory()

        # Get disk usage for the root filesystem
        disk = psutil.disk_usage('/')

        # Get system uptime (in seconds)
        uptime = time.time() - psutil.boot_time()

        # Get load averages (1, 5, 15 minutes)
        load_avg = list(psutil.getloadavg())

        # Compile all stats into a dictionary
        stats = {
            'cpu_temp': cpu_temp,
            'cpu_freq': cpu_freq,
            'cpu_usage': cpu_usage,
            'per_cpu_usage': per_cpu_usage,
            'memory': {
                'total': memory.total,      # Total memory in bytes
                'available': memory.available,  # Available memory in bytes
                'used': memory.used,        # Used memory in bytes
                'percent': memory.percent   # Percentage used
            },
            'swap': get_swap_info(),
            'disk': {
                'total': disk.total,        # Total disk space in bytes
                'used': disk.used,          # Used disk space in bytes
                'free': disk.free,          # Free disk space in bytes
                'percent': disk.percent     # Percentage used
            },
            'disk_io': get_disk_io(),
            'uptime': uptime,
            'load_avg': load_avg,
            'timestamp': current_time,      # Time of data collection
            
            # New metrics
            'gpu': get_gpu_info(),
            'power': get_power_info(),
            'clocks': get_clock_info(),
            'network': get_network_details(),
            'hardware': get_hardware_info()
        }

        # Update cache
        last_stats = stats
        last_stats_time = current_time
        
        # Return stats as JSON
        return jsonify(stats)
    
    except Exception as e:
        logger.error(f"Error collecting system stats: {str(e)}")
        return jsonify({
            'error': 'Failed to collect system statistics',
            'details': str(e)
        }), 500

# Run the Flask app
if __name__ == '__main__':
    logger.info(f"Starting Pi System Monitor on {HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=DEBUG_MODE) 