#!/usr/bin/env python3

import subprocess
import sys
import os
import time
import re
import socket
from datetime import datetime
import shutil
import pexpect

# Default Configuration (can be changed via menu)
DEFAULT_NETWORK = {"ENTER YOUR IP/16"}
DEFAULT_PORT = "22"
RATE = "1000"
OUTPUT_FILE = "wifi_scan_results.txt"
MASSACAN_OUTPUT = "masscan_results.txt"
PASSWORD = {"YOUR PASSWORD"}
USERNAME = {"YOUR USERNAME"}
MAX_TIMEOUT = 30

# ANSI Colors
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    WHITE = '\033[1;37m'
    MAGENTA = '\033[0;35m'
    GRAY = '\033[0;90m'
    NC = '\033[0m'

def print_status(msg):
    print(f"{Colors.GREEN}[+]{Colors.NC} {msg}")

def print_error(msg):
    print(f"{Colors.RED}[!]{Colors.NC} {msg}")

def print_warning(msg):
    print(f"{Colors.YELLOW}[*]{Colors.NC} {msg}")

def print_info(msg):
    print(f"{Colors.BLUE}[i]{Colors.NC} {msg}")

def print_debug(msg):
    print(f"{Colors.GRAY}[DEBUG]{Colors.NC} {msg}")

def print_prompt(msg):
    print(f"{Colors.MAGENTA}[PROMPT]{Colors.NC} {msg}")

def print_success(msg):
    print(f"{Colors.GREEN}[✓]{Colors.NC} {msg}")

def print_fail(msg):
    print(f"{Colors.RED}[✗]{Colors.NC} {msg}")

def check_root():
    if os.geteuid() != 0:
        print_error("This script must be run with sudo privileges!")
        print_info("Please run: sudo python3 masscan-ssh.py")
        sys.exit(1)

def check_tools():
    """Check if required tools are installed"""
    tools = ['masscan']
    missing = []
    for tool in tools:
        if shutil.which(tool) is None:
            missing.append(tool)
    if missing:
        print_error(f"Missing required tools: {', '.join(missing)}")
        print_info("Install with: sudo apt-get install masscan python3-pexpect")
        return False
    
    # Check pexpect
    try:
        import pexpect
    except ImportError:
        print_error("Python pexpect module not installed")
        print_info("Install with: sudo apt-get install python3-pexpect")
        return False
    
    return True

def test_port(ip, port=22):
    """Test if port is open on IP"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((ip, int(port)))
        sock.close()
        return result == 0
    except:
        return False

def run_masscan(network, port, rate=RATE):
    """Run masscan and return list of IPs"""
    print_status(f"Starting masscan scan on {network}:{port} at rate {rate}...")
    print_warning("This may take a while depending on network size...")
    
    try:
        cmd = ['masscan', network, f'-p{port}', f'--rate={rate}', '-oL', MASSACAN_OUTPUT]
        print_debug(f"Running: {' '.join(cmd)}")
        
        start_time = time.time()
        subprocess.run(cmd, capture_output=True, text=True)
        elapsed = time.time() - start_time
        
        print_debug(f"Masscan completed in {elapsed:.1f}s")
        
        if not os.path.exists(MASSACAN_OUTPUT):
            print_error("Masscan failed to create output file")
            return []
        
        # Parse results
        ips = []
        with open(MASSACAN_OUTPUT, 'r') as f:
            for line in f:
                if 'open' in line and 'tcp' in line:
                    parts = line.strip().split()
                    if len(parts) >= 4:
                        ip = parts[3]
                        if ip not in ips:
                            ips.append(ip)
        
        ips.sort()
        print_status(f"Found {len(ips)} hosts with port {port} open")
        return ips
        
    except Exception as e:
        print_error(f"Error running masscan: {e}")
        return []

def try_ssh_connection(ip, port=22, timeout=MAX_TIMEOUT, show_debug=False):
    """
    SSH into device and get WiFi information
    If command doesn't work, immediately move to next IP
    Returns (success, output)
    """
    
    if show_debug:
        print_debug(f"Starting SSH to {ip}:{port}")
    
    # Build SSH command with custom port if needed
    if port and port != 22:
        ssh_cmd = f'ssh -o HostKeyAlgorithms=+ssh-rsa -p {port} {ip}'
    else:
        ssh_cmd = f'ssh -o HostKeyAlgorithms=+ssh-rsa {ip}'
    
    if show_debug:
        print_debug(f"Command: {ssh_cmd}")
    
    try:
        # Start SSH process
        child = pexpect.spawn(ssh_cmd, timeout=timeout, encoding='utf-8')
        
        wifi_success = False
        output_lines = []
        wap_count = 0
        
        while True:
            try:
                # Wait for any prompt
                index = child.expect([
                    r'\(yes/no(/\[fingerprint\])?\)',  # 0: Host key
                    r'password:',                       # 1: Password prompt
                    r'Login:',                          # 2: Login prompt
                    r'Password:',                       # 3: Password after login
                    r'User name or password is wrong',  # 4: Auth failed
                    r'Permission denied',               # 5: Auth denied
                    r'WAP>',                            # 6: WAP prompt
                    r'success!',                        # 7: Success
                    r'Configuration console exit',      # 8: Exit
                    r'Connection refused',              # 9: Connection refused
                    r'Connection timed out',            # 10: Connection timeout
                    r'No route to host',                # 11: No route
                    pexpect.TIMEOUT,                    # 12: Timeout
                    pexpect.EOF                         # 13: End of file
                ], timeout=10)
                
                # Store received text
                if child.before:
                    text = child.before.strip()
                    if text:
                        output_lines.append(text)
                
                # Handle each case
                if index == 0:  # Host key verification
                    if show_debug:
                        print_prompt("Host key verification - sending 'yes'")
                    child.sendline('yes')
                    
                elif index == 1:  # password:
                    if show_debug:
                        print_prompt("Password prompt - sending password")
                    child.sendline(PASSWORD)
                    
                elif index == 2:  # Login:
                    if show_debug:
                        print_prompt(f"Login prompt - sending '{USERNAME}'")
                    child.sendline(USERNAME)
                    
                elif index == 3:  # Password:
                    if show_debug:
                        print_prompt("Password prompt - sending password")
                    child.sendline(PASSWORD)
                    
                elif index in [4, 5]:  # Auth failed
                    if show_debug:
                        print_error("Authentication failed - moving to next IP")
                    child.close()
                    return False, "AUTH_FAILED"
                    
                elif index == 6:  # WAP>
                    wap_count += 1
                    
                    if wap_count == 1:
                        # First time - try the command
                        if show_debug:
                            print_prompt("WAP> - sending 'display wifi information'")
                        child.sendline('display wifi information')
                    
                    elif wap_count == 2:
                        # Check if we got WiFi info
                        full_output = '\n'.join(output_lines)
                        if 'SSID' in full_output or 'BSSID' in full_output:
                            if show_debug:
                                print_debug("WiFi info found - sending 'quit'")
                            child.sendline('quit')
                        else:
                            if show_debug:
                                print_warning("No WiFi info - sending 'quit' and moving on")
                            child.sendline('quit')
                    
                    elif wap_count >= 3:
                        if show_debug:
                            print_warning("Max attempts reached - quitting")
                        child.sendline('quit')
                        full_output = '\n'.join(output_lines)
                        child.close()
                        if 'SSID' in full_output or 'BSSID' in full_output:
                            return True, full_output
                        else:
                            return False, "NO_WIFI_INFO"
                    
                elif index == 7:  # success!
                    wifi_success = True
                    if show_debug:
                        print_status("Command successful!")
                    
                elif index == 8:  # Configuration console exit
                    if show_debug:
                        print_status("Configuration console exit")
                    child.close()
                    full_output = '\n'.join(output_lines)
                    if 'SSID' in full_output or 'BSSID' in full_output or wifi_success:
                        return True, full_output
                    else:
                        return False, "NO_WIFI_INFO"
                    
                elif index in [9, 10, 11]:  # Connection issues
                    if show_debug:
                        print_error("Connection failed - moving to next IP")
                    child.close()
                    return False, "CONNECTION_FAILED"
                    
                elif index == 12:  # TIMEOUT
                    if show_debug:
                        print_error("Timeout - moving to next IP")
                    child.close()
                    full_output = '\n'.join(output_lines)
                    if 'SSID' in full_output or 'BSSID' in full_output:
                        return True, full_output
                    return False, "TIMEOUT"
                    
                elif index == 13:  # EOF
                    child.close()
                    full_output = '\n'.join(output_lines)
                    if 'SSID' in full_output or 'BSSID' in full_output or wifi_success:
                        return True, full_output
                    else:
                        return False, "CONNECTION_CLOSED"
                
            except pexpect.TIMEOUT:
                child.close()
                full_output = '\n'.join(output_lines)
                if 'SSID' in full_output or 'BSSID' in full_output:
                    return True, full_output
                return False, "TIMEOUT"
                
    except Exception as e:
        return False, f"ERROR: {str(e)}"

def extract_wifi_info(output):
    """Extract WiFi information from command output"""
    info = {}
    
    # Extract SSID
    ssid_match = re.search(r'SSID\s+:(\S.+)', output)
    if ssid_match:
        info['SSID'] = ssid_match.group(1).strip()
    
    # Extract BSSID
    bssid_match = re.search(r'BSSID\s+:(\S+)', output)
    if bssid_match:
        info['BSSID'] = bssid_match.group(1).strip()
    
    # Extract Channel
    channel_match = re.search(r'Channel\s+:(\S+)', output)
    if channel_match:
        info['Channel'] = channel_match.group(1).strip()
    
    # Extract Authentication
    auth_match = re.search(r'Authentication Mode\s+:(\S.+)', output)
    if auth_match:
        info['Authentication'] = auth_match.group(1).strip()
    
    # Extract Encryption
    enc_match = re.search(r'Encryption Mode\s+:(\S.+)', output)
    if enc_match:
        info['Encryption'] = enc_match.group(1).strip()
    
    return info

def process_single_ip(idx, ip, total, port=22, show_debug=False):
    """Process a single IP address - fast fail if command doesn't work"""
    
    if show_debug:
        print(f"\n{Colors.CYAN}{'─'*60}{Colors.NC}")
        print_status(f"[{idx}/{total}] Processing {ip}:{port}...")
    
    # Quick port test
    if not test_port(ip, port):
        if show_debug:
            print_fail(f"[{idx}/{total}] {ip}:{port} - PORT CLOSED - skipping")
        return {
            'ip': ip,
            'port': port,
            'success': False,
            'output': 'PORT_CLOSED',
            'elapsed': 0,
            'wifi_info': {}
        }
    
    start_time = time.time()
    
    # Try SSH connection
    success, output = try_ssh_connection(ip, port, show_debug=show_debug)
    elapsed = time.time() - start_time
    
    # Extract WiFi info if successful
    wifi_info = {}
    if success:
        wifi_info = extract_wifi_info(output)
    
    result = {
        'ip': ip,
        'port': port,
        'success': success,
        'output': output,
        'elapsed': elapsed,
        'wifi_info': wifi_info
    }
    
    # Display result
    if show_debug:
        if success:
            print_success(f"[{idx}/{total}] {ip}:{port} - SUCCESS ({elapsed:.1f}s)")
            if wifi_info.get('SSID'):
                print(f"    {Colors.GREEN}SSID: {wifi_info['SSID']}{Colors.NC}")
        else:
            reason = str(output)
            if 'AUTH_FAILED' in reason:
                print_fail(f"[{idx}/{total}] {ip}:{port} - AUTH FAILED - skipping")
            elif 'NO_WIFI_INFO' in reason:
                print_fail(f"[{idx}/{total}] {ip}:{port} - NO WIFI INFO - skipping")
            elif 'TIMEOUT' in reason:
                print_fail(f"[{idx}/{total}] {ip}:{port} - TIMEOUT - skipping")
            else:
                print_fail(f"[{idx}/{total}] {ip}:{port} - FAILED - skipping")
    
    return result

def test_single_ip(ip, port=22):
    """Test a single IP with full debug output"""
    print(f"\n{Colors.CYAN}{'='*60}{Colors.NC}")
    print(f"{Colors.WHITE}TESTING: {ip}:{port}{Colors.NC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.NC}")
    
    # Test port
    if not test_port(ip, port):
        print_error(f"Port {port} is CLOSED on {ip}")
        return
    print_status(f"Port {port} is OPEN on {ip}")
    
    # Test connection
    print(f"\n{Colors.YELLOW}Starting SSH connection...{Colors.NC}")
    print_info(f"Command: ssh -o HostKeyAlgorithms=+ssh-rsa -p {port} {ip}")
    print(f"{Colors.CYAN}{'─'*60}{Colors.NC}\n")
    
    result = process_single_ip(1, ip, 1, port, show_debug=True)
    
    # Show results
    print(f"\n{Colors.CYAN}{'='*60}{Colors.NC}")
    if result['success']:
        print_status("SUCCESS!")
        if result['wifi_info']:
            print(f"\n{Colors.GREEN}WiFi Information:{Colors.NC}")
            for key, value in result['wifi_info'].items():
                print(f"  {Colors.GREEN}{key}: {value}{Colors.NC}")
    else:
        print_error(f"FAILED: {result['output']}")

def run_full_scan(ip_list, port=22):
    """Run full scan on all IPs"""
    total_ips = len(ip_list)
    
    print_status(f"Starting scan of {total_ips} hosts on port {port}...")
    print_info("Will immediately skip IPs that don't return WiFi info")
    print_warning("Press Ctrl+C to skip current host\n")
    
    # Initialize output file
    with open(OUTPUT_FILE, 'w') as f:
        f.write(f"WiFi Scan Results - {datetime.now()}\n")
        f.write(f"Target: {len(ip_list)} hosts on port {port}\n")
        f.write("="*60 + "\n\n")
    
    # Process all IPs
    successful = 0
    failed = 0
    results = []
    
    for idx, ip in enumerate(ip_list, 1):
        try:
            result = process_single_ip(idx, ip, total_ips, port, show_debug=True)
            results.append(result)
            
            # Write to output file
            with open(OUTPUT_FILE, 'a') as f:
                f.write(f"--- {ip}:{port} ---\n")
                f.write(f"Time: {result['elapsed']:.1f}s\n")
                f.write(f"Success: {result['success']}\n")
                if result['wifi_info']:
                    for key, value in result['wifi_info'].items():
                        f.write(f"{key}: {value}\n")
                f.write(f"\nOutput:\n{result['output']}\n")
                f.write("\n")
            
            if result['success']:
                successful += 1
            else:
                failed += 1
                
        except KeyboardInterrupt:
            print_warning(f"Skipped {ip} - moving to next...")
            failed += 1
            continue
    
    # Cleanup
    if os.path.exists(MASSACAN_OUTPUT):
        os.remove(MASSACAN_OUTPUT)
    
    # Final summary
    print(f"\n{Colors.CYAN}{'='*60}{Colors.NC}")
    print(f"{Colors.WHITE}SCAN COMPLETE{Colors.NC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.NC}")
    print_status(f"Total: {total_ips}")
    print_status(f"Successful: {successful}")
    print_error(f"Failed/Skipped: {failed}")
    print_info(f"Results saved to: {OUTPUT_FILE}")
    
    # Add summary to file
    with open(OUTPUT_FILE, 'a') as f:
        f.write("\n" + "="*60 + "\n")
        f.write("SCAN SUMMARY\n")
        f.write("="*60 + "\n")
        f.write(f"Completed: {datetime.now()}\n")
        f.write(f"Target port: {port}\n")
        f.write(f"Total: {total_ips}\n")
        f.write(f"Successful: {successful}\n")
        f.write(f"Failed: {failed}\n")
    
    # Show found networks
    if successful > 0:
        print(f"\n{Colors.GREEN}Found WiFi Networks:{Colors.NC}")
        print("="*60)
        for result in results:
            if result['success'] and result['wifi_info']:
                wifi = result['wifi_info']
                print(f"\n{Colors.CYAN}IP: {result['ip']}:{result['port']}{Colors.NC}")
                for key, value in wifi.items():
                    print(f"  {Colors.GREEN}{key}: {value}{Colors.NC}")
        
        # Save successful IPs
        with open("successful_ips.txt", 'w') as f:
            for result in results:
                if result['success']:
                    f.write(f"{result['ip']}:{result['port']}\n")
                    if result['wifi_info'].get('SSID'):
                        f.write(f"  SSID: {result['wifi_info']['SSID']}\n")
                    f.write("\n")
        print_info(f"Successful IPs saved to: successful_ips.txt")

def get_scan_config():
    """Get scan configuration from user"""
    print(f"\n{Colors.CYAN}{'='*60}{Colors.NC}")
    print(f"{Colors.WHITE}Scan Configuration{Colors.NC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.NC}")
    
    # Get network/IP range
    print(f"\n{Colors.YELLOW}Enter target network/IP range:{Colors.NC}")
    print(f"{Colors.GRAY}Examples:{Colors.NC}")
    print(f"  {Colors.GRAY}10.70.50.75/16  - Full Class B network{Colors.NC}")
    print(f"  {Colors.GRAY}192.168.1.0/24  - Class C network{Colors.NC}")
    print(f"  {Colors.GRAY}10.70.41.37     - Single IP{Colors.NC}")
    print(f"  {Colors.GRAY}10.70.41.0/24   - Subnet range{Colors.NC}")
    
    network = input(f"\n{Colors.GREEN}Network/IP Range [{DEFAULT_NETWORK}]:{Colors.NC} ").strip()
    if not network:
        network = DEFAULT_NETWORK
    
    # Get port
    print(f"\n{Colors.YELLOW}Enter port to scan:{Colors.NC}")
    print(f"{Colors.GRAY}Examples: 22 (SSH), 23 (Telnet), 2222 (SSH alt){Colors.NC}")
    
    port = input(f"{Colors.GREEN}Port [{DEFAULT_PORT}]:{Colors.NC} ").strip()
    if not port:
        port = DEFAULT_PORT
    
    # Validate port
    try:
        port_num = int(port)
        if port_num < 1 or port_num > 65535:
            print_error("Invalid port number! Using default port 22")
            port = DEFAULT_PORT
    except ValueError:
        print_error("Invalid port! Using default port 22")
        port = DEFAULT_PORT
    
    # Get scan rate
    print(f"\n{Colors.YELLOW}Enter scan rate (packets per second):{Colors.NC}")
    print(f"{Colors.GRAY}Lower = stealthier, Higher = faster (100-10000){Colors.NC}")
    
    rate = input(f"{Colors.GREEN}Rate [{RATE}]:{Colors.NC} ").strip()
    if not rate:
        rate = RATE
    
    print(f"\n{Colors.CYAN}{'='*60}{Colors.NC}")
    print(f"{Colors.WHITE}Configuration Summary:{Colors.NC}")
    print(f"  Target: {network}")
    print(f"  Port: {port}")
    print(f"  Rate: {rate} pps")
    print(f"  Username: {USERNAME}")
    print(f"  Password: {PASSWORD}")
    print(f"{Colors.CYAN}{'='*60}{Colors.NC}")
    
    confirm = input(f"\n{Colors.GREEN}Proceed with scan? (y/n):{Colors.NC} ").strip().lower()
    if confirm != 'y':
        print_warning("Scan cancelled")
        return None, None, None
    
    return network, port, rate

def main():
    """Main function with menu"""
    print(f"\n{Colors.CYAN}{'='*60}{Colors.NC}")
    print(f"{Colors.WHITE}WiFi Scanner - Auto SSH{Colors.NC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.NC}")
    print(f"{Colors.BLUE}Command: ssh -o HostKeyAlgorithms=+ssh-rsa <IP>{Colors.NC}")
    print(f"{Colors.BLUE}Customizable IP range, port, and scan rate{Colors.NC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.NC}\n")
    
    # Check requirements
    check_root()
    if not check_tools():
        sys.exit(1)
    
    while True:
        # Menu
        print(f"\n{Colors.WHITE}Options:{Colors.NC}")
        print("1. Run full scan (custom IP range and port)")
        print("2. Quick scan with defaults (10.70.50.75/16:22)")
        print("3. Test a specific IP and port")
        print("4. Use existing masscan results file")
        print("5. Exit")
        
        choice = input(f"\n{Colors.GREEN}Choose option (1-5):{Colors.NC} ").strip()
        
        if choice == '1':
            # Get custom configuration
            network, port, rate = get_scan_config()
            if network is None:
                continue
            
            # Run masscan
            ip_list = run_masscan(network, port, rate)
            if ip_list:
                run_full_scan(ip_list, port)
            else:
                print_error("No hosts found!")
        
        elif choice == '2':
            # Quick scan with defaults
            print_info(f"Using defaults: {DEFAULT_NETWORK}:{DEFAULT_PORT}")
            ip_list = run_masscan(DEFAULT_NETWORK, DEFAULT_PORT)
            if ip_list:
                run_full_scan(ip_list, DEFAULT_PORT)
            else:
                print_error("No hosts found!")
        
        elif choice == '3':
            # Test specific IP and port
            print(f"\n{Colors.YELLOW}Test Single Host{Colors.NC}")
            test_ip = input(f"{Colors.GREEN}Enter IP address:{Colors.NC} ").strip()
            if not test_ip:
                print_error("IP address required!")
                continue
            
            test_port = input(f"{Colors.GREEN}Enter port [22]:{Colors.NC} ").strip()
            if not test_port:
                test_port = "22"
            
            test_single_ip(test_ip, test_port)
        
        elif choice == '4':
            # Use existing masscan results
            if not os.path.exists(MASSACAN_OUTPUT):
                print_error(f"{MASSACAN_OUTPUT} not found!")
                continue
            
            # Ask for port
            port = input(f"{Colors.GREEN}Enter port to use [22]:{Colors.NC} ").strip()
            if not port:
                port = "22"
            
            print_info(f"Loading results from {MASSACAN_OUTPUT}")
            ips = []
            with open(MASSACAN_OUTPUT, 'r') as f:
                for line in f:
                    if 'open' in line and 'tcp' in line:
                        parts = line.strip().split()
                        if len(parts) >= 4:
                            ips.append(parts[3])
            ip_list = sorted(set(ips))
            
            if ip_list:
                print_status(f"Loaded {len(ip_list)} IPs")
                run_full_scan(ip_list, port)
            else:
                print_error("No IPs found in file!")
        
        elif choice == '5':
            print_info("Exiting...")
            break
        
        else:
            print_error("Invalid option!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}[*]{Colors.NC} Script interrupted")
        sys.exit(0)
