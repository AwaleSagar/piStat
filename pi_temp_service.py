#!/usr/bin/env python3

import os
import time
import subprocess
import psutil
from datetime import datetime, timedelta
from flask import Flask, jsonify, request

app = Flask(__name__)

def get_cpu_temperature():
    """
    Get the CPU temperature of the Raspberry Pi
    Returns temperature as a float in Celsius
    """
    try:
        # Read the temperature from the thermal zone
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp = float(f.read()) / 1000.0
        return temp
    except Exception as e:
        print(f"Error reading temperature: {e}")
        return None

def get_cpu_usage():
    """
    Get the CPU usage percentage
    """
    return psutil.cpu_percent(interval=1)

def get_memory_info():
    """
    Get memory usage information
    """
    memory = psutil.virtual_memory()
    return {
        'total': round(memory.total / (1024 * 1024), 2),  # MB
        'available': round(memory.available / (1024 * 1024), 2),  # MB
        'used': round(memory.used / (1024 * 1024), 2),  # MB
        'percent': memory.percent
    }

def get_disk_info():
    """
    Get disk usage information
    """
    disk = psutil.disk_usage('/')
    return {
        'total': round(disk.total / (1024 * 1024 * 1024), 2),  # GB
        'used': round(disk.used / (1024 * 1024 * 1024), 2),  # GB
        'free': round(disk.free / (1024 * 1024 * 1024), 2),  # GB
        'percent': disk.percent
    }

def get_uptime():
    """
    Get system uptime
    """
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
        
        uptime = str(timedelta(seconds=uptime_seconds))
        return uptime
    except Exception as e:
        print(f"Error reading uptime: {e}")
        return None

def get_network_info():
    """
    Get network information
    """
    try:
        # Get network stats
        net_io = psutil.net_io_counters()
        return {
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv,
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv
        }
    except Exception as e:
        print(f"Error getting network info: {e}")
        return None

@app.route('/temp', methods=['GET'])
def get_temperature():
    """
    API endpoint that returns the current CPU temperature
    """
    temp = get_cpu_temperature()
    if temp is not None:
        return jsonify({
            'temperature': temp,
            'unit': 'Celsius',
            'timestamp': time.time()
        })
    else:
        return jsonify({
            'error': 'Unable to read temperature'
        }), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    """
    API endpoint that returns comprehensive system statistics
    """
    try:
        stats = {
            'temperature': get_cpu_temperature(),
            'cpu_usage': get_cpu_usage(),
            'memory': get_memory_info(),
            'disk': get_disk_info(),
            'uptime': get_uptime(),
            'network': get_network_info(),
            'timestamp': time.time()
        }
        return jsonify(stats)
    except Exception as e:
        return jsonify({
            'error': f'Error getting system stats: {str(e)}'
        }), 500

@app.route('/', methods=['GET'])
def index():
    """
    API root endpoint that returns available endpoints
    """
    return jsonify({
        'available_endpoints': {
            '/temp': 'Get CPU temperature',
            '/stats': 'Get comprehensive system statistics'
        }
    })

if __name__ == '__main__':
    # Run the Flask app on port 8585
    app.run(host='0.0.0.0', port=8585) 