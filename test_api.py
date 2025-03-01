#!/usr/bin/env python3

import requests
import json
import socket
import time

def get_local_ip():
    """Get the local IP address of the Raspberry Pi"""
    try:
        # Create a socket connection to determine the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"

def test_api_endpoint(endpoint):
    """Test an API endpoint"""
    ip = get_local_ip()
    url = f"http://{ip}:8585{endpoint}"
    
    print(f"Testing API endpoint: {url}")
    
    try:
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print("\nAPI Response:")
            print(json.dumps(data, indent=2))
            print(f"\nEndpoint {endpoint} is working correctly!")
            return True
        else:
            print(f"\nError: API returned status code {response.status_code}")
            print(response.text)
            return False
    except requests.exceptions.ConnectionError:
        print("\nError: Could not connect to the API.")
        print("Make sure the service is running and the port 8585 is accessible.")
        return False
    except Exception as e:
        print(f"\nError: {e}")
        return False

def test_all_endpoints():
    """Test all available API endpoints"""
    endpoints = ['/', '/temp', '/stats']
    results = {}
    
    print("Testing all API endpoints...\n")
    
    for endpoint in endpoints:
        print(f"{'=' * 50}")
        results[endpoint] = test_api_endpoint(endpoint)
        print(f"{'=' * 50}\n")
        time.sleep(1)  # Small delay between requests
    
    # Print summary
    print("\nTest Summary:")
    for endpoint, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        print(f"{endpoint}: {status}")
    
    return all(results.values())

if __name__ == "__main__":
    test_all_endpoints() 