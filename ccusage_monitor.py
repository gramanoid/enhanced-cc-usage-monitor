#!/usr/bin/env python3

import subprocess
import json
import sys
import time
from datetime import datetime, timedelta, timezone
import os
import argparse
import pytz


def run_ccusage(per_project=False, project_filter=None):
    """Execute ccusage blocks --json command and return parsed JSON data."""
    try:
        cmd = ['ccusage', 'blocks', '--json']
        if per_project:
            cmd.append('--per-project')
        if project_filter:
            cmd.extend(['--project', project_filter])
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running ccusage: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return None


def get_session_info():
    """Get session information including project paths."""
    try:
        result = subprocess.run(['ccusage', 'session', '--json'], capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running ccusage session: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing session JSON: {e}")
        return None


def parse_session_id_to_project_path(session_id):
    """Convert session ID to readable project path."""
    if not session_id or not session_id.startswith('-'):
        return "Unknown Project"
    
    # Remove leading dash
    path_parts = session_id[1:].split('-')
    
    # Handle special encoding cases
    project_path = '/'.join(path_parts)
    
    # Clean up known patterns
    project_path = project_path.replace('home/alexgrama/GitHome/', '~/GitHome/')
    project_path = project_path.replace('home/alexgrama/', '~/')
    project_path = project_path.replace('/personal/', '/_personal/')
    project_path = project_path.replace('/work/', '/_work/')
    project_path = project_path.replace('/active/', '/_active/')
    
    # Get just the project name (last part of path)
    if project_path.count('/') > 0:
        project_name = project_path.split('/')[-1]
        if len(project_name) > 20:
            project_name = project_name[:17] + "..."
        return project_name
    
    return project_path


def get_current_project_info():
    """Get information about the currently active project."""
    session_data = get_session_info()
    if not session_data or 'sessions' not in session_data:
        return None
    
    # Find sessions with recent activity (today)
    today = datetime.now().strftime("%Y-%m-%d")
    recent_sessions = [s for s in session_data['sessions'] if s.get('lastActivity') == today]
    
    if recent_sessions:
        # Get the session with highest cost (most active)
        most_active = max(recent_sessions, key=lambda x: x.get('totalCost', 0))
        project_name = parse_session_id_to_project_path(most_active['sessionId'])
        return {
            'project_name': project_name,
            'session_id': most_active['sessionId'],
            'total_cost': most_active.get('totalCost', 0)
        }
    
    return None


def format_time(minutes):
    """Format minutes into human-readable time (e.g., '3h 45m')."""
    if minutes < 60:
        return f"{int(minutes)}m"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    if mins == 0:
        return f"{hours}h"
    return f"{hours}h {mins}m"


def create_token_progress_bar(percentage, width=15):
    """Create a token usage progress bar with bracket style."""
    filled = int(width * percentage / 100)
    
    # Create the bar with green fill and red empty space
    green_bar = '█' * filled
    red_bar = '░' * (width - filled)
    
    # Color codes
    green = '\033[92m'  # Bright green
    red = '\033[91m'    # Bright red
    reset = '\033[0m'
    
    return f"[{green}{green_bar}{red}{red_bar}{reset}] {percentage:.0f}%"


def create_time_progress_bar(elapsed_minutes, total_minutes, width=15):
    """Create a time progress bar showing time until reset."""
    if total_minutes <= 0:
        percentage = 0
    else:
        percentage = min(100, (elapsed_minutes / total_minutes) * 100)
    
    filled = int(width * percentage / 100)
    
    # Create the bar with blue fill and red empty space
    blue_bar = '█' * filled
    red_bar = '░' * (width - filled)
    
    # Color codes
    blue = '\033[94m'   # Bright blue
    red = '\033[91m'    # Bright red
    reset = '\033[0m'
    
    remaining_time = format_time(max(0, total_minutes - elapsed_minutes))
    return f"[{blue}{blue_bar}{red}{red_bar}{reset}] {remaining_time}"


def print_header():
    """Print the stylized header with sparkles."""
    cyan = '\033[96m'
    blue = '\033[94m'
    reset = '\033[0m'
    
    print(f"{cyan}CLAUDE CODE MONITOR{reset}")
    print(f"{blue}{'=' * 19}{reset}")
    print()


def get_velocity_indicator(burn_rate):
    """Get velocity emoji based on burn rate."""
    if burn_rate < 50:
        return '🐌'  # Slow
    elif burn_rate < 150:
        return '➡️'  # Normal
    elif burn_rate < 300:
        return '🚀'  # Fast
    else:
        return '⚡'  # Very fast


def calculate_hourly_burn_rate(blocks, current_time):
    """Calculate burn rate based on all sessions in the last hour."""
    if not blocks:
        return 0
    
    one_hour_ago = current_time - timedelta(hours=1)
    total_tokens = 0
    
    for block in blocks:
        start_time_str = block.get('startTime')
        if not start_time_str:
            continue
            
        # Parse start time
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        
        # Skip gaps
        if block.get('isGap', False):
            continue
            
        # Determine session end time
        if block.get('isActive', False):
            # For active sessions, use current time
            session_actual_end = current_time
        else:
            # For completed sessions, use actualEndTime or current time
            actual_end_str = block.get('actualEndTime')
            if actual_end_str:
                session_actual_end = datetime.fromisoformat(actual_end_str.replace('Z', '+00:00'))
            else:
                session_actual_end = current_time
        
        # Check if session overlaps with the last hour
        if session_actual_end < one_hour_ago:
            # Session ended before the last hour
            continue
            
        # Calculate how much of this session falls within the last hour
        session_start_in_hour = max(start_time, one_hour_ago)
        session_end_in_hour = min(session_actual_end, current_time)
        
        if session_end_in_hour <= session_start_in_hour:
            continue
            
        # Calculate portion of tokens used in the last hour
        total_session_duration = (session_actual_end - start_time).total_seconds() / 60  # minutes
        hour_duration = (session_end_in_hour - session_start_in_hour).total_seconds() / 60  # minutes
        
        if total_session_duration > 0:
            session_tokens = block.get('totalTokens', 0)
            tokens_in_hour = session_tokens * (hour_duration / total_session_duration)
            total_tokens += tokens_in_hour
    
    # Return tokens per minute
    return total_tokens / 60 if total_tokens > 0 else 0


def calculate_hourly_cost_burn_rate(blocks, current_time):
    """Calculate cost burn rate in USD per hour based on all sessions in the last hour."""
    one_hour_ago = current_time - timedelta(hours=1)
    total_cost = 0
    
    for block in blocks:
        # Parse start time
        start_time_str = block.get('startTime')
        if not start_time_str:
            continue
            
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        
        # Skip if session started after current time
        if start_time > current_time:
            continue
            
        # Determine session end time
        if block.get('isActive', False):
            session_actual_end = current_time
        else:
            actual_end_str = block.get('actualEndTime')
            if actual_end_str:
                session_actual_end = datetime.fromisoformat(actual_end_str.replace('Z', '+00:00'))
            else:
                session_actual_end = current_time
        
        # Check if session overlaps with the last hour
        if session_actual_end < one_hour_ago:
            continue
            
        # Calculate how much of this session falls within the last hour
        session_start_in_hour = max(start_time, one_hour_ago)
        session_end_in_hour = min(session_actual_end, current_time)
        
        if session_end_in_hour <= session_start_in_hour:
            continue
            
        # Calculate portion of cost incurred in the last hour
        total_session_duration = (session_actual_end - start_time).total_seconds() / 60
        hour_duration = (session_end_in_hour - session_start_in_hour).total_seconds() / 60
        
        if total_session_duration > 0:
            session_cost = block.get('costUSD', 0)
            cost_in_hour = session_cost * (hour_duration / total_session_duration)
            total_cost += cost_in_hour
    
    # Return cost per hour
    return total_cost


def get_next_reset_time(current_time, custom_reset_hour=None, timezone_str='Europe/Warsaw'):
    """Calculate next token reset time based on fixed 5-hour intervals.
    Default reset times in specified timezone: 04:00, 09:00, 14:00, 18:00, 23:00
    Or use custom reset hour if provided.
    """
    # Convert to specified timezone
    try:
        target_tz = pytz.timezone(timezone_str)
    except pytz.exceptions.UnknownTimeZoneError:
        print(f"Warning: Unknown timezone '{timezone_str}', using Europe/Warsaw")
        target_tz = pytz.timezone('Europe/Warsaw')
    
    # If current_time is timezone-aware, convert to target timezone
    if current_time.tzinfo is not None:
        target_time = current_time.astimezone(target_tz)
    else:
        # Assume current_time is in target timezone if not specified
        target_time = target_tz.localize(current_time)
    
    if custom_reset_hour is not None:
        # Use single daily reset at custom hour
        reset_hours = [custom_reset_hour]
    else:
        # Default 5-hour intervals
        reset_hours = [4, 9, 14, 18, 23]
    
    # Get current hour and minute
    current_hour = target_time.hour
    current_minute = target_time.minute
    
    # Find next reset hour
    next_reset_hour = None
    for hour in reset_hours:
        if current_hour < hour or (current_hour == hour and current_minute == 0):
            next_reset_hour = hour
            break
    
    # If no reset hour found today, use first one tomorrow
    if next_reset_hour is None:
        next_reset_hour = reset_hours[0]
        next_reset_date = target_time.date() + timedelta(days=1)
    else:
        next_reset_date = target_time.date()
    
    # Create next reset datetime in target timezone
    next_reset = target_tz.localize(
        datetime.combine(next_reset_date, datetime.min.time().replace(hour=next_reset_hour)),
        is_dst=None
    )
    
    # Convert back to the original timezone if needed
    if current_time.tzinfo is not None and current_time.tzinfo != target_tz:
        next_reset = next_reset.astimezone(current_time.tzinfo)
    
    return next_reset


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Claude Token Monitor - Real-time token usage monitoring')
    parser.add_argument('--plan', type=str, default='pro', 
                        choices=['pro', 'max5', 'max20', 'custom_max'],
                        help='Claude plan type (default: pro). Use "custom_max" to auto-detect from highest previous block')
    parser.add_argument('--reset-hour', type=int, 
                        help='Change the reset hour (0-23) for daily limits')
    parser.add_argument('--timezone', type=str, default='Europe/Warsaw',
                        help='Timezone for reset times (default: Europe/Warsaw). Examples: US/Eastern, Asia/Tokyo, UTC')
    parser.add_argument('--per-project', action='store_true',
                        help='Show per-project session blocks instead of aggregated')
    parser.add_argument('--project', type=str,
                        help='Filter by project path (supports partial matching)')
    return parser.parse_args()


def get_token_limit(plan, blocks=None):
    """Get token limit based on plan type."""
    if plan == 'custom_max' and blocks:
        # Find the highest token count from all previous blocks
        max_tokens = 0
        for block in blocks:
            if not block.get('isGap', False) and not block.get('isActive', False):
                tokens = block.get('totalTokens', 0)
                if tokens > max_tokens:
                    max_tokens = tokens
        # Return the highest found, or default to pro if none found
        return max_tokens if max_tokens > 0 else 7000
    
    limits = {
        'pro': 7000,
        'max5': 35000,
        'max20': 140000
    }
    return limits.get(plan, 7000)


def calculate_daily_cost(blocks, current_time, timezone_str='Europe/Warsaw'):
    """Calculate total cost spent today (cumulative for the current day)."""
    # Convert to specified timezone
    try:
        target_tz = pytz.timezone(timezone_str)
    except pytz.exceptions.UnknownTimeZoneError:
        target_tz = pytz.timezone('Europe/Warsaw')
    
    # Get start of current day in target timezone
    if current_time.tzinfo is not None:
        local_time = current_time.astimezone(target_tz)
    else:
        local_time = target_tz.localize(current_time)
    
    start_of_day = local_time.replace(hour=0, minute=0, second=0, microsecond=0)
    
    total_cost = 0
    
    for block in blocks:
        start_time_str = block.get('startTime')
        if not start_time_str:
            continue
            
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        
        # Convert session start time to target timezone for comparison
        if start_time.tzinfo is not None:
            session_local_time = start_time.astimezone(target_tz)
        else:
            session_local_time = target_tz.localize(start_time)
        
        # Count all costs from sessions that had any activity today
        # (sessions that started today OR sessions that were active today)
        session_end_time = start_time
        if block.get('isActive', False):
            # For active sessions, they're definitely active today
            session_end_time = current_time
        else:
            actual_end_str = block.get('actualEndTime')
            if actual_end_str:
                session_end_time = datetime.fromisoformat(actual_end_str.replace('Z', '+00:00'))
        
        # Convert end time to local timezone
        if session_end_time.tzinfo is not None:
            session_end_local = session_end_time.astimezone(target_tz)
        else:
            session_end_local = target_tz.localize(session_end_time)
        
        # Include if session started today OR ended today (covers sessions spanning midnight)
        if (session_local_time.date() == local_time.date() or 
            session_end_local.date() == local_time.date()):
            total_cost += block.get('costUSD', 0)
    
    return total_cost


def main():
    """Main monitoring loop."""
    args = parse_args()
    
    # For 'custom_max' plan, we need to get data first to determine the limit
    if args.plan == 'custom_max':
        initial_data = run_ccusage(getattr(args, 'per_project', False), args.project)
        if initial_data and 'blocks' in initial_data:
            token_limit = get_token_limit(args.plan, initial_data['blocks'])
        else:
            token_limit = get_token_limit('pro')  # Fallback to pro
    else:
        token_limit = get_token_limit(args.plan)
    
    try:
        # Initial screen clear and hide cursor
        os.system('clear' if os.name == 'posix' else 'cls')
        print('\033[?25l', end='', flush=True)  # Hide cursor
        
        while True:
            # Move cursor to top without clearing
            print('\033[H', end='', flush=True)
            
            data = run_ccusage(getattr(args, 'per_project', False), args.project)
            if not data or 'blocks' not in data:
                print("Failed to get usage data")
                continue
            
            # Find the active block
            active_block = None
            for block in data['blocks']:
                if block.get('isActive', False):
                    active_block = block
                    break
            
            if not active_block:
                print("No active session found")
                continue
            
            # Extract data from active block
            tokens_used = active_block.get('totalTokens', 0)
            cost_usd = active_block.get('costUSD', 0)
            
            # Get model info
            models = active_block.get('models', [])
            # Filter out synthetic models and get the first real model
            real_models = [m for m in models if '<synthetic>' not in m]
            model_name = real_models[0] if real_models else 'unknown'
            # Shorten model name for display
            if 'opus-4' in model_name:
                model_display = 'Opus 4'
            elif 'sonnet' in model_name:
                model_display = 'Sonnet'
            elif 'haiku' in model_name:
                model_display = 'Haiku'
            else:
                model_display = model_name.split('-')[1] if '-' in model_name else model_name
            
            # Check if tokens exceed limit and switch to custom_max if needed
            if tokens_used > token_limit and args.plan == 'pro':
                # Auto-switch to custom_max when pro limit is exceeded
                new_limit = get_token_limit('custom_max', data['blocks'])
                if new_limit > token_limit:
                    token_limit = new_limit
            
            usage_percentage = (tokens_used / token_limit) * 100 if token_limit > 0 else 0
            tokens_left = token_limit - tokens_used
            
            # Time calculations
            start_time_str = active_block.get('startTime')
            if start_time_str:
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                current_time = datetime.now(start_time.tzinfo)
                elapsed = current_time - start_time
                elapsed_minutes = elapsed.total_seconds() / 60
            else:
                elapsed_minutes = 0
            
            session_duration = 300  # 5 hours in minutes
            remaining_minutes = max(0, session_duration - elapsed_minutes)
            
            # Calculate burn rate from ALL sessions in the last hour
            burn_rate = calculate_hourly_burn_rate(data['blocks'], current_time)
            cost_burn_rate = calculate_hourly_cost_burn_rate(data['blocks'], current_time)
            
            # Reset time calculation - use fixed schedule or custom hour with timezone
            reset_time = get_next_reset_time(current_time, args.reset_hour, args.timezone)
            
            # Calculate time to reset
            time_to_reset = reset_time - current_time
            minutes_to_reset = time_to_reset.total_seconds() / 60
            
            # Predicted end calculation - when tokens will run out based on burn rate
            if burn_rate > 0 and tokens_left > 0:
                minutes_to_depletion = tokens_left / burn_rate
                predicted_end_time = current_time + timedelta(minutes=minutes_to_depletion)
            else:
                # If no burn rate or tokens already depleted, use reset time
                predicted_end_time = reset_time
            
            # Color codes
            cyan = '\033[96m'
            green = '\033[92m'
            blue = '\033[94m'
            red = '\033[91m'
            yellow = '\033[93m'
            white = '\033[97m'
            gray = '\033[90m'
            reset = '\033[0m'
            
            # Calculate daily cost
            daily_cost = calculate_daily_cost(data['blocks'], current_time, args.timezone)
            
            # Display header
            print_header()
            
            # Get current project info
            project_info = get_current_project_info()
            
            # Model info and project info
            model_line = f"🤖 {white}Model:{reset} {cyan}{model_display}{reset}"
            if project_info:
                model_line += f" | 📁 {white}Project:{reset} {cyan}{project_info['project_name']}{reset}"
            elif hasattr(args, 'per_project') and getattr(args, 'per_project', False):
                if args.project:
                    model_line += f" | 📁 {white}Project:{reset} {cyan}{args.project}{reset}"
                else:
                    model_line += f" | 📁 {white}Mode:{reset} {cyan}Per-Project{reset}"
            print(model_line)
            print()
            
            # Progress bars
            print(f"📊 {white}Tokens:{reset} {create_token_progress_bar(usage_percentage)}")
            print(f"⏳ {white}Reset:{reset}  {create_time_progress_bar(max(0, 300 - minutes_to_reset), 300)}")
            print()
            
            # Compact stats
            print(f"🎯 {white}{tokens_used:,}{reset}/{gray}{token_limit:,}{reset} ({cyan}{tokens_left:,}{reset} left)")
            print(f"🔥 {yellow}{burn_rate:.1f}{reset} tok/min {get_velocity_indicator(burn_rate)}")
            print()
            
            # Cost tracking
            print(f"💰 {white}Session:{reset} ${green}{cost_usd:.2f}{reset}")
            print(f"📅 {white}Today:{reset}   ${green}{daily_cost:.2f}{reset}")
            print(f"📈 {white}Rate:{reset}    ${yellow}{cost_burn_rate:.2f}{reset}/hr")
            print()
            
            # Predictions - convert to configured timezone for display
            try:
                local_tz = pytz.timezone(args.timezone)
            except:
                local_tz = pytz.timezone('Europe/Warsaw')
            predicted_end_local = predicted_end_time.astimezone(local_tz)
            reset_time_local = reset_time.astimezone(local_tz)
            
            predicted_end_str = predicted_end_local.strftime("%H:%M")
            reset_time_str = reset_time_local.strftime("%H:%M")
            print(f"🏁 {white}End:{reset} {predicted_end_str} | 🔄 {white}Reset:{reset} {reset_time_str}")
            print()
            
            # Show notifications
            if tokens_used > 7000 and args.plan == 'pro' and token_limit > 7000:
                print(f"🔄 {yellow}Switched to custom_max{reset}")
            
            if tokens_used > token_limit:
                print(f"🚨 {red}TOKENS EXCEEDED!{reset}")
            
            # Warning if tokens will run out before reset
            if predicted_end_time < reset_time:
                print(f"⚠️  {red}Tokens depleting fast!{reset}")
            
            # Status line - compact
            current_time_str = datetime.now().strftime("%H:%M:%S")
            print(f"{gray}{current_time_str} | Ctrl+C to exit{reset}")
            
            # Clear any remaining lines below to prevent artifacts
            print('\033[J', end='', flush=True)
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        # Show cursor before exiting
        print('\033[?25h', end='', flush=True)
        print(f"\n\n{cyan}Monitoring stopped.{reset}")
        # Clear the terminal
        os.system('clear' if os.name == 'posix' else 'cls')
        sys.exit(0)
    except Exception:
        # Show cursor on any error
        print('\033[?25h', end='', flush=True)
        raise


if __name__ == "__main__":
    main()