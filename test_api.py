#!/usr/bin/env python3

import requests
import json
import socket
import time
import argparse
import sys
from tabulate import tabulate
from datetime import datetime

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

def test_api_endpoint(endpoint, host, port, expect_json=True):
    """Test an API endpoint"""
    url = f"http://{host}:{port}{endpoint}"
    
    print(f"Testing API endpoint: {url}")
    start_time = time.time()
    
    try:
        response = requests.get(url, timeout=5)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            if expect_json:
                data = response.json()
                print("\nAPI Response:")
                print(json.dumps(data, indent=2))
            else:
                print("\nReceived HTML response (first 100 characters):")
                print(response.text[:100] + "...")
                
            print(f"\nEndpoint {endpoint} is working correctly!")
            return True, response.status_code, response_time
        else:
            print(f"\nError: API returned status code {response.status_code}")
            print(response.text)
            return False, response.status_code, response_time
    except requests.exceptions.ConnectionError:
        print("\nError: Could not connect to the API.")
        print(f"Make sure the service is running at {host}:{port} and is accessible.")
        return False, "Connection Error", time.time() - start_time
    except json.JSONDecodeError:
        if expect_json:
            print("\nError: Expected JSON response but received non-JSON data.")
            print("Response preview:", response.text[:100] + "...")
            return False, "JSON Decode Error", time.time() - start_time
        else:
            print("\nReceived non-JSON response as expected.")
            return True, response.status_code, time.time() - start_time
    except Exception as e:
        print(f"\nError: {e}")
        return False, str(e)[:30], time.time() - start_time

def test_root_endpoint(host, port):
    """Test the root endpoint which returns HTML documentation"""
    print("Testing root endpoint (/)...")
    return test_api_endpoint("/", host, port, expect_json=False)

def test_stats_endpoint(host, port):
    """Test the stats endpoint which returns system statistics"""
    print("Testing stats endpoint (/stats)...")
    return test_api_endpoint("/stats", host, port, expect_json=True)

def test_all_endpoints(host, port):
    """Test all available API endpoints"""
    results = []
    all_passed = True
    
    print(f"Testing API at {host}:{port}...\n")
    
    # Test root endpoint
    print(f"{'=' * 50}")
    print("Testing root endpoint (HTML documentation)")
    success, status, response_time = test_root_endpoint(host, port)
    results.append(["/", "HTML Documentation", success, status, f"{response_time:.4f}s"])
    all_passed = all_passed and success
    print(f"{'=' * 50}\n")
    
    time.sleep(1)  # Small delay between requests
    
    # Test stats endpoint
    print(f"{'=' * 50}")
    print("Testing stats endpoint (JSON data)")
    success, status, response_time = test_stats_endpoint(host, port)
    results.append(["/stats", "System Statistics", success, status, f"{response_time:.4f}s"])
    all_passed = all_passed and success
    print(f"{'=' * 50}\n")
    
    # Print summary as a table
    print("\nTest Summary:")
    headers = ["Endpoint", "Description", "Status", "Response Code", "Response Time"]
    table_data = []
    
    for row in results:
        endpoint, description, success, status, response_time = row
        status_str = "✓ SUCCESS" if success else "✗ FAILED"
        table_data.append([endpoint, description, status_str, status, response_time])
    
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: {host}:{port}")
    print(f"Overall result: {'PASSED' if all_passed else 'FAILED'}")
    
    return all_passed

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Test the Raspberry Pi System Monitoring API')
    
    parser.add_argument('-H', '--host', 
                        help='Host address of the API (default: auto-detect local IP)',
                        default=None)
    
    parser.add_argument('-p', '--port', 
                        help='Port number of the API (default: 8585)',
                        type=int,
                        default=8585)
    
    parser.add_argument('-f', '--format',
                        help='Table format for results (default: grid)',
                        choices=['plain', 'simple', 'github', 'grid', 'fancy_grid', 'pipe', 'orgtbl', 'jira'],
                        default='grid')
    
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    
    # If host is not specified, try to auto-detect
    host = args.host if args.host else get_local_ip()
    port = args.port
    
    print(f"Target API: {host}:{port}")
    
    # Run the tests
    success = test_all_endpoints(host, port)
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1) 