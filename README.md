# 🎯 Enhanced Claude Code Usage Monitor

[![Python Version](https://img.shields.io/badge/python-3.6+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

A comprehensive real-time terminal monitoring suite for Claude AI token usage. Features both simple monitoring and interactive setup with project identification, accurate daily cost tracking, and advanced session management.

![Claude Token Monitor Screenshot](doc/sc.png)

---

## 📑 Table of Contents

- [✨ Features](#-features)
- [🚀 Installation](#-installation)
  - [Prerequisites](#prerequisites)
  - [Quick Setup](#quick-setup)
- [📖 Usage](#-usage)
  - [Basic Usage](#basic-usage)
  - [Specify Your Plan](#specify-your-plan)
  - [Custom Reset Times](#custom-reset-times)
  - [Timezone Configuration](#timezone-configuration)
  - [Exit the Monitor](#exit-the-monitor)
- [📊 Understanding Claude Sessions](#-understanding-claude-sessions)
  - [How Sessions Work](#how-sessions-work)
  - [Token Reset Schedule](#token-reset-schedule)
  - [Burn Rate Calculation](#burn-rate-calculation)
- [🛠️ Token Limits by Plan](#-token-limits-by-plan)
- [🔧 Advanced Features](#-advanced-features)
  - [Auto-Detection Mode](#auto-detection-mode)
  - [Smart Pro Plan Switching](#smart-pro-plan-switching)
- [⚡ Best Practices](#-best-practices)
- [🐛 Troubleshooting](#-troubleshooting)
- [🚀 Example Usage Scenarios](#-example-usage-scenarios)
- [🤝 Contributing](#-contributing)
- [📝 License](#-license)
- [🙏 Acknowledgments](#-acknowledgments)

---

## ✨ Features

### 🚀 Core Monitoring
- **🔄 Real-time tracking** - Updates every 1-3 seconds with smooth refresh
- **📊 Visual progress bars** - Color-coded token and time progress indicators
- **🔮 Smart predictions** - Calculates when tokens will run out based on burn rate
- **📁 Project identification** - Shows which project/session is being monitored
- **💰 Accurate cost tracking** - Cumulative daily costs with session breakdowns

### 🎯 Multiple Interfaces
- **⚡ Simple Monitor** (`ccusage_monitor.py`) - Quick, lightweight monitoring
- **🧙‍♂️ Interactive Setup** (`ccusage_monitor_interactive.py`) - Full wizard with persistent settings
- **🔧 Real-time controls** - Press `s` to view settings, `m` to modify, `q` to quit

### 🤖 Intelligence & Automation
- **📋 Multi-plan support** - Pro, Max5, Max20, and auto-detect modes
- **🔍 Auto-detection** - Finds current active sessions and project paths
- **⚙️ Persistent settings** - Save preferences and reuse across sessions
- **⚠️ Smart warnings** - Token, cost, and time-based alerts

---

## 🚀 Installation

### Prerequisites

1. **Python 3.6+** installed on your system
2. **pytz** Python package:
   ```bash
   pip install pytz
   ```
3. **ccusage** CLI tool installed globally:
   ```bash
   npm install -g ccusage
   ```

### Quick Setup

```bash
# Clone the repository
git clone https://github.com/gramanoid/enhanced-cc-usage-monitor.git
cd enhanced-cc-usage-monitor

# Make scripts executable
chmod +x ccusage_monitor.py ccusage_monitor_interactive.py

# Quick start - simple monitor
./ccusage_monitor.py

# OR - Interactive setup with full features
./ccusage_monitor_interactive.py
```

---

## 📖 Usage

### 🎯 Two Ways to Monitor

#### ⚡ Quick Monitor (Simple)
```bash
# Basic monitoring with project detection
./ccusage_monitor.py

# With custom plan
./ccusage_monitor.py --plan max5
```

#### 🧙‍♂️ Interactive Monitor (Full Features)
```bash
# Complete setup wizard with persistent settings
./ccusage_monitor_interactive.py
```

The interactive version includes:
- 🔍 Active session detection
- ⚙️ Persistent configuration 
- 🎨 Customizable display options
- 🚨 Advanced alert settings
- 🎹 Live settings modification (`s` = show, `m` = modify, `q` = quit)

### Specify Your Plan

```bash
# Pro plan (~7,000 tokens) - Default
./ccusage_monitor.py --plan pro

# Max5 plan (~35,000 tokens)
./ccusage_monitor.py --plan max5

# Max20 plan (~140,000 tokens)
./ccusage_monitor.py --plan max20

# Auto-detect from highest previous session
./ccusage_monitor.py --plan custom_max
```

### Custom Reset Times

Set a custom daily reset hour (0-23):

```bash
# Reset at 3 AM
./ccusage_monitor.py --reset-hour 3

# Reset at 10 PM
./ccusage_monitor.py --reset-hour 22
```

### Timezone Configuration

The default timezone is **Europe/Warsaw**. You can change it to any valid timezone:

```bash
# Use US Eastern Time
./ccusage_monitor.py --timezone US/Eastern

# Use Tokyo time
./ccusage_monitor.py --timezone Asia/Tokyo

# Use UTC
./ccusage_monitor.py --timezone UTC

# Use London time
./ccusage_monitor.py --timezone Europe/London
```

### Exit the Monitor

Press `Ctrl+C` to gracefully exit the monitoring tool.

---

## 📊 Understanding Claude Sessions

### How Sessions Work

Claude Code operates on a **5-hour rolling session window system**:

- **Sessions start** with your first message to Claude
- **Sessions last** for exactly 5 hours from that first message
- **Token limits** apply within each 5-hour session window
- **Multiple sessions** can be active simultaneously

### Token Reset Schedule

**Default reset times** (in your configured timezone, default: Europe/Warsaw):
- `04:00`, `09:00`, `14:00`, `18:00`, `23:00`

> **⚠️ Important**: These are reference times. Your actual token refresh happens 5 hours after YOUR first message in each session.

> **🌍 Timezone Note**: The default timezone is Europe/Warsaw. You can change it using the `--timezone` parameter with any valid timezone name.

### Burn Rate Calculation

The monitor calculates burn rate based on all sessions from the last hour:

- Analyzes token consumption across overlapping sessions
- Provides accurate recent usage patterns
- Updates predictions in real-time

---

## 🛠️ Token Limits by Plan

| Plan | Token Limit | Best For |
|------|-------------|----------|
| **Pro** | ~7,000 | Light usage, testing (default) |
| **Max5** | ~35,000 | Regular development |
| **Max20** | ~140,000 | Heavy usage, large projects |
| **Custom Max** | Auto-detect | Automatically uses highest from previous sessions |

---

## 🔧 Advanced Features

### 📁 Project Identification
- **Auto-detects** which Claude project/session is currently active
- **Displays project name** in monitor header
- **Multiple session handling** for complex workflows

### 💰 Enhanced Cost Tracking
- **Cumulative daily costs** - Fixed calculation shows total spent today
- **Session cost breakdown** - Individual session spending
- **Real-time burn rate** - Cost per hour predictions

### 🎹 Interactive Controls (Interactive Version)
- **`s`** - Show current settings without stopping monitor
- **`m`** - Modify settings on-the-fly with guided menus  
- **`q`** - Quit gracefully
- **Persistent settings** - Configurations saved between sessions

### 🤖 Auto-Detection Features
- **Plan detection** - Automatically finds appropriate token limits
- **Session discovery** - Identifies all active Claude sessions
- **Smart switching** - Upgrades limits when exceeded

---

## ⚡ Best Practices

1. **🚀 Start Early**: Begin monitoring when you start a new session
2. **👀 Watch Velocity**: Monitor burn rate indicators to manage usage
3. **📅 Plan Ahead**: If tokens will deplete before reset, adjust your usage
4. **⏰ Custom Schedule**: Set `--reset-hour` to match your typical work schedule
5. **🤖 Use Auto-Detect**: Let the monitor figure out your limits with `--plan custom_max`

---

## 🐛 Troubleshooting

### "Failed to get usage data"

- Ensure `ccusage` is installed: `npm install -g ccusage`
- Check if you have an active Claude session
- Verify `ccusage` works: `ccusage blocks --json`

### "No active session found"

- Start a new Claude Code session
- The monitor only works when there's an active session

### Cursor remains hidden after exit

```bash
printf '\033[?25h'
```

### Display issues or overlapping text

- Ensure your terminal window is at least 80 characters wide
- Try resizing your terminal and restarting the monitor

---

## 🚀 Example Usage Scenarios

### 🌅 First Time User
```bash
# Interactive setup - recommended for new users
./ccusage_monitor_interactive.py
# Walks through session detection, plan selection, and preferences
```

### ⚡ Quick Daily Check
```bash
# Simple monitoring with auto-detection
./ccusage_monitor.py --plan custom_max
# Shows project name and accurate daily costs
```

### 🌍 International Developer
```bash
# Interactive setup with timezone selection
./ccusage_monitor_interactive.py
# Includes built-in timezone picker and persistent settings
```

### 🔧 Power User with Multiple Projects
```bash
# Quick monitor for specific workflows
./ccusage_monitor.py --timezone US/Pacific --reset-hour 9
# Project identification shows which session is active
```

### 🎯 Cost-Conscious Monitoring
```bash
# Interactive with cost alerts
./ccusage_monitor_interactive.py
# Set custom cost thresholds and daily spending limits
```

---

## 🤝 Contributing

Contributions are welcome! Feel free to:

- 🐛 Report bugs or issues
- 💡 Suggest new features
- 🔧 Submit pull requests
- 📚 Improve documentation

### 🆕 What's New in Enhanced Version

**Recent Improvements:**
- ✅ **Fixed daily cost calculation** - Now shows accurate cumulative spending
- ✅ **Added project identification** - Displays which session is being monitored  
- ✅ **Interactive setup wizard** - Complete configuration with persistent settings
- ✅ **Real-time settings control** - Modify preferences without restarting
- ✅ **Enhanced session detection** - Better multi-project support

### 📊 Help Us Improve

Share your experience to help improve the monitoring tool:
- 🐛 Report issues with session detection
- 💡 Suggest new monitoring features  
- 📈 Share cost tracking use cases
- 🔧 Contribute improvements to project identification

---

## 📝 License

[MIT License](LICENSE) - feel free to use and modify as needed.

---

## 🙏 Acknowledgments

This tool builds upon the excellent [ccusage](https://github.com/ryoppippi/ccusage) by [@ryoppippi](https://github.com/ryoppippi), adding a real-time monitoring interface with visual progress bars, burn rate calculations, and predictive analytics.

- 🏗️ Built for monitoring [Claude Code](https://claude.ai/code) token usage
- 🔧 Uses [ccusage](https://www.npmjs.com/package/ccusage) for data retrieval
- 💭 Inspired by the need for better token usage visibility

---

<div align="center">

**⭐ Star this repo if you find it useful! ⭐**

[Report Bug](https://github.com/gramanoid/enhanced-cc-usage-monitor/issues) • [Request Feature](https://github.com/gramanoid/enhanced-cc-usage-monitor/issues) • [Contribute](https://github.com/gramanoid/enhanced-cc-usage-monitor/pulls)

</div>
