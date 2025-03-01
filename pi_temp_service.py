from flask import Flask, jsonify, render_template_string
import psutil
import time

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
        <li>Uptime is in seconds</li>
        <li>Timestamp is Unix time (seconds since epoch)</li>
    </ul>
    
    <p>For more information, visit the <a href="https://github.com/yourusername/piStat">GitHub repository</a>.</p>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def index():
    """
    Root endpoint that displays a simple webpage explaining the API usage.
    """
    return render_template_string(HTML_TEMPLATE)

@app.route('/stats', methods=['GET'])
def get_stats():
    """
    Endpoint to retrieve real-time Raspberry Pi system statistics.
    Returns a JSON object with CPU, memory, disk, and other system metrics.
    """
    # Get CPU temperature
    temps = psutil.sensors_temperatures()
    cpu_temp = None
    if 'cpu_thermal' in temps:
        cpu_temp = temps['cpu_thermal'][0].current  # Temperature in Celsius

    # Get CPU frequency (in MHz)
    cpu_freq = psutil.cpu_freq().current

    # Get CPU usage percentage (blocks for 1 second for accuracy)
    cpu_usage = psutil.cpu_percent(interval=1)

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
        'memory': {
            'total': memory.total,      # Total memory in bytes
            'available': memory.available,  # Available memory in bytes
            'used': memory.used,        # Used memory in bytes
            'percent': memory.percent   # Percentage used
        },
        'disk': {
            'total': disk.total,        # Total disk space in bytes
            'used': disk.used,          # Used disk space in bytes
            'free': disk.free,          # Free disk space in bytes
            'percent': disk.percent     # Percentage used
        },
        'uptime': uptime,
        'load_avg': load_avg,
        'timestamp': time.time()        # Time of data collection
    }

    # Return stats as JSON
    return jsonify(stats)

# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8585)