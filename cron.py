#!/usr/bin/env python3
"""
Cron scheduler for Railway
Runs morning report (9 AM), evening report (6 PM), divergence (9 AM, 2 PM, 6 PM)
Signal checker runs continuously every 15 minutes
"""
import schedule
import time
import subprocess
from datetime import datetime
import pytz

TIMEZONE = 'America/Montevideo'

def run_morning_report():
    print(f"\n{'='*70}")
    print(f"Running MORNING REPORT at {datetime.now(pytz.timezone(TIMEZONE)).strftime('%H:%M:%S')}")
    print(f"{'='*70}")
    subprocess.run(['python3', 'morning_report.py'])

def run_evening_report():
    print(f"\n{'='*70}")
    print(f"Running EVENING REPORT at {datetime.now(pytz.timezone(TIMEZONE)).strftime('%H:%M:%S')}")
    print(f"{'='*70}")
    subprocess.run(['python3', 'evening_report.py'])

def run_divergence_report():
    print(f"\n{'='*70}")
    print(f"Running DIVERGENCE REPORT at {datetime.now(pytz.timezone(TIMEZONE)).strftime('%H:%M:%S')}")
    print(f"{'='*70}")
    subprocess.run(['python3', 'divergence_reporter.py'])

def run_signal_checker():
    print(f"\n{'='*70}")
    print(f"Running SIGNAL CHECKER at {datetime.now(pytz.timezone(TIMEZONE)).strftime('%H:%M:%S')}")
    print(f"{'='*70}")
    subprocess.run(['python3', 'signal_checker.py'])

# Schedule jobs (Montevideo time)
schedule.every().day.at("09:00").do(run_morning_report)
schedule.every().day.at("18:00").do(run_evening_report)
schedule.every().day.at("09:00").do(run_divergence_report)
schedule.every().day.at("14:00").do(run_divergence_report)
schedule.every().day.at("18:00").do(run_divergence_report)

# Signal checker every 15 minutes
schedule.every(15).minutes.do(run_signal_checker)

print("🤖 Bot scheduler started!")
print("📅 Morning Report: 9 AM")
print("📅 Evening Report: 6 PM")
print("📅 Divergence: 9 AM, 2 PM, 6 PM")
print("📅 Signals: Every 15 minutes")
print(f"🌍 Timezone: {TIMEZONE}")
print("\nWaiting for scheduled tasks...\n")

# Run signal checker immediately on startup
run_signal_checker()

# Keep running
while True:
    schedule.run_pending()
    time.sleep(60)  # Check every minute
