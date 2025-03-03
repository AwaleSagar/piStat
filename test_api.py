#!/usr/bin/env python3
"""
Raspberry Pi System Monitor API Test Script

This script tests the Raspberry Pi System Monitor API by connecting to the
specified host and port and verifying that all endpoints are working correctly.
"""

import requests
import json
import socket
import time
import argparse
import sys
import os
from tabulate import tabulate
from datetime import datetime
import logging
import concurrent.futures

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('test_api')

def get_local_ip():
    """Get the local IP address of the device"""
    try:
        # Create a socket connection to determine the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"

def save_response_to_file(endpoint, data, output_dir):
    """Save API response to file for analysis"""
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        filename = f"{endpoint.replace('/', '_')}.json"
        if endpoint == '/':
            filename = "root.html"
            
        filepath = os.path.join(output_dir, filename)
        
        if isinstance(data, str):
            # For HTML content
            with open(filepath, 'w', encoding='utf-8') as file:
                file.write(data)
        else:
            # For JSON content
            with open(filepath, 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=2)
                
        logger.info(f"Saved response from {endpoint} to {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Failed to save response: {str(e)}")
        return None

def test_api_endpoint(endpoint, host, port, expect_json=True, save_output=False, output_dir="./api_responses", timeout=5):
    """Test an API endpoint"""
    url = f"http://{host}:{port}{endpoint}"
    
    print(f"Testing API endpoint: {url}")
    start_time = time.time()
    
    try:
        response = requests.get(url, timeout=timeout)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            if expect_json:
                try:
                    data = response.json()
                    print("\nAPI Response:")
                    print(json.dumps(data, indent=2))
                    
                    # Save response to file if requested
                    if save_output:
                        save_response_to_file(endpoint, data, output_dir)
                except json.JSONDecodeError:
                    print("\nError: Expected JSON response but received non-JSON data.")
                    print("Response preview:", response.text[:100] + "...")
                    return False, "JSON Decode Error", time.time() - start_time
            else:
                print("\nReceived HTML response (first 100 characters):")
                print(response.text[:100] + "...")
                
                # Save response to file if requested
                if save_output:
                    save_response_to_file(endpoint, response.text, output_dir)
                
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
    except requests.exceptions.Timeout:
        print(f"\nError: Request timed out after {timeout} seconds.")
        return False, "Timeout", time.time() - start_time
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

def test_root_endpoint(host, port, save_output=False, output_dir="./api_responses"):
    """Test the root endpoint which returns HTML documentation"""
    print("Testing root endpoint (/)...")
    return test_api_endpoint("/", host, port, expect_json=False, save_output=save_output, output_dir=output_dir)

def test_stats_endpoint(host, port, save_output=False, output_dir="./api_responses", params=None):
    """Test the stats endpoint which returns system statistics"""
    print("Testing stats endpoint (/stats)...")
    
    url_suffix = ""
    if params:
        param_strings = [f"{key}={value}" for key, value in params.items()]
        url_suffix = "?" + "&".join(param_strings)
    
    return test_api_endpoint(f"/stats{url_suffix}", host, port, expect_json=True, 
                            save_output=save_output, output_dir=output_dir)

def test_health_endpoint(host, port, save_output=False, output_dir="./api_responses"):
    """Test the health endpoint which returns service health status"""
    print("Testing health endpoint (/health)...")
    return test_api_endpoint("/health", host, port, expect_json=True, 
                            save_output=save_output, output_dir=output_dir)

def test_processes_endpoint(host, port, save_output=False, output_dir="./api_responses", params=None):
    """Test the processes endpoint which returns process information"""
    print("Testing processes endpoint (/processes)...")
    
    url_suffix = ""
    if params:
        param_strings = [f"{key}={value}" for key, value in params.items()]
        url_suffix = "?" + "&".join(param_strings)
    
    return test_api_endpoint(f"/processes{url_suffix}", host, port, expect_json=True, 
                            save_output=save_output, output_dir=output_dir)

def test_network_endpoint(host, port, save_output=False, output_dir="./api_responses"):
    """Test the network interfaces endpoint"""
    print("Testing network interfaces endpoint (/network/interfaces)...")
    return test_api_endpoint("/network/interfaces", host, port, expect_json=True, 
                            save_output=save_output, output_dir=output_dir)

def test_storage_endpoint(host, port, save_output=False, output_dir="./api_responses"):
    """Test the storage devices endpoint"""
    print("Testing storage devices endpoint (/storage/devices)...")
    return test_api_endpoint("/storage/devices", host, port, expect_json=True, 
                            save_output=save_output, output_dir=output_dir)

def run_load_test(host, port, endpoint, requests_count, concurrency):
    """Run a simple load test on an endpoint"""
    print(f"Running load test on {endpoint} with {requests_count} requests ({concurrency} concurrent)...")
    print("Note: If rate limiting is enabled on the server, this test may be affected.")
    
    url = f"http://{host}:{port}{endpoint}"
    results = {
        'success': 0,
        'failed': 0,
        'total_time': 0,
        'min_time': float('inf'),
        'max_time': 0,
        'rate_limited': 0,  # Counter for rate limited responses
    }
    
    def single_request():
        try:
            start_time = time.time()
            response = requests.get(url, timeout=10)
            elapsed = time.time() - start_time
            
            is_rate_limited = response.status_code == 429
            
            return {
                'success': response.status_code == 200,
                'status_code': response.status_code,
                'time': elapsed,
                'rate_limited': is_rate_limited
            }
        except Exception as e:
            return {
                'success': False,
                'status_code': str(e)[:30],
                'time': time.time() - start_time,
                'rate_limited': False
            }
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(single_request) for _ in range(requests_count)]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            
            if result['success']:
                results['success'] += 1
            else:
                results['failed'] += 1
                
            if result.get('rate_limited', False):
                results['rate_limited'] += 1
                
            results['total_time'] += result['time']
            results['min_time'] = min(results['min_time'], result['time'])
            results['max_time'] = max(results['max_time'], result['time'])
    
    results['avg_time'] = results['total_time'] / requests_count if requests_count > 0 else 0
    
    print("\nLoad Test Results:")
    print(f"Endpoint: {endpoint}")
    print(f"Total Requests: {requests_count}")
    print(f"Concurrency: {concurrency}")
    print(f"Successful: {results['success']} ({results['success']/requests_count*100:.1f}%)")
    print(f"Failed: {results['failed']}")
    if results['rate_limited'] > 0:
        print(f"Rate Limited: {results['rate_limited']} ({results['rate_limited']/requests_count*100:.1f}%)")
    print(f"Average Response Time: {results['avg_time']:.4f}s")
    print(f"Min Response Time: {results['min_time']:.4f}s")
    print(f"Max Response Time: {results['max_time']:.4f}s")
    print(f"Requests Per Second: {requests_count/results['total_time']:.1f}")
    
    return results

def test_all_endpoints(host, port, table_format, save_output=False, output_dir="./api_responses"):
    """Test all available API endpoints"""
    results = []
    all_passed = True
    
    print(f"Testing Raspberry Pi System Monitor API at {host}:{port}...\n")
    print("Note: Tests may be affected by rate limiting if enabled on the server.\n")
    
    # Test root endpoint
    print(f"{'=' * 50}")
    print("Testing root endpoint (HTML documentation)")
    success, status, response_time = test_root_endpoint(host, port, save_output, output_dir)
    results.append(["/", "HTML Documentation", success, status, f"{response_time:.4f}s"])
    all_passed = all_passed and success
    print(f"{'=' * 50}\n")
    
    time.sleep(1)  # Small delay between requests
    
    # Test stats endpoint
    print(f"{'=' * 50}")
    print("Testing stats endpoint (JSON data)")
    success, status, response_time = test_stats_endpoint(host, port, save_output, output_dir)
    results.append(["/stats", "System Statistics", success, status, f"{response_time:.4f}s"])
    all_passed = all_passed and success
    print(f"{'=' * 50}\n")
    
    # Test stats endpoint with parameters
    print(f"{'=' * 50}")
    print("Testing stats endpoint with parameters")
    params = {'fields': 'cpu_usage,memory,uptime', 'block': 'true'}
    success, status, response_time = test_stats_endpoint(host, port, save_output, output_dir, params)
    results.append(["/stats (filtered)", "CPU, Memory & Uptime", success, status, f"{response_time:.4f}s"])
    all_passed = all_passed and success
    print(f"{'=' * 50}\n")
    
    # Test health endpoint
    print(f"{'=' * 50}")
    print("Testing health endpoint")
    success, status, response_time = test_health_endpoint(host, port, save_output, output_dir)
    results.append(["/health", "Service Health", success, status, f"{response_time:.4f}s"])
    all_passed = all_passed and success
    print(f"{'=' * 50}\n")
    
    # Test processes endpoint
    print(f"{'=' * 50}")
    print("Testing processes endpoint")
    success, status, response_time = test_processes_endpoint(host, port, save_output, output_dir)
    results.append(["/processes", "Process Information", success, status, f"{response_time:.4f}s"])
    all_passed = all_passed and success
    print(f"{'=' * 50}\n")
    
    # Test network endpoint
    print(f"{'=' * 50}")
    print("Testing network interfaces endpoint")
    success, status, response_time = test_network_endpoint(host, port, save_output, output_dir)
    results.append(["/network/interfaces", "Network Information", success, status, f"{response_time:.4f}s"])
    all_passed = all_passed and success
    print(f"{'=' * 50}\n")
    
    # Test storage endpoint
    print(f"{'=' * 50}")
    print("Testing storage devices endpoint")
    success, status, response_time = test_storage_endpoint(host, port, save_output, output_dir)
    results.append(["/storage/devices", "Storage Information", success, status, f"{response_time:.4f}s"])
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
    
    print(tabulate(table_data, headers=headers, tablefmt=table_format))
    print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: {host}:{port}")
    print(f"Overall result: {'PASSED' if all_passed else 'FAILED'}")
    
    return all_passed

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Test the Raspberry Pi System Monitor API',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument('-H', '--host', 
                        help='Host address of the API (default: auto-detect local IP)',
                        default=None)
    
    parser.add_argument('-p', '--port', 
                        help='Port number of the API',
                        type=int,
                        default=8585)
    
    parser.add_argument('-f', '--format',
                        help='Table format for results',
                        choices=['plain', 'simple', 'github', 'grid', 'fancy_grid', 'pipe', 'orgtbl', 'jira'],
                        default='grid')
    
    parser.add_argument('-e', '--endpoint',
                        help='Test a specific endpoint',
                        choices=['root', 'stats', 'health', 'processes', 'network', 'storage', 'all'],
                        default='all')
    
    parser.add_argument('-s', '--save',
                        help='Save API responses to files for analysis',
                        action='store_true',
                        default=False)
    
    parser.add_argument('-o', '--output-dir',
                        help='Directory to save API responses',
                        default='./api_responses')
    
    parser.add_argument('-v', '--verbose',
                        help='Enable verbose logging',
                        action='store_true',
                        default=False)
    
    parser.add_argument('-t', '--timeout',
                        help='Request timeout in seconds',
                        type=int,
                        default=5)
    
    parser.add_argument('--load-test',
                        help='Run a load test on the specified endpoint',
                        action='store_true',
                        default=False)
                        
    parser.add_argument('--requests',
                        help='Number of requests to send during load test',
                        type=int,
                        default=100)
                        
    parser.add_argument('--concurrency',
                        help='Number of concurrent requests during load test',
                        type=int,
                        default=10)
    
    parser.add_argument('--bypass-rate-limit',
                       help='Add a delay between requests to avoid rate limiting',
                       action='store_true',
                       default=False)
    
    parser.add_argument('--delay',
                       help='Delay between requests in seconds (used with --bypass-rate-limit)',
                       type=float,
                       default=1.0)
    
    return parser.parse_args()

def main():
    """Main function"""
    args = parse_arguments()
    
    # If host is not specified, try to auto-detect
    host = args.host if args.host else get_local_ip()
    port = args.port
    
    # Set log level based on verbose flag
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    print(f"Target API: {host}:{port}")
    
    # Add warning about rate limiting
    print("Note: The API may have rate limiting enabled. If tests fail unexpectedly,")
    print("      try using --bypass-rate-limit to add delays between requests.\n")
    
    # Run load test if requested
    if args.load_test:
        if args.endpoint == 'all':
            endpoint = '/stats'  # Default endpoint for load testing
            print("No specific endpoint provided for load test, using /stats")
        else:
            endpoint_mapping = {
                'root': '/',
                'stats': '/stats',
                'health': '/health',
                'processes': '/processes',
                'network': '/network/interfaces',
                'storage': '/storage/devices'
            }
            endpoint = endpoint_mapping.get(args.endpoint, '/stats')
        
        run_load_test(host, port, endpoint, args.requests, args.concurrency)
        return 0
    
    # Test specific endpoint or all endpoints
    if args.endpoint == 'all':
        success = test_all_endpoints(host, port, args.format, args.save, args.output_dir)
    else:
        # Map endpoint choice to test function
        endpoint_tests = {
            'root': lambda: test_root_endpoint(host, port, args.save, args.output_dir),
            'stats': lambda: test_stats_endpoint(host, port, args.save, args.output_dir),
            'health': lambda: test_health_endpoint(host, port, args.save, args.output_dir),
            'processes': lambda: test_processes_endpoint(host, port, args.save, args.output_dir),
            'network': lambda: test_network_endpoint(host, port, args.save, args.output_dir),
            'storage': lambda: test_storage_endpoint(host, port, args.save, args.output_dir)
        }
        
        success, status, response_time = endpoint_tests[args.endpoint]()
        print(f"\nTest result: {'PASSED' if success else 'FAILED'}")
        print(f"Status code: {status}")
        print(f"Response time: {response_time:.4f}s")
        
        # Add check for rate limiting
        if status == 429:
            print("\nWARNING: Received a 429 status code (Too Many Requests).")
            print("The API's rate limiting is restricting your requests.")
            print("Try again with the --bypass-rate-limit option.")
    
    # Exit with appropriate status code
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())