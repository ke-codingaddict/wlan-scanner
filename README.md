# wlan-scanner
Network scanner that finds SSH-enabled devices and extracts WiFi configuration data.


# Wlan Scanner - Multi-Credential SSH WiFi Info Grabber

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Bash](https://img.shields.io/badge/Bash-4.4+-green.svg)](https://www.gnu.org/software/bash/)
[![Linux](https://img.shields.io/badge/Linux-Tested-blue.svg)](https://www.linux.org/)

A powerful Bash script that scans your network for devices with SSH (port 22), automatically tries multiple credential sets, and retrieves WiFi information from compatible devices.

## 📋 Table of Contents

- [Features](#-features)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Usage Guide](#-usage-guide)
- [How It Works](#-how-it-works)
- [Customizing Credentials](#-customizing-credentials)
- [Troubleshooting](#-troubleshooting)
- [Security Considerations](#-security-considerations)
- [Contributing](#-contributing)
- [License](#-license)

## Features

- **🔍 Network Scanning**: Uses `masscan` to discover all devices with SSH (port 22) on your network
- **🔑 Multiple Credential Sets**: Tries multiple credential combinations automatically
- **🔄 Two-Step Login Handler**: Handles non-standard SSH login flows:
  - First Password: SSH password
  - Login: Username
  - Password: Device password
  - WAP> Shell
- **⚡ Auto-Skip on Failure**: Automatically moves to the next IP if all credential sets fail
- **📊 Real-Time Progress**: Shows progress bars, statistics, and estimated time remaining
- **📝 Automatic Logging**: Saves results to a timestamped file
- **⏱️ Configurable Timeout**: Set custom timeout per connection

## 📦 Prerequisites

Before using this script, ensure you have the following installed:

| Tool | Installation Command |
|------|---------------------|
| **masscan** | `sudo apt-get install masscan` |
| **expect** | `sudo apt-get install expect` |
| **jq** | `sudo apt-get install jq` |
| **sshpass** | `sudo apt-get install sshpass` |

### Quick Install All Dependencies

```bash
sudo apt-get update
sudo apt-get install -y masscan expect jq sshpass

How it Works
╔════════════════════════════════════════════════════════╗
║     Wlan SSH Scanner + WiFi Info Grabber           ║
║     v1.0.0 - MULTI-CREDENTIAL - AUTO SKIP            ║
╚════════════════════════════════════════════════════════╝

⚠️  Two-step login flow:
   1. SSH Password
   2. Login (username)
   3. Device Password
   4. WAP> shell

🔑 Trying credential sets...
✅ Auto-skip on all failures

📡 Enter target (IP, IP/CIDR, or range):
   Target: 10.70.10.65
⚡ Enter scan rate (packets/sec):
   Rate: 1000
⏱️  Connection timeout (default 30s):
   Timeout: 30

[Scanning...]

✅ Found 3 device(s) with SSH open:
   ➜ 10.70.10.65
   ➜ 10.70.10.66
   ➜ 10.70.10.67

📝 Attempt 1/2:
   SSH Password: ********
   Login: ********
   Device Password: ********

✅ SUCCESS!

┌─────────────────────────────────────────────────────────┐
│                    WIFI INFORMATION                    │
└─────────────────────────────────────────────────────────┘
SSID number:1
----------------------------------------------------
SSID Index                    :1
SSID                          :***********
BSSID                         :A1:B1:05:C3:F5:DD
Enable                        :Enabled
Status                        :Up
Authentication Mode           :WPA/WPA2-PSK
Encryption Mode               :TKIPandAESEncryption
Channel                       :10(auto)
Channel bandwidth             :Auto 20/40 MHz
Standard                      :11bgn
Supported Max Rate            :300 M
Maximum Tx-Power              :25 dBm (316 mW)
Current Tx-Power Level        :100%
───────────────────────────────────────────────────────────

✅ WiFi info retrieved from 10.70.10.65
───────────────────────────────────────────────────────────
🔄 Moving to next device...


CUSTOMIZING CREDENTIALS
CREDENTIALS=(
    "ssh_password|login_username|device_password"
    "ssh_password2|login_username2|device_password2"
)

