#!/usr/bin/env python3
"""
Always-on task that checks for buy/sell/spike signals every minute
"""
import time
import sys
from signal_checker import check_all_signals, get_altcoin_catalysts_summary
from crypto_monitor import send_telegram_message, get_montevideo_time

def main():
    """Main loop - runs forever, checking every minute"""

    # Send startup notification
    try:
        msg = f"🟢 <b>Crypto Signal Monitor Started</b>\n\n"
        msg += f"⏰ {get_montevideo_time().strftime('%Y-%m-%d %H:%M %Z')}\n"
        msg += f"🔍 Checking every 1 minute\n"
        msg += f"📊 Monitoring: Acceleration, Momentum, Spikes\n"
        msg += f"🥇 Gold & BTC level breaks\n"
        msg += f"🔄 Gold/BTC rotation signals\n"

        # Add catalyst info
        catalysts = get_altcoin_catalysts_summary()
        if catalysts:
            msg += f"\n📅 <b>Active Catalysts:</b>\n"
            msg += f"{' | '.join(catalysts)}"
        else:
            msg += f"\n📅 No upcoming catalysts in next 7 days"

        send_telegram_message(msg)
        print("=" * 70)
        print("🟢 CRYPTO SIGNAL MONITOR STARTED")
        print("=" * 70)
        print(f"Started at: {get_montevideo_time().strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print("Check interval: 1 minute")
        print("Monitoring:")
        print("  • BTC Acceleration alerts")
        print("  • BTC Momentum alerts")
        print("  • BTC Spike alerts")
        print("  • BTC Key Level breaks ($1000 increments)")
        print("  • Gold Key Level breaks ($100 increments)")
        print("  • Gold/BTC Rotation signals")

        if catalysts:
            print(f"\nActive catalysts: {', '.join(catalysts)}")
        else:
            print("\nNo active catalysts")

        print("\nPress Ctrl+C to stop")
        print("=" * 70)

    except Exception as e:
        print(f"Error sending startup message: {e}")

    # Main infinite loop
    while True:
        try:
            check_all_signals()

            print(f"Next check in 1 minute...")
            time.sleep(60)  # Sleep for 1 minute

        except KeyboardInterrupt:
            print("\n" + "=" * 70)
            print("👋 Signal monitor stopped by user")
            print("=" * 70)
            try:
                msg = f"🔴 <b>Crypto Signal Monitor Stopped</b>\n\n"
                msg += f"⏰ {get_montevideo_time().strftime('%Y-%m-%d %H:%M %Z')}"
                send_telegram_message(msg)
            except:
                pass
            sys.exit(0)

        except Exception as e:
            print(f"\n❌ ERROR in signal check: {e}")
            print("Waiting 2 minutes before retry...")

            # Try to send error notification
            try:
                error_msg = f"⚠️ <b>Signal Monitor Error</b>\n\n"
                error_msg += f"Error: {str(e)[:200]}\n"
                error_msg += f"Retrying in 2 minutes...\n"
                error_msg += f"⏰ {get_montevideo_time().strftime('%H:%M %Z')}"
                send_telegram_message(error_msg)
            except:
                pass

            time.sleep(120)

if __name__ == "__main__":
    main()