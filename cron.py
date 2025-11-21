#!/usr/bin/env python3
"""
Cron scheduler for Railway
Runs:
- Morning report (9 AM)
- Evening report (6 PM)
- Weekly report (Sunday 8 AM)
- Signal checker (continuously every 1 minute)

UPDATED: November 21, 2025 - Added weekly report scheduling
"""
import schedule
import time
from datetime import datetime
import pytz
import os

TIMEZONE = 'America/Montevideo'

# Verify environment variables are loaded
print(f"DEBUG at cron start: Token exists = {bool(os.environ.get('TELEGRAM_BOT_TOKEN'))}")
print(f"DEBUG at cron start: Chat ID exists = {bool(os.environ.get('TELEGRAM_CHAT_ID'))}")
print(f"\nDEBUG: Checking all environment variables:")
print(f"Total env vars available: {len(os.environ)}")
print("First 15 env var names:")
for i, key in enumerate(sorted(os.environ.keys())[:15]):
    value = os.environ[key]
    # Mask sensitive data
    if 'TOKEN' in key or 'KEY' in key or 'SECRET' in key:
        display = f"{value[:5]}..." if len(value) > 5 else "***"
    else:
        display = value[:50]
    print(f"  {i+1}. {key} = {display}")
print()

def run_morning_report():
    print(f"\n{'='*70}")
    print(f"Running MORNING REPORT at {datetime.now(pytz.timezone(TIMEZONE)).strftime('%H:%M:%S')}")
    print(f"{'='*70}")
    from morning_report import generate_morning_report
    generate_morning_report()

def run_evening_report():
    print(f"\n{'='*70}")
    print(f"Running EVENING REPORT at {datetime.now(pytz.timezone(TIMEZONE)).strftime('%H:%M:%S')}")
    print(f"{'='*70}")
    from evening_report import generate_evening_report
    generate_evening_report()

def run_weekly_report():
    print(f"\n{'='*70}")
    print(f"Running WEEKLY REPORT at {datetime.now(pytz.timezone(TIMEZONE)).strftime('%H:%M:%S')}")
    print(f"{'='*70}")
    from weekly_report import generate_weekly_report
    generate_weekly_report()

def run_signal_checker():
    print(f"\n{'='*70}")
    print(f"Running SIGNAL CHECKER at {datetime.now(pytz.timezone(TIMEZONE)).strftime('%H:%M:%S')}")
    print(f"{'='*70}")
    from signal_checker import check_all_signals
    check_all_signals()

# Schedule daily jobs (Montevideo time)
schedule.every().day.at("09:00").do(run_morning_report)
schedule.every().day.at("18:00").do(run_evening_report)

# Schedule weekly report (Sunday 8 AM Montevideo time)
schedule.every().sunday.at("08:00").do(run_weekly_report)

# Signal checker every 1 minute
schedule.every(1).minutes.do(run_signal_checker)

print("🤖 Bot scheduler started!")
print("📅 Morning Report: 9 AM daily")
print("📅 Evening Report: 6 PM daily")
print("📅 Weekly Report: Sunday 8 AM")
print("📅 Signals: Every 1 minute")
print(f"🌍 Timezone: {TIMEZONE}")
print("\nWaiting for scheduled tasks...\n")

# Run signal checker immediately on startup
run_signal_checker()

# Keep running
while True:
    schedule.run_pending()
    time.sleep(30)
