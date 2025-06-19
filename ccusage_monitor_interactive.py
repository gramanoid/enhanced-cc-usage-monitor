#!/usr/bin/env python3

import subprocess
import json
import sys
import time
from datetime import datetime, timedelta, timezone
import os
import argparse
import pytz
from collections import defaultdict
import pickle
from pathlib import Path

# Configuration file path
CONFIG_FILE = Path.home() / '.claude_monitor_config.json'

def save_config(config):
    """Save configuration to persistent file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"💾 Configuration saved to {CONFIG_FILE}")
    except Exception as e:
        print(f"⚠️  Warning: Could not save configuration: {e}")

def load_config():
    """Load configuration from persistent file."""
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️  Warning: Could not load configuration: {e}")
    return None

def run_ccusage(command='blocks', extra_args=None):
    """Execute ccusage command and return parsed JSON data."""
    try:
        cmd = ['ccusage', command, '--json']
        if extra_args:
            cmd.extend(extra_args)
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running ccusage: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return None


def detect_active_sessions():
    """Detect active Claude Code sessions by project."""
    print("🔍 Detecting active Claude Code sessions...")
    
    # Get per-project active blocks
    blocks_data = run_ccusage('blocks', ['--per-project', '--active'])
    
    if not blocks_data or 'blocks' not in blocks_data:
        print("❌ No active sessions detected.")
        return []
    
    active_sessions = []
    for block in blocks_data['blocks']:
        if block.get('isActive', False):
            project_path = block.get('projectPath', 'Unknown')
            session_info = {
                'project_path': project_path,
                'tokens': block['tokenCounts']['inputTokens'] + block['tokenCounts']['outputTokens'],
                'cost': block.get('costUSD', 0),
                'models': block.get('models', []),
                'elapsed_minutes': get_elapsed_minutes(block),
                'remaining_minutes': get_remaining_minutes(block)
            }
            active_sessions.append(session_info)
    
    return active_sessions


def get_elapsed_minutes(block):
    """Calculate elapsed minutes from block start time."""
    try:
        start_time = datetime.fromisoformat(block['startTime'].replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        elapsed = now - start_time
        return elapsed.total_seconds() / 60
    except:
        return 0


def get_remaining_minutes(block):
    """Calculate remaining minutes until block end."""
    try:
        end_time = datetime.fromisoformat(block['endTime'].replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        remaining = end_time - now
        return max(0, remaining.total_seconds() / 60)
    except:
        return 0


def format_path_short(path, max_length=35):
    """Format path for display, truncating if necessary."""
    if len(path) <= max_length:
        return path
    
    # Try to show meaningful parts
    parts = path.split('/')
    if len(parts) > 3:
        return f".../{'/'.join(parts[-2:])}"
    return f"...{path[-(max_length-3):]}"


def display_session_summary(sessions):
    """Display a summary of detected sessions."""
    if not sessions:
        print("❌ No active sessions found.")
        return
    
    print(f"\n✅ Found {len(sessions)} active session(s):")
    print("=" * 70)
    
    for i, session in enumerate(sessions, 1):
        path_short = format_path_short(session['project_path'])
        tokens = session['tokens']
        cost = session['cost']
        models = ', '.join(set(m.replace('claude-', '').replace('-20250514', '') for m in session['models'] if 'claude-' in m))
        
        elapsed = session['elapsed_minutes']
        remaining = session['remaining_minutes']
        
        print(f"  {i}. 📁 {path_short}")
        print(f"     🎯 {tokens:,} tokens | 💰 ${cost:.2f} | 🤖 {models}")
        print(f"     ⏱️  {format_time(elapsed)} elapsed | ⏳ {format_time(remaining)} remaining")
        print()


def format_time(minutes):
    """Format minutes into human-readable time."""
    if minutes < 60:
        return f"{int(minutes)}m"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    if mins == 0:
        return f"{hours}h"
    return f"{hours}h {mins}m"


def get_user_choice(prompt, options):
    """Get user choice from a list of options."""
    print(prompt)
    for i, option in enumerate(options, 1):
        print(f"  {i}. {option}")
    
    while True:
        try:
            choice = input(f"\nEnter choice (1-{len(options)}): ").strip()
            choice_num = int(choice)
            if 1 <= choice_num <= len(options):
                return choice_num - 1
            else:
                print(f"Please enter a number between 1 and {len(options)}")
        except ValueError:
            print("Please enter a valid number")


def get_token_limit_options():
    """Get token limit options based on historical data."""
    print("\n🔍 Analyzing your usage history for token limits...")
    
    # Get historical data to find max usage
    blocks_data = run_ccusage('blocks')
    max_tokens = 0
    
    if blocks_data and 'blocks' in blocks_data:
        for block in blocks_data['blocks']:
            if not block.get('isGap', False) and not block.get('isActive', False):
                tokens = block['tokenCounts']['inputTokens'] + block['tokenCounts']['outputTokens']
                max_tokens = max(max_tokens, tokens)
    
    options = [
        ("Pro Plan (~7,000 tokens)", "pro", 7000),
        ("Max 5 Plan (~35,000 tokens)", "max5", 35000),
        ("Max 20 Plan (~140,000 tokens)", "max20", 140000),
    ]
    
    if max_tokens > 0:
        options.append((f"Custom Max (based on your history: {max_tokens:,} tokens)", "custom_max", max_tokens))
    
    return options


def get_timezone_choice():
    """Get timezone choice from user."""
    common_timezones = [
        ("UTC", "UTC"),
        ("US Eastern", "US/Eastern"), 
        ("US Central", "US/Central"),
        ("US Mountain", "US/Mountain"),
        ("US Pacific", "US/Pacific"),
        ("Europe/London", "Europe/London"),
        ("Europe/Paris", "Europe/Paris"),
        ("Asia/Tokyo", "Asia/Tokyo"),
        ("System Default", "local")
    ]
    
    choice_idx = get_user_choice("\n⏰ Choose your timezone:", [tz[0] for tz in common_timezones])
    return common_timezones[choice_idx][1]


def get_reset_hour():
    """Get reset hour preference from user."""
    print("\n🔄 When should the daily reset occur? (0-23, where 0 = midnight)")
    print("   This affects when your daily usage counters reset.")
    
    while True:
        try:
            hour = input("Enter hour (default: 0 for midnight): ").strip()
            if not hour:
                return 0
            hour_num = int(hour)
            if 0 <= hour_num <= 23:
                return hour_num
            else:
                print("Please enter a number between 0 and 23")
        except ValueError:
            print("Please enter a valid number")

def get_display_preferences():
    """Get display and UI preferences."""
    print("\n🎨 Display Preferences")
    
    # Update frequency
    update_options = [
        ("Every 1 second (real-time)", 1),
        ("Every 3 seconds (default)", 3),
        ("Every 5 seconds", 5),
        ("Every 10 seconds", 10),
        ("Every 30 seconds", 30)
    ]
    update_choice = get_user_choice("📊 How often should the display update?", [opt[0] for opt in update_options])
    update_frequency = update_options[update_choice][1]
    
    # Progress bar width
    width_options = [
        ("Narrow (15 chars - good for small terminals)", 15),
        ("Medium (20 chars)", 20),
        ("Wide (25 chars - default)", 25)
    ]
    width_choice = get_user_choice("\n📏 Progress bar width:", [opt[0] for opt in width_options])
    progress_width = width_options[width_choice][1]
    
    # Sound alerts
    sound_choice = get_user_choice("\n🔔 Enable sound alerts for warnings?", ["Yes", "No"])
    sound_alerts = sound_choice == 0
    
    # Color scheme
    color_options = [
        ("Default (colorful)", "default"),
        ("Minimal (less colors)", "minimal"),
        ("Monochrome (no colors)", "mono")
    ]
    color_choice = get_user_choice("\n🌈 Color scheme:", [opt[0] for opt in color_options])
    color_scheme = color_options[color_choice][1]
    
    return {
        'update_frequency': update_frequency,
        'progress_width': progress_width,
        'sound_alerts': sound_alerts,
        'color_scheme': color_scheme
    }

def get_alert_preferences():
    """Get alert and notification preferences."""
    print("\n🚨 Alert Settings")
    
    # Token usage warnings
    token_warning_options = [
        ("At 80% of limit", 0.8),
        ("At 90% of limit", 0.9),
        ("At 95% of limit", 0.95),
        ("Never", 0)
    ]
    token_choice = get_user_choice("⚠️  When to show token usage warnings:", [opt[0] for opt in token_warning_options])
    token_warning_threshold = token_warning_options[token_choice][1]
    
    # Cost warnings
    cost_warning_options = [
        ("Every $10 spent", 10),
        ("Every $25 spent", 25),
        ("Every $50 spent", 50),
        ("Never", 0)
    ]
    cost_choice = get_user_choice("\n💰 When to show cost warnings:", [opt[0] for opt in cost_warning_options])
    cost_warning_threshold = cost_warning_options[cost_choice][1]
    
    # Session end warnings
    time_warning_options = [
        ("15 minutes before session ends", 15),
        ("30 minutes before session ends", 30),
        ("1 hour before session ends", 60),
        ("Never", 0)
    ]
    time_choice = get_user_choice("\n⏰ When to warn before session ends:", [opt[0] for opt in time_warning_options])
    time_warning_threshold = time_warning_options[time_choice][1]
    
    return {
        'token_warning_threshold': token_warning_threshold,
        'cost_warning_threshold': cost_warning_threshold,
        'time_warning_threshold': time_warning_threshold
    }

def get_advanced_preferences():
    """Get advanced preferences."""
    print("\n⚙️  Advanced Settings")
    
    # Auto-save session data
    autosave_choice = get_user_choice("💾 Auto-save session data for analysis?", ["Yes", "No"])
    auto_save = autosave_choice == 0
    
    # Include cache tokens in display
    cache_choice = get_user_choice("\n🗄️  Include cache tokens in token counts?", ["Yes", "No"])
    include_cache = cache_choice == 0
    
    # Show model breakdown
    model_choice = get_user_choice("\n🤖 Show model breakdown in summary?", ["Yes", "No"])
    show_models = model_choice == 0
    
    # Startup checks
    startup_choice = get_user_choice("\n🔍 Run startup checks (verify ccusage, detect conflicts)?", ["Yes", "No"])
    startup_checks = startup_choice == 0
    
    return {
        'auto_save': auto_save,
        'include_cache': include_cache,
        'show_models': show_models,
        'startup_checks': startup_checks
    }


def setup_wizard():
    """Interactive setup wizard for the Claude Code Usage Monitor."""
    print("🎯" + "=" * 68)
    print("🤖 CLAUDE CODE USAGE MONITOR - INTERACTIVE SETUP")
    print("🎯" + "=" * 68)
    print()
    
    # Check for existing configuration
    existing_config = load_config()
    if existing_config:
        print("📋 Found existing configuration!")
        print(f"   Last used: {existing_config.get('last_used', 'Unknown')}")
        print(f"   Monitoring mode: {existing_config.get('mode', 'Unknown')}")
        print(f"   Token plan: {existing_config.get('plan', 'Unknown')}")
        
        use_existing = get_user_choice("\nWhat would you like to do?", [
            "Use existing settings and start monitoring",
            "Modify existing settings", 
            "Create completely new configuration"
        ])
        
        if use_existing == 0:  # Use existing
            existing_config['last_used'] = datetime.now().isoformat()
            save_config(existing_config)
            return existing_config
        elif use_existing == 1:  # Modify existing
            # Load existing as defaults but allow modifications
            print("\n🔧 Modifying existing configuration...")
            defaults = existing_config
        else:  # New config
            defaults = None
    else:
        defaults = None
    
    # Step 1: Detect active sessions
    active_sessions = detect_active_sessions()
    display_session_summary(active_sessions)
    
    # Step 2: Choose monitoring mode
    if len(active_sessions) > 1:
        mode_options = [
            "Monitor all sessions separately (per-project view)",
            "Monitor single aggregated session (combined view)",
            "Monitor specific session only"
        ]
        
        default_mode = 0  # Default to per-project for multiple sessions
        if defaults and 'mode' in defaults:
            mode_map = {'per_project': 0, 'aggregated': 1, 'single': 2}
            default_mode = mode_map.get(defaults['mode'], 0)
        
        print(f"\n📊 How would you like to monitor your sessions? (default: {mode_options[default_mode]})")
        mode_choice = get_user_choice("", mode_options)
        
        if mode_choice == 0:  # Per-project monitoring
            monitoring_mode = "per_project"
            selected_project = None
        elif mode_choice == 1:  # Aggregated monitoring
            monitoring_mode = "aggregated" 
            selected_project = None
        else:  # Specific session
            session_options = [format_path_short(s['project_path']) for s in active_sessions]
            session_choice = get_user_choice("\n📁 Which session would you like to monitor?", session_options)
            monitoring_mode = "single"
            selected_project = active_sessions[session_choice]['project_path']
    else:
        if active_sessions:
            print(f"\n📊 Will monitor your active session: {format_path_short(active_sessions[0]['project_path'])}")
            monitoring_mode = "single"
            selected_project = active_sessions[0]['project_path']
        else:
            print("\n📊 Will monitor for when a session becomes active.")
            monitoring_mode = "aggregated"
            selected_project = None
    
    # Step 3: Token limit settings
    token_options = get_token_limit_options()
    
    # Use existing plan as default
    default_token = 0
    if defaults and 'plan' in defaults:
        plan_codes = [opt[1] for opt in token_options]
        if defaults['plan'] in plan_codes:
            default_token = plan_codes.index(defaults['plan'])
    
    token_choice = get_user_choice("\n🎯 Choose your token limit plan:", [opt[0] for opt in token_options])
    plan_name, plan_code, plan_limit = token_options[token_choice]
    
    # Step 4: Timezone settings
    timezone_choice = get_timezone_choice()
    
    # Step 5: Reset hour
    reset_hour = get_reset_hour()
    
    # Step 6: Display preferences
    setup_type = get_user_choice("\n⚙️  Configuration type:", [
        "Quick setup (use defaults)",
        "Full setup (customize all settings)"
    ])
    
    if setup_type == 0:  # Quick setup
        display_prefs = {
            'update_frequency': 1,  # Default to 1 second for quick setup
            'progress_width': 15,
            'sound_alerts': False,
            'color_scheme': 'default'
        }
        alert_prefs = {
            'token_warning_threshold': 0.9,
            'cost_warning_threshold': 25,
            'time_warning_threshold': 30
        }
        advanced_prefs = {
            'auto_save': True,
            'include_cache': False,
            'show_models': True,
            'startup_checks': True
        }
    else:  # Full setup
        display_prefs = get_display_preferences()
        alert_prefs = get_alert_preferences()
        advanced_prefs = get_advanced_preferences()
    
    # Combine all settings
    config = {
        'mode': monitoring_mode,
        'project': selected_project,
        'plan': plan_code,
        'plan_name': plan_name,
        'plan_limit': plan_limit,
        'timezone': timezone_choice,
        'reset_hour': reset_hour,
        'last_used': datetime.now().isoformat(),
        'version': '2.0',
        **display_prefs,
        **alert_prefs,
        **advanced_prefs
    }
    
    # Summary
    print("\n" + "=" * 70)
    print("📋 CONFIGURATION SUMMARY")
    print("=" * 70)
    print(f"🔄 Monitoring Mode: {monitoring_mode}")
    if selected_project:
        print(f"📁 Selected Project: {format_path_short(selected_project)}")
    print(f"🎯 Token Plan: {plan_name}")
    print(f"⏰ Timezone: {timezone_choice}")
    print(f"🔄 Daily Reset: {reset_hour}:00")
    print(f"📊 Update Frequency: Every {display_prefs['update_frequency']} seconds")
    print(f"📏 Progress Bar Width: {display_prefs['progress_width']} characters")
    print(f"🚨 Token Warnings: {'Enabled' if alert_prefs['token_warning_threshold'] > 0 else 'Disabled'}")
    print(f"💰 Cost Warnings: {'$' + str(alert_prefs['cost_warning_threshold']) if alert_prefs['cost_warning_threshold'] > 0 else 'Disabled'}")
    print("=" * 70)
    
    # Confirm and start
    confirm = input("\n✅ Start monitoring with these settings? (y/N): ").strip().lower()
    if confirm in ['y', 'yes']:
        save_config(config)
        return config
    else:
        print("❌ Setup cancelled.")
        return None


def show_current_settings(config):
    """Display current configuration settings."""
    print("\n" + "📋" + "=" * 60)
    print("📋 CURRENT SETTINGS")
    print("📋" + "=" * 60)
    
    # Basic settings
    print(f"🔄 Monitoring Mode: {config.get('mode', 'Unknown')}")
    if config.get('project'):
        print(f"📁 Selected Project: {format_path_short(config['project'])}")
    print(f"🎯 Token Plan: {config.get('plan_name', config.get('plan', 'Unknown'))}")
    print(f"⏰ Timezone: {config.get('timezone', 'Unknown')}")
    print(f"🔄 Daily Reset: {config.get('reset_hour', 0)}:00")
    
    # Display settings
    print(f"\n🎨 Display Settings:")
    print(f"   📊 Update Frequency: Every {config.get('update_frequency', 3)} seconds")
    print(f"   📏 Progress Bar Width: {config.get('progress_width', 15)} characters")
    print(f"   🔔 Sound Alerts: {'Enabled' if config.get('sound_alerts', False) else 'Disabled'}")
    print(f"   🌈 Color Scheme: {config.get('color_scheme', 'default')}")
    
    # Alert settings
    print(f"\n🚨 Alert Settings:")
    token_thresh = config.get('token_warning_threshold', 0)
    print(f"   ⚠️  Token Warnings: {'At ' + str(int(token_thresh * 100)) + '% of limit' if token_thresh > 0 else 'Disabled'}")
    cost_thresh = config.get('cost_warning_threshold', 0)
    print(f"   💰 Cost Warnings: {'Every $' + str(cost_thresh) if cost_thresh > 0 else 'Disabled'}")
    time_thresh = config.get('time_warning_threshold', 0)
    print(f"   ⏰ Time Warnings: {str(time_thresh) + ' minutes before session ends' if time_thresh > 0 else 'Disabled'}")
    
    # Advanced settings
    print(f"\n⚙️  Advanced Settings:")
    print(f"   💾 Auto-save Data: {'Enabled' if config.get('auto_save', True) else 'Disabled'}")
    print(f"   🗄️  Include Cache Tokens: {'Yes' if config.get('include_cache', False) else 'No'}")
    print(f"   🤖 Show Model Breakdown: {'Yes' if config.get('show_models', True) else 'No'}")
    print(f"   🔍 Startup Checks: {'Enabled' if config.get('startup_checks', True) else 'Disabled'}")
    
    print(f"\n📅 Last Used: {config.get('last_used', 'Unknown')}")
    print("📋" + "=" * 60)

def modify_settings_menu(config):
    """Interactive menu to modify specific settings while monitoring."""
    while True:
        print("\n⚙️  QUICK SETTINGS MENU")
        print("=" * 40)
        
        options = [
            "🎨 Change display settings (update frequency, progress bar)",
            "🚨 Change alert settings (warnings, thresholds)",
            "⏰ Change timezone and reset hour",
            "🎯 Change token plan",
            "📊 Change monitoring mode",
            "💾 Save settings and return to monitoring",
            "❌ Return without saving changes"
        ]
        
        choice = get_user_choice("Select what to modify:", options)
        
        if choice == 0:  # Display settings
            new_display = get_display_preferences()
            config.update(new_display)
            print("✅ Display settings updated!")
            
        elif choice == 1:  # Alert settings
            new_alerts = get_alert_preferences()
            config.update(new_alerts)
            print("✅ Alert settings updated!")
            
        elif choice == 2:  # Timezone and reset
            new_timezone = get_timezone_choice()
            new_reset = get_reset_hour()
            config['timezone'] = new_timezone
            config['reset_hour'] = new_reset
            print("✅ Timezone and reset hour updated!")
            
        elif choice == 3:  # Token plan
            token_options = get_token_limit_options()
            token_choice = get_user_choice("🎯 Choose your token limit plan:", [opt[0] for opt in token_options])
            plan_name, plan_code, plan_limit = token_options[token_choice]
            config['plan'] = plan_code
            config['plan_name'] = plan_name
            config['plan_limit'] = plan_limit
            print("✅ Token plan updated!")
            
        elif choice == 4:  # Monitoring mode
            print("⚠️  Note: Changing monitoring mode will restart the monitor")
            mode_options = [
                "Monitor all sessions separately (per-project view)",
                "Monitor single aggregated session (combined view)",
                "Monitor specific session only"
            ]
            mode_choice = get_user_choice("📊 Choose monitoring mode:", mode_options)
            
            if mode_choice == 0:
                config['mode'] = "per_project"
                config['project'] = None
            elif mode_choice == 1:
                config['mode'] = "aggregated"
                config['project'] = None
            else:
                # Get active sessions for selection
                active_sessions = detect_active_sessions()
                if active_sessions:
                    session_options = [format_path_short(s['project_path']) for s in active_sessions]
                    session_choice = get_user_choice("📁 Which session to monitor?", session_options)
                    config['mode'] = "single"
                    config['project'] = active_sessions[session_choice]['project_path']
                else:
                    print("❌ No active sessions found. Keeping current mode.")
            print("✅ Monitoring mode updated!")
            
        elif choice == 5:  # Save and return
            config['last_used'] = datetime.now().isoformat()
            save_config(config)
            print("💾 Settings saved! Returning to monitoring...")
            break
            
        elif choice == 6:  # Return without saving
            print("❌ Changes discarded. Returning to monitoring...")
            break
        
        # Show updated settings after each change
        show_current_settings(config)

def run_monitor_with_config(config):
    """Run the monitor with the specified configuration and interactive controls."""
    import threading
    import select
    import sys
    import tty
    import termios
    
    print(f"\n🚀 Starting monitor...")
    print("📋 Press 's' to show settings, 'm' to modify settings, 'q' to quit")
    print("=" * 60)
    
    # Store original terminal settings
    old_settings = termios.tcgetattr(sys.stdin)
    
    def monitor_keyboard():
        """Monitor for keyboard input in a separate thread."""
        try:
            tty.setraw(sys.stdin.fileno())
            while True:
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1).lower()
                    
                    if key == 's':
                        # Restore terminal for proper input
                        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                        print("\n" + "🔽" * 20 + " PAUSED FOR SETTINGS VIEW " + "🔽" * 20)
                        show_current_settings(config)
                        input("\nPress Enter to continue monitoring...")
                        print("🔼" * 20 + " RESUMING MONITORING " + "🔼" * 20 + "\n")
                        tty.setraw(sys.stdin.fileno())
                        
                    elif key == 'm':
                        # Restore terminal for proper input
                        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                        print("\n" + "🔽" * 20 + " PAUSED FOR SETTINGS MODIFICATION " + "🔽" * 20)
                        modify_settings_menu(config)
                        print("🔼" * 20 + " RESUMING MONITORING " + "🔼" * 20 + "\n")
                        tty.setraw(sys.stdin.fileno())
                        
                    elif key == 'q':
                        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                        print("\n\n👋 Monitoring stopped by user.")
                        os._exit(0)
                        
        except Exception as e:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            print(f"Keyboard monitoring error: {e}")
    
    # Start keyboard monitoring in background thread
    keyboard_thread = threading.Thread(target=monitor_keyboard, daemon=True)
    keyboard_thread.start()
    
    try:
        # Build command arguments
        args = ['python3', 'ccusage_monitor.py']
        
        if config.get('plan'):
            args.extend(['--plan', config['plan']])
        
        if config.get('timezone', 'local') != 'local':
            args.extend(['--timezone', config['timezone']])
        
        if config.get('reset_hour', 0) != 0:
            args.extend(['--reset-hour', str(config['reset_hour'])])
        
        # Add update frequency if different from default
        if config.get('update_frequency', 3) != 3:
            # Note: The base monitor would need to be updated to accept this parameter
            pass
        
        subprocess.run(args)
        
    except KeyboardInterrupt:
        print("\n\n👋 Monitoring stopped. Thanks for using Claude Code Usage Monitor!")
    finally:
        # Restore terminal settings
        try:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        except:
            pass


if __name__ == "__main__":
    try:
        config = setup_wizard()
        if config:
            run_monitor_with_config(config)
    except KeyboardInterrupt:
        print("\n\n👋 Setup cancelled. Goodbye!")
        sys.exit(0)
