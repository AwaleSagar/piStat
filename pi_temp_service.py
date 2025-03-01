from flask import Flask, jsonify
import psutil
import time

# Initialize Flask app
app = Flask(__name__)

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