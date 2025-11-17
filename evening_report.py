#!/usr/bin/env python3
"""
EVENING REPORT
Daily market recap - price action, divergences, and tomorrow's watch list
Run at 6 PM daily

UPDATED: November 9, 2025 - Added seasonal patterns section
"""

from crypto_monitor import *
from config import *
from divergence_reporter import (
    get_fear_greed_index,
    get_rsi_for_coin,
    get_rsi_for_coin_daily,
    get_volume_comparison,
    calculate_rsi
)
from catalyst_tracker import detect_potential_etf_wave, get_all_seasonal_signals, get_all_etf_waves, get_upcoming_catalysts, CATALYSTS
import time
import requests
from datetime import datetime

def get_historical_price_with_retry(coin_id, days_ago, max_retries=3):
    """Get historical price with retry logic"""
    for attempt in range(max_retries):
        try:
            price = get_historical_price(coin_id, days_ago)
            if price:
                return price
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                print(f"  Retry {attempt + 1} for {coin_id} after {wait_time}s...")
                time.sleep(wait_time + 45)
        except Exception as e:
            print(f"  Error fetching {coin_id}: {e}")
            if attempt < max_retries - 1:
                time.sleep(8)
    return None

def generate_evening_report():
    """Generate evening market recap"""

    current_time = get_montevideo_time()

    print(f"=" * 70)
    print(f"EVENING REPORT - {current_time.strftime('%A, %B %d, %Y')}")
    print(f"=" * 70)

    # Get current prices
    print("Fetching current prices...")
    current_data = get_current_prices()
    if not current_data:
        send_telegram_message("❌ Error fetching current prices")
        return

    # Get Fear & Greed
    fg_value, fg_classification = get_fear_greed_index()

    # Bitcoin data
    btc_data = current_data.get(BITCOIN_ID, {})
    btc_price = btc_data.get('usd', 0)
    btc_24h_change = btc_data.get('usd_24h_change', 0)

    # ETH data
    eth_data = current_data.get('ethereum', {})
    eth_price = eth_data.get('usd', 0)
    eth_24h_change = eth_data.get('usd_24h_change', 0)

    # ATOM data
    atom_data = current_data.get('cosmos', {})
    atom_price = atom_data.get('usd', 0)
    atom_24h_change = atom_data.get('usd_24h_change', 0)

    # Gold data - fetch explicitly
    gold_price = 0
    gold_24h_change = 0

    # Try from current_data first
    gold_data = current_data.get('pax-gold', {})
    if gold_data:
        gold_price = gold_data.get('usd', 0)
        gold_24h_change = gold_data.get('usd_24h_change', 0)

    # If still 0, fetch directly
    if gold_price == 0:
        print("Fetching Gold price directly...")
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': 'pax-gold',
            'vs_currencies': 'usd',
            'include_24hr_change': 'true'
        }
        try:
            time.sleep(2)
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                gold_direct = response.json().get('pax-gold', {})
                gold_price = gold_direct.get('usd', 0)
                gold_24h_change = gold_direct.get('usd_24h_change', 0)
        except Exception as e:
            print(f"Error fetching gold: {e}")

    # Get BTC volume
    btc_volume_vs_avg = get_volume_comparison('BTC')

    # Get BTC RSI
    btc_rsi = get_rsi_for_coin('BTC')

    # Get EUR/USD
    print("Fetching EUR/USD...")
    api_key = "7fd7e4bd0c4be5b5d382faaa64e8d9ee"
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        'series_id': 'DEXUSEU',
        'api_key': api_key,
        'file_type': 'json',
        'sort_order': 'desc',
        'limit': 5
    }

    eur_usd_today = None
    eur_usd_yesterday = None

    try:
        time.sleep(2)
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if 'observations' in data and len(data['observations']) > 0:
                for i, obs in enumerate(data['observations']):
                    value = obs.get('value', '.')
                    if value != '.':
                        if not eur_usd_today:
                            eur_usd_today = float(value)
                        elif not eur_usd_yesterday:
                            eur_usd_yesterday = float(value)
                            break
    except:
        pass

    eur_usd_change = 0
    if eur_usd_today and eur_usd_yesterday:
        eur_usd_change = ((eur_usd_today - eur_usd_yesterday) / eur_usd_yesterday) * 100

    # Get DXY (Dollar Index)
    print("Fetching DXY...")
    dxy_url = "https://api.stlouisfed.org/fred/series/observations"
    dxy_params = {
        'series_id': 'DTWEXBGS',
        'api_key': api_key,
        'file_type': 'json',
        'sort_order': 'desc',
        'limit': 5
    }

    dxy_today = None
    dxy_yesterday = None

    try:
        time.sleep(2)
        response = requests.get(dxy_url, params=dxy_params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if 'observations' in data and len(data['observations']) > 0:
                for i, obs in enumerate(data['observations']):
                    value = obs.get('value', '.')
                    if value != '.':
                        if not dxy_today:
                            dxy_today = float(value)
                        elif not dxy_yesterday:
                            dxy_yesterday = float(value)
                            break
    except:
        pass

    dxy_change = 0
    if dxy_today and dxy_yesterday:
        dxy_change = ((dxy_today - dxy_yesterday) / dxy_yesterday) * 100

    # ========== BUILD MESSAGE ==========
    message = f"🌙 <b>EVENING REPORT</b>\n"
    message += f"📅 {current_time.strftime('%A, %B %d, %Y')}\n"
    message += f"🕐 {current_time.strftime('%H:%M %Z')}\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"

    # ========== SECTION 1: TODAY'S LEADERS ==========
    message += "📊 <b>TODAY'S PERFORMANCE</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"

    # BTC
    btc_emoji = "🟢" if btc_24h_change > 0 else "🔴" if btc_24h_change < -2 else "🟡"
    message += f"{btc_emoji} <b>BTC:</b> ${btc_price:,.0f} ({btc_24h_change:+.2f}%%)\n"

    if btc_rsi:
        rsi_status = "Oversold" if btc_rsi < 30 else "Overbought" if btc_rsi > 70 else "Neutral"
        message += f"   RSI: {btc_rsi:.0f} ({rsi_status})"

    if btc_volume_vs_avg:
        vol_status = "High" if btc_volume_vs_avg > 20 else "Low" if btc_volume_vs_avg < -20 else "Normal"
        message += f" | Vol: {vol_status} ({btc_volume_vs_avg:+.0f}%% vs avg)"

    message += "\n\n"

    # ETH
    eth_emoji = "🟢" if eth_24h_change > 0 else "🔴" if eth_24h_change < -2 else "🟡"
    message += f"{eth_emoji} <b>ETH:</b> ${eth_price:,.2f} ({eth_24h_change:+.2f}%%)\n\n"

    # ATOM
    atom_emoji = "🟢" if atom_24h_change > 0 else "🔴" if atom_24h_change < -2 else "🟡"
    message += f"{atom_emoji} <b>ATOM:</b> ${atom_price:.2f} ({atom_24h_change:+.2f}%%)\n"
    message += f"   <i>Unlock: Nov 19-20 (11 days)</i>\n\n"

    # Gold
    gold_emoji = "🟢" if gold_24h_change > 0 else "🔴" if gold_24h_change < 0 else "🟡"
    message += f"{gold_emoji} <b>GOLD:</b> ${gold_price:,.0f} ({gold_24h_change:+.2f}%%)\n\n"

    # Dollar
    if eur_usd_today:
        dollar_emoji = "🔴" if eur_usd_change > 0 else "🟢" if eur_usd_change < 0 else "🟡"
        dollar_interpretation = "weaker" if eur_usd_change > 0 else "stronger" if eur_usd_change < 0 else "flat"
        message += f"{dollar_emoji} <b>DOLLAR:</b> €{eur_usd_today:.4f} ({eur_usd_change:+.2f}%% - {dollar_interpretation})\n"

    # Add DXY if available
    if dxy_today:
        dxy_emoji = "🟢" if dxy_change > 0 else "🔴" if dxy_change < 0 else "🟡"
        message += f"   DXY: {dxy_today:.2f} ({dxy_change:+.2f}%%)\n"

    message += "\n"

    # Market Sentiment
    if fg_value:
        if fg_value < 25:
            sentiment = "😱 EXTREME FEAR"
        elif fg_value < 45:
            sentiment = "😰 FEAR"
        elif fg_value < 55:
            sentiment = "😐 NEUTRAL"
        elif fg_value < 75:
            sentiment = "😊 GREED"
        else:
            sentiment = "🤑 EXTREME GREED"

        message += f"<b>Sentiment:</b> {sentiment} ({fg_value})\n\n"

    # ========== SECTION 2: ALT DIVERGENCES ==========
    message += "━━━━━━━━━━━━━━━━━━━━\n"
    message += "📈 <b>ALT DIVERGENCES (vs BTC)</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"

    print("Calculating alt divergences...")

    alt_performances = []

    print(f"DEBUG: Number of altcoins to check: {len(ALTCOINS)}")

    for coin_id, symbol in ALTCOINS.items():
        print(f"DEBUG: Processing {symbol} ({coin_id})")

        if coin_id == 'pax-gold':
            print(f"DEBUG: Skipping gold")
            continue

        alt_data = current_data.get(coin_id, {})
        alt_price = alt_data.get('usd', 0)
        alt_24h_change = alt_data.get('usd_24h_change', 0)

        print(f"DEBUG: {symbol} - price: {alt_price}, change: {alt_24h_change}")

        if alt_price > 0 and alt_24h_change != 0:
            divergence = alt_24h_change - btc_24h_change

            # Get RSI for this alt (with delay to avoid rate limits)
            time.sleep(1.5)
            alt_rsi = get_rsi_for_coin_daily(symbol)

            alt_performances.append({
                'symbol': symbol,
                'coin_id': coin_id,
                'price': alt_price,
                'change': alt_24h_change,
                'divergence': divergence,
                'rsi': alt_rsi
            })
            print(f"DEBUG: Added {symbol} to performances")
        else:
            print(f"DEBUG: Skipped {symbol} - no valid data")

    print(f"DEBUG: Total alts in performance list: {len(alt_performances)}")

    # Sort by divergence (best to worst)
    alt_performances.sort(key=lambda x: x['divergence'], reverse=True)

    # Display ALL alts with emoji based on divergence
    if alt_performances:
        for alt in alt_performances:
            div = alt['divergence']

            # Emoji based on divergence strength
            if div > 5:
                emoji = "🔥"
            elif div > 2:
                emoji = "🟢"
            elif div > -2:
                emoji = "⚪"
            elif div > -5:
                emoji = "🟡"
            else:
                emoji = "🔴"

            # Build the line with RSI (convert to decimal format)
            change_decimal = alt['change'] / 100
            div_decimal = div / 100
            line = f"{emoji} <b>{alt['symbol']}:</b> {change_decimal:+.4f} (div: {div_decimal:+.4f})"

            # Add RSI if available
            if alt['rsi']:
                rsi_indicator = "🔥" if alt['rsi'] < 30 else "❄️" if alt['rsi'] > 70 else ""
                line += f" | RSI: {alt['rsi']:.0f}{rsi_indicator}"

            message += line + "\n"

        message += "\n"

    # ========== NEW SECTION: ETF WAVE DETECTION ==========
    message += "━━━━━━━━━━━━━━━━━━━━\n"
    message += "💎 <b>ETF WAVE DETECTOR</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"

    # Identify coins pumping >5%
    pumping_coins = [alt['coin_id'] for alt in alt_performances if alt['change'] > 5]

    print(f"DEBUG: Pumping coins (>5%%): {pumping_coins}")

    if len(pumping_coins) >= 3:
        # Run detection
        alert = detect_potential_etf_wave(pumping_coins, threshold_days=30)

        if alert:
            if alert['type'] == 'known_wave':
                # Matches known ETF wave
                matching_symbols = [ALTCOINS.get(c, c.upper()) for c in alert['matching_coins']]
                message += f"✅ <b>KNOWN ETF WAVE DETECTED</b>\n"
                message += f"   {alert['wave']['description']}\n"
                message += f"   Status: {alert['wave']['status'].upper()}\n"
                message += f"   Matching pumps: {', '.join(matching_symbols)}\n"
                message += f"   Days until: {alert['wave'].get('days_until', 'N/A')}\n\n"
                message += f"💡 This coordinated pump is likely driven by ETF speculation\n\n"

            elif alert['type'] == 'unknown_wave':
                # Unknown coordinated pump - research needed
                pump_symbols = [ALTCOINS.get(c, c.upper()) for c in alert['coins']]
                message += f"🚨 <b>UNKNOWN WAVE - RESEARCH NEEDED</b>\n"
                message += f"   {len(alert['coins'])} coins pumping together: {', '.join(pump_symbols)}\n\n"
                message += f"💡 <b>Action Required:</b>\n"
                message += f"   {alert['action']}\n\n"
    else:
        # No coordinated pump detected
        if pumping_coins:
            pump_symbols = [ALTCOINS.get(c, c.upper()) for c in pumping_coins]
            message += f"✅ No ETF wave pattern detected\n"
            message += f"   Pumping coins: {', '.join(pump_symbols)} (individual moves)\n\n"
        else:
            message += f"✅ No significant pumps today (threshold: >5%%)\n\n"

    # ========== NEW SECTION: SEASONAL PATTERNS ==========
    message += "━━━━━━━━━━━━━━━━━━━━\n"
    message += "📈 <b>SEASONAL PATTERNS</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"

    # Get current month and next month signals
    current_month = datetime.now().month
    next_month = (current_month % 12) + 1

    current_signals = get_all_seasonal_signals(current_month)
    next_signals = get_all_seasonal_signals(next_month)

    # Current month seasonality
    current_month_name = current_signals['month_name']
    if current_signals['signals']:
        message += f"<b>{current_month_name} (This Month):</b>\n"

        # Group by signal type
        bullish = [s for s in current_signals['signals'] if s['signal'] == 'bullish']
        bearish = [s for s in current_signals['signals'] if s['signal'] == 'bearish']

        if bullish:
            message += "🟢 <b>Historically Strong:</b>\n"
            for s in bullish:
                conf_indicator = "🔥" if s['confidence'] == 'high' else "✓" if s['confidence'] == 'medium' else "•"
                message += f"   {conf_indicator} <b>{s['symbol']}</b>"

                # Add brief context for high confidence patterns
                if s['confidence'] == 'high':
                    # Extract key stat from notes
                    if 'strongest month' in s['notes']:
                        message += " - strongest month"
                    elif 'avg' in s['notes'].lower():
                        import re
                        avg_match = re.search(r'(\d+\.?\d*)%', s['notes'])
                        if avg_match:
                            message += f" ({avg_match.group(1)}% avg)"

                message += "\n"
            message += "\n"

        if bearish:
            message += "🔴 <b>Historically Weak:</b>\n"
            for s in bearish:
                conf_indicator = "❄️" if s['confidence'] == 'high' else "✓" if s['confidence'] == 'medium' else "•"
                message += f"   {conf_indicator} <b>{s['symbol']}</b>\n"
            message += "\n"
    else:
        message += f"<i>No strong seasonal signals for {current_month_name}</i>\n\n"

    # Next month preview (only show if different from current)
    next_month_name = next_signals['month_name']
    if next_signals['signals']:
        # Check if next month has different signals than current
        next_bullish = {s['symbol'] for s in next_signals['signals'] if s['signal'] == 'bullish'}
        current_bullish = {s['symbol'] for s in current_signals['signals'] if s['signal'] == 'bullish'}

        if next_bullish != current_bullish:
            message += f"<b>{next_month_name} (Next Month) Preview:</b>\n"

            # Show what changes
            new_bullish = next_bullish - current_bullish
            leaving_bullish = current_bullish - next_bullish

            if new_bullish:
                symbols_list = [s['symbol'] for s in next_signals['signals'] if s['symbol'] in new_bullish]
                message += f"   🟢 Turning strong: {', '.join(symbols_list)}\n"

            if leaving_bullish:
                symbols_list = [s['symbol'] for s in current_signals['signals'] if s['symbol'] in leaving_bullish]
                message += f"   🟡 Leaving strong period: {', '.join(symbols_list)}\n"

            message += "\n"

    # Add context note
    message += "<i>📊 Seasonal patterns = historical tendencies, not guarantees. Catalysts override seasonality.</i>\n\n"

    # ========== SECTION 4: UPCOMING CATALYSTS ==========
    etf_waves_30d = get_all_etf_waves(days_ahead=30)
    has_catalysts_30d = any(get_upcoming_catalysts(coin_id, days_ahead=30) for coin_id in CATALYSTS.keys())

    if etf_waves_30d or has_catalysts_30d:
        message += "━━━━━━━━━━━━━━━━━━━━\n"
        message += "📅 <b>UPCOMING CATALYSTS (30 days)</b>\n"
        message += "━━━━━━━━━━━━━━━━━━━━\n\n"

        # ETF waves first
        if etf_waves_30d:
            message += "💎 <b>ETF WAVES:</b>\n"

            status_emoji_map = {
                "approved": "✅",
                "filed": "📋",
                "pending": "⏳",
                "speculation": "🔮"
            }

            for wave in etf_waves_30d:
                status_emoji = status_emoji_map.get(wave['status'], "❓")
                coin_symbols = [ALTCOINS.get(c, c.upper()) for c in wave['coins']]

                # Highlight urgency
                if wave['days_until'] <= 2:
                    urgency = "🔥🔥 "
                elif wave['days_until'] <= 4:
                    urgency = "🔥 "
                else:
                    urgency = ""

                message += f"{urgency}• Day {wave['days_until']}: {wave['description']} {status_emoji}\n"

                # Add context for imminent events
                if wave['status'] == 'approved' and wave['days_until'] <= 3:
                    message += f"   ⚡ <b>IMMINENT</b> - Watch for volatility\n"
                elif wave['status'] == 'pending' and wave['days_until'] <= 3:
                    message += f"   ⏰ Decision deadline approaching\n"

            message += "\n"

        # Individual catalysts
        all_catalysts_30d = []
        for coin_id in CATALYSTS.keys():
            catalysts = get_upcoming_catalysts(coin_id, days_ahead=30)
            if catalysts:
                symbol = ALTCOINS.get(coin_id, coin_id.upper())
                for c in catalysts:
                    if not c.get('is_etf_wave'):  # Skip duplicates
                        all_catalysts_30d.append({
                            'symbol': symbol,
                            'days': c['days_until'],
                            'event': c['event'],
                            'impact': c['impact']
                        })

        if all_catalysts_30d:
            message += "<b>Individual Catalysts:</b>\n"
            all_catalysts_30d.sort(key=lambda x: x['days'])

            for cat in all_catalysts_30d:
                if cat['impact'].startswith('high'):
                    impact_emoji = "🔥"
                elif cat['impact'].startswith('medium'):
                    impact_emoji = "📅"
                else:
                    impact_emoji = "📌"

                message += f"{impact_emoji} <b>{cat['symbol']}</b> (Day {cat['days']}): {cat['event']}\n"

            message += "\n"

    # ========== SECTION 5: TOMORROW'S WATCH ==========
    message += "━━━━━━━━━━━━━━━━━━━━\n"
    message += "👀 <b>TOMORROW'S WATCH</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"

    # Key levels for BTC
    btc_resistance = round(btc_price * 1.02, -2)  # +2%
    btc_support = round(btc_price * 0.98, -2)     # -2%

    message += f"<b>BTC Levels:</b>\n"
    message += f"• Resistance: ${btc_resistance:,}\n"
    message += f"• Support: ${btc_support:,}\n\n"

    # Market bias
    if btc_24h_change > 2:
        bias = "🟢 Bullish momentum - watch for continuation"
    elif btc_24h_change < -2:
        bias = "🔴 Bearish pressure - watch for support"
    else:
        bias = "🟡 Consolidating - waiting for direction"

    message += f"<b>Bias:</b> {bias}\n\n"

    # Specific watchlist based on divergences
    if alt_performances:
        strong_alts = [a['symbol'] for a in alt_performances if a['divergence'] > 3][:3]
        weak_alts = [a['symbol'] for a in alt_performances if a['divergence'] < -3][-3:]

        if strong_alts:
            message += f"<b>Watch strength:</b> {', '.join(strong_alts)}\n"
        if weak_alts:
            weak_alts.reverse()
            message += f"<b>Watch weakness:</b> {', '.join(weak_alts)}\n"

        message += "\n"

    message += "━━━━━━━━━━━━━━━━━━━━"

    # Send to Telegram
    print("\nSending evening report...")
    send_telegram_message(message)
    print(f"✅ Evening report sent at {current_time.strftime('%H:%M:%S')}")

if __name__ == "__main__":
    generate_evening_report()
