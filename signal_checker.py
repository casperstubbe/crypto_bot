#!/usr/bin/env python3
from crypto_monitor import *
from config import *
import time
from datetime import datetime, timedelta
from catalyst_tracker import get_catalyst_marker, get_upcoming_catalysts

# ============================================
# ALERT SETTINGS (easily adjustable)
# ============================================
ALERT_ENABLED = True  # Master switch for all alerts

# ============================================
# ALERT 1: ACCELERATION
# ============================================
ALERT_ACCELERATION_ENABLED = True
ALERT_ACCELERATION_PERIOD = 30
ALERT_ACCELERATION_MIN_DIFF = 0.5
ALERT_ACCELERATION_COOLDOWN = 30

# ============================================
# ALERT 2: MOMENTUM
# ============================================
ALERT_MOMENTUM_ENABLED = True
ALERT_MOMENTUM_PERIOD = 5
ALERT_MOMENTUM_COUNT = 4
ALERT_MOMENTUM_MIN_CHANGE = 0.2
ALERT_MOMENTUM_DIRECTION = 'both'
ALERT_MOMENTUM_COOLDOWN = 60

# ============================================
# ALERT 3: SPIKE
# ============================================
ALERT_SPIKE_ENABLED = True
ALERT_SPIKE_PERIOD = 5
ALERT_SPIKE_THRESHOLD = 0.6
ALERT_SPIKE_COOLDOWN = 120

# ============================================
# ALERT 4: GOLD KEY LEVEL BREAKS
# ============================================
ALERT_GOLD_ENABLED = True
ALERT_GOLD_COOLDOWN = 180
ALERT_GOLD_ROUND_INCREMENT = 100

# ============================================
# ALERT 5: GOLD/BTC ROTATION SIGNALS
# ============================================
ALERT_ROTATION_ENABLED = True
ALERT_ROTATION_THRESHOLD_MODERATE = 2.5
ALERT_ROTATION_THRESHOLD_STRONG = 4.0
ALERT_ROTATION_COOLDOWN = 600

# ============================================
# ALERT 6: BTC KEY LEVEL BREAKS
# ============================================
ALERT_BTC_LEVEL_ENABLED = True
ALERT_BTC_ROUND_INCREMENT = 2000
ALERT_BTC_COOLDOWN = 240

# ============================================
# ALERT 7: ETH/BTC RATIO BREAKS
# ============================================
ALERT_ETH_BTC_ENABLED = True
ALERT_ETH_BTC_LEVELS = [0.035, 0.040, 0.045, 0.050, 0.055, 0.060]
ALERT_ETH_BTC_DIVERGENCE_THRESHOLD = 3.0
ALERT_ETH_BTC_COOLDOWN = 90
ALERT_ETH_BTC_MIN_VOLUME = -50

# ============================================
# ALERT 8: BTC DOMINANCE SHIFTS
# ============================================
ALERT_BTC_DOM_ENABLED = True
ALERT_BTC_DOM_THRESHOLDS = [54.0, 56.0, 57.5, 58.5]
ALERT_BTC_DOM_MOMENTUM_THRESHOLD = 0.4
ALERT_BTC_DOM_COOLDOWN = 180

# ============================================
# ALERT 9: DERIVATIVES EXTREMES (Funding + OI)
# Triggers on dangerous leverage conditions
# ============================================
ALERT_DERIVATIVES_ENABLED = True
ALERT_DERIVATIVES_FUNDING_EXTREME = 0.08  # 0.08% per 8hrs = danger zone
ALERT_DERIVATIVES_FUNDING_VERY_EXTREME = 0.10  # 0.10% = red alert
ALERT_DERIVATIVES_OI_HIGH = 30  # $30B = elevated
ALERT_DERIVATIVES_OI_EXTREME = 35  # $35B = danger
ALERT_DERIVATIVES_COOLDOWN = 360  # 6 hours (rare, important alerts)

# ============================================

# Global variables to track cooldowns
last_alert_acceleration_time = None
last_alert_momentum_time = None
last_alert_spike_time = None
last_alert_gold_time = None
last_gold_check_price = None
last_alert_rotation_time = None
last_alert_btc_level_time = None
last_btc_check_price = None
last_alert_eth_btc_time = None
last_eth_btc_check_ratio = None
last_alert_btc_dom_time = None
last_btc_dom_check = None
last_alert_derivatives_time = None

def get_market_context():
    """Get macro market context for alt trading"""

    context = {
        'btc_dominance': None,
        'btc_dom_signal': None,
        'eth_btc_ratio': None,
        'eth_btc_trend': None,
        'eth_btc_signal': None,
        'alt_volume_share': None,
        'alt_vol_signal': None
    }

    try:
        # 1. BTC Dominance
        url_global = "https://api.coingecko.com/api/v3/global"
        response_global = requests.get(url_global, timeout=10)

        if response_global.status_code == 200:
            global_data = response_global.json()
            btc_dom = global_data.get('data', {}).get('market_cap_percentage', {}).get('btc', 0)
            context['btc_dominance'] = round(btc_dom, 2)

            if btc_dom < 57:
                context['btc_dom_signal'] = 'BUY'
            elif btc_dom > 60:
                context['btc_dom_signal'] = 'SELL'
            else:
                context['btc_dom_signal'] = 'NEUTRAL'

        time.sleep(2)

        # 2. ETH/BTC ratio
        url_eth_btc = "https://min-api.cryptocompare.com/data/v2/histohour"
        params_eth_btc = {'fsym': 'ETH', 'tsym': 'BTC', 'limit': 480}

        response_eth_btc = requests.get(url_eth_btc, params=params_eth_btc, timeout=10)

        if response_eth_btc.status_code == 200:
            eth_btc_data = response_eth_btc.json()
            if 'Data' in eth_btc_data and 'Data' in eth_btc_data['Data']:
                candles = eth_btc_data['Data']['Data']
                current_ratio = candles[-1]['close']
                context['eth_btc_ratio'] = round(current_ratio, 6)

                prices = [c['close'] for c in candles]
                ma_20d = sum(prices) / len(prices)

                ratio_7d_ago = candles[-168]['close']
                trend_7d = ((current_ratio - ratio_7d_ago) / ratio_7d_ago) * 100
                context['eth_btc_trend'] = round(trend_7d, 2)

                if current_ratio > ma_20d and trend_7d > 0:
                    context['eth_btc_signal'] = 'BUY'
                elif current_ratio < ma_20d and trend_7d < 0:
                    context['eth_btc_signal'] = 'SELL'
                else:
                    context['eth_btc_signal'] = 'NEUTRAL'

        time.sleep(2)

        # 3. Alt Volume Share
        url_btc_vol = "https://min-api.cryptocompare.com/data/v2/histohour"
        params_btc_vol = {'fsym': 'BTC', 'tsym': 'USD', 'limit': 24}
        response_btc_vol = requests.get(url_btc_vol, params=params_btc_vol, timeout=10)

        btc_volume_24h = 0
        if response_btc_vol.status_code == 200:
            btc_data = response_btc_vol.json()
            if 'Data' in btc_data and 'Data' in btc_data['Data']:
                btc_candles = btc_data['Data']['Data']
                btc_volume_24h = sum([c['volumeto'] for c in btc_candles])

        time.sleep(2)

        url_eth_vol = "https://min-api.cryptocompare.com/data/v2/histohour"
        params_eth_vol = {'fsym': 'ETH', 'tsym': 'USD', 'limit': 24}
        response_eth_vol = requests.get(url_eth_vol, params=params_eth_vol, timeout=10)

        eth_volume_24h = 0
        if response_eth_vol.status_code == 200:
            eth_data = response_eth_vol.json()
            if 'Data' in eth_data and 'Data' in eth_data['Data']:
                eth_candles = eth_data['Data']['Data']
                eth_volume_24h = sum([c['volumeto'] for c in eth_candles])

        combined_volume = btc_volume_24h + eth_volume_24h
        estimated_total_volume = combined_volume / 0.65 if combined_volume > 0 else 0
        alt_volume = estimated_total_volume - btc_volume_24h

        if estimated_total_volume > 0:
            alt_volume_share = (alt_volume / estimated_total_volume) * 100
            context['alt_volume_share'] = round(alt_volume_share, 1)

            if alt_volume_share > 40:
                context['alt_vol_signal'] = 'BUY'
            elif alt_volume_share < 35:
                context['alt_vol_signal'] = 'CAUTION'
            else:
                context['alt_vol_signal'] = 'NEUTRAL'

    except Exception as e:
        print(f"Error fetching market context: {e}")

    return context

def send_alert(message):
    """Send alert to Telegram"""
    send_telegram_message(message)

def get_cryptocompare_data():
    """Get Bitcoin price data from CryptoCompare (no API key needed)"""

    # Get current price
    url_current = "https://min-api.cryptocompare.com/data/price"
    params_current = {
        'fsym': 'BTC',
        'tsyms': 'USD'
    }

    # Get minute-by-minute data for last 2+ hours
    url_historical = "https://min-api.cryptocompare.com/data/v2/histominute"
    params_historical = {
        'fsym': 'BTC',
        'tsym': 'USD',
        'limit': 130  # Get 130 minutes to cover 120min lookback
    }

    try:
        # Get current price
        response_current = requests.get(url_current, params=params_current, timeout=10)
        if response_current.status_code != 200:
            print(f"Error fetching current price: {response_current.status_code}")
            return None

        current_price = response_current.json().get('USD', 0)

        # Get historical data
        response_hist = requests.get(url_historical, params=params_historical, timeout=10)
        if response_hist.status_code != 200:
            print(f"Error fetching historical data: {response_hist.status_code}")
            return None

        hist_data = response_hist.json()

        return {
            'current_price': current_price,
            'historical': hist_data
        }

    except Exception as e:
        print(f"Error fetching CryptoCompare data: {e}")
        return None

def check_cooldown(last_time, cooldown_minutes):
    """Check if enough time has passed since last alert"""
    if not last_time:
        return True

    now = get_montevideo_time()
    time_since_last = (now - last_time).total_seconds() / 60
    return time_since_last >= cooldown_minutes

def get_gold_price():
    """Get current gold price via PAXG"""
    try:
        url = "https://min-api.cryptocompare.com/data/price"
        params = {'fsym': 'PAXG', 'tsyms': 'USD'}
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            return data.get('USD')
        return None
    except Exception as e:
        print(f"Error fetching gold price: {e}")
        return None

def get_altcoin_catalysts_summary():
    """Get summary of upcoming catalysts for all altcoins"""
    catalyst_list = []

    for coin_id, symbol in ALTCOINS.items():
        if coin_id == 'pax-gold':
            continue

        marker = get_catalyst_marker(coin_id, days_ahead=7)
        if marker:
            catalyst_list.append(f"{symbol}{marker}")

    return catalyst_list

def check_alert_acceleration(candles, btc_price):
    """
    ALERT 1: Acceleration
    Recent 30min > previous 30min by at least X%
    Volume: Last 30min vs 24h average 30min
    """
    global last_alert_acceleration_time

    if not ALERT_ENABLED or not ALERT_ACCELERATION_ENABLED:
        return

    # Check cooldown
    if not check_cooldown(last_alert_acceleration_time, ALERT_ACCELERATION_COOLDOWN):
        return

    # Need enough data
    if len(candles) < ALERT_ACCELERATION_PERIOD * 2:
        return

    # Compare two periods
    price_2periods_ago = candles[-(ALERT_ACCELERATION_PERIOD * 2)]['close']
    price_1period_ago = candles[-ALERT_ACCELERATION_PERIOD]['close']

    period1_change = ((price_1period_ago - price_2periods_ago) / price_2periods_ago) * 100
    period2_change = ((btc_price - price_1period_ago) / price_1period_ago) * 100

    # Calculate difference (absolute values to work for both up and down)
    difference = abs(period2_change) - abs(period1_change)

    # Check if difference meets minimum threshold
    has_acceleration = difference >= ALERT_ACCELERATION_MIN_DIFF

    # Calculate volume: Last 30min vs 24h average 30min
    volume_last_30min = sum([candle['volumeto'] for candle in candles[-ALERT_ACCELERATION_PERIOD:]])
    volume_24h_total = sum([candle['volumeto'] for candle in candles])
    periods_in_24h = len(candles)
    volume_per_30min_avg = (volume_24h_total / periods_in_24h) * ALERT_ACCELERATION_PERIOD if periods_in_24h > 0 else 1
    volume_vs_avg = ((volume_last_30min / volume_per_30min_avg) - 1) * 100 if volume_per_30min_avg > 0 else 0

    print(f"  ACCELERATION ALERT:")
    print(f"    Period 1: {period1_change:+.2f}%")
    print(f"    Period 2: {period2_change:+.2f}%")
    print(f"    Difference: {difference:+.2f}% (need ≥{ALERT_ACCELERATION_MIN_DIFF}%)")
    print(f"    Volume (last 30min vs 24h avg 30min): {volume_vs_avg:+.0f}%")
    print(f"    Accelerating: {'✅' if has_acceleration else '❌'}")

    if has_acceleration:
        last_alert_acceleration_time = get_montevideo_time()

        direction = "UP 🚀" if period2_change > 0 else "DOWN ⚠️"
        emoji = "🔥"

        # Get catalysts
        catalysts = get_altcoin_catalysts_summary()

        message = f"{emoji} <b>ACCELERATION ALERT!</b>\n\n"
        message += f"₿ Bitcoin: ${btc_price:,.2f}\n"
        message += f"Direction: <b>{direction}</b>\n\n"
        message += f"Previous {ALERT_ACCELERATION_PERIOD}min: {period1_change:+.2f}%\n"
        message += f"Recent {ALERT_ACCELERATION_PERIOD}min: {period2_change:+.2f}%\n"
        message += f"<b>Difference: {difference:+.2f}%</b>\n\n"
        message += f"💰 Volume (last 30min): {volume_vs_avg:+.0f}% vs avg\n\n"
        message += f"💡 Momentum accelerating - check divergence signals!\n"

        if catalysts:
            message += f"\n📅 <b>Upcoming Catalysts:</b> {' | '.join(catalysts)}\n"

        message += f"\n⏰ {get_montevideo_time().strftime('%H:%M %Z')}"

        send_alert(message)
        print(f"  🔥 ACCELERATION ALERT SENT!")

def check_alert_momentum(candles, btc_price):
    """
    ALERT 2: Consecutive Momentum
    X consecutive Y-min periods, each with >Z% change
    Direction: Can be 'up', 'down', or 'both'
    Volume: Current 5min vs 24h average 5min
    """
    global last_alert_momentum_time

    if not ALERT_ENABLED or not ALERT_MOMENTUM_ENABLED:
        return

    # Check cooldown
    if not check_cooldown(last_alert_momentum_time, ALERT_MOMENTUM_COOLDOWN):
        return

    # Need enough data
    if len(candles) < ALERT_MOMENTUM_PERIOD * ALERT_MOMENTUM_COUNT:
        return

    # Check consecutive periods
    all_positive = True
    all_negative = True
    all_meet_threshold = True
    consecutive_changes = []

    for i in range(ALERT_MOMENTUM_COUNT):
        start_idx = -((i + 1) * ALERT_MOMENTUM_PERIOD)
        end_idx = -(i * ALERT_MOMENTUM_PERIOD) if i > 0 else None

        start_price = candles[start_idx]['close']
        end_price = candles[end_idx]['close'] if end_idx else btc_price

        period_change = ((end_price - start_price) / start_price) * 100
        consecutive_changes.append(period_change)

        # Check if this period meets the minimum threshold
        if abs(period_change) < ALERT_MOMENTUM_MIN_CHANGE:
            all_meet_threshold = False

        # Check direction
        if period_change <= 0:
            all_positive = False
        if period_change >= 0:
            all_negative = False

    consecutive_changes.reverse()  # Show oldest to newest

    # Determine if we should trigger based on direction setting
    should_trigger = False
    detected_direction = None

    if ALERT_MOMENTUM_DIRECTION == 'up':
        should_trigger = all_positive and all_meet_threshold
        detected_direction = 'UP' if should_trigger else None
    elif ALERT_MOMENTUM_DIRECTION == 'down':
        should_trigger = all_negative and all_meet_threshold
        detected_direction = 'DOWN' if should_trigger else None
    elif ALERT_MOMENTUM_DIRECTION == 'both':
        if all_positive and all_meet_threshold:
            should_trigger = True
            detected_direction = 'UP'
        elif all_negative and all_meet_threshold:
            should_trigger = True
            detected_direction = 'DOWN'

    # Calculate volume: Current period vs 24h average
    volume_current_period = sum([candle['volumeto'] for candle in candles[-ALERT_MOMENTUM_PERIOD:]])
    volume_24h_total = sum([candle['volumeto'] for candle in candles])
    periods_in_24h = len(candles)
    volume_per_period_avg = (volume_24h_total / periods_in_24h) * ALERT_MOMENTUM_PERIOD if periods_in_24h > 0 else 1
    volume_vs_avg = ((volume_current_period / volume_per_period_avg) - 1) * 100 if volume_per_period_avg > 0 else 0

    print(f"  MOMENTUM ALERT ({ALERT_MOMENTUM_COUNT}x {ALERT_MOMENTUM_PERIOD}min, each >{ALERT_MOMENTUM_MIN_CHANGE}%, dir:{ALERT_MOMENTUM_DIRECTION}):")
    for idx, change in enumerate(consecutive_changes, 1):
        meets = abs(change) >= ALERT_MOMENTUM_MIN_CHANGE
        print(f"    Period {idx}: {change:+.2f}% {'✅' if meets else '❌'}")
    print(f"    All positive: {'✅' if all_positive else '❌'}")
    print(f"    All negative: {'✅' if all_negative else '❌'}")
    print(f"    Volume (current {ALERT_MOMENTUM_PERIOD}min vs 24h avg): {volume_vs_avg:+.0f}%")
    print(f"    Should trigger: {'✅ YES' if should_trigger else '❌ NO'}")

    if should_trigger:
        last_alert_momentum_time = get_montevideo_time()

        total_periods = ALERT_MOMENTUM_PERIOD * ALERT_MOMENTUM_COUNT
        total_change = ((btc_price - candles[-total_periods]['close']) /
                       candles[-total_periods]['close']) * 100

        # Set emoji based on direction
        if detected_direction == 'UP':
            emoji = "📈"
            direction_text = "UP 🚀"
        else:
            emoji = "📉"
            direction_text = "DOWN ⚠️"

        # Get catalysts
        catalysts = get_altcoin_catalysts_summary()

        message = f"{emoji} <b>MOMENTUM ALERT!</b>\n\n"
        message += f"₿ Bitcoin: ${btc_price:,.2f}\n"
        message += f"Direction: <b>{direction_text}</b>\n\n"
        message += f"<b>{ALERT_MOMENTUM_COUNT} consecutive {ALERT_MOMENTUM_PERIOD}-min periods</b>\n"
        message += f"<b>(each >{ALERT_MOMENTUM_MIN_CHANGE}%):</b>\n"
        for idx, change in enumerate(consecutive_changes, 1):
            message += f"Period {idx}: {change:+.2f}%\n"
        message += f"\nTotal ({total_periods}min): {total_change:+.2f}%\n\n"
        message += f"💰 Volume (current {ALERT_MOMENTUM_PERIOD}min): {volume_vs_avg:+.0f}% vs avg\n\n"
        message += f"💡 Sustained momentum - check divergence opportunities!\n"

        if catalysts:
            message += f"\n📅 <b>Upcoming Catalysts:</b> {' | '.join(catalysts)}\n"

        message += f"\n⏰ {get_montevideo_time().strftime('%H:%M %Z')}"

        send_alert(message)
        print(f"  {emoji} MOMENTUM ALERT SENT! Direction: {detected_direction}")

def check_alert_spike(candles, btc_price):
    """
    ALERT 3: Short-term Spike
    >X% movement in Y minutes
    Volume: Last Y min vs 24h average Y min
    """
    global last_alert_spike_time

    if not ALERT_ENABLED or not ALERT_SPIKE_ENABLED:
        return

    # Check cooldown
    if not check_cooldown(last_alert_spike_time, ALERT_SPIKE_COOLDOWN):
        return

    # Need enough data
    if len(candles) < ALERT_SPIKE_PERIOD:
        return

    # Check spike
    price_ago = candles[-ALERT_SPIKE_PERIOD]['close']
    spike_change = ((btc_price - price_ago) / price_ago) * 100
    has_spike = abs(spike_change) >= ALERT_SPIKE_THRESHOLD

    # Calculate volume: Last period vs 24h average
    volume_last_period = sum([candle['volumeto'] for candle in candles[-ALERT_SPIKE_PERIOD:]])
    volume_24h_total = sum([candle['volumeto'] for candle in candles])
    periods_in_24h = len(candles)
    volume_per_period_avg = (volume_24h_total / periods_in_24h) * ALERT_SPIKE_PERIOD if periods_in_24h > 0 else 1
    volume_vs_avg = ((volume_last_period / volume_per_period_avg) - 1) * 100 if volume_per_period_avg > 0 else 0

    print(f"  SPIKE ALERT ({ALERT_SPIKE_PERIOD}min):")
    print(f"    Change: {spike_change:+.2f}% {'✅' if has_spike else '❌'} (need >{ALERT_SPIKE_THRESHOLD}%)")
    print(f"    Volume (last {ALERT_SPIKE_PERIOD}min vs 24h avg): {volume_vs_avg:+.0f}%")

    if has_spike:
        last_alert_spike_time = get_montevideo_time()

        direction = "UP 🚀" if spike_change > 0 else "DOWN ⚠️"
        emoji = "⚡"

        # Get catalysts
        catalysts = get_altcoin_catalysts_summary()

        message = f"{emoji} <b>SPIKE ALERT!</b> {emoji}\n\n"
        message += f"₿ Bitcoin: ${btc_price:,.2f}\n"
        message += f"Direction: <b>{direction}</b>\n\n"
        message += f"<b>{ALERT_SPIKE_PERIOD}-min change: {spike_change:+.2f}%</b>\n"
        message += f"${price_ago:,.2f} → ${btc_price:,.2f}\n\n"
        message += f"💰 Volume (last {ALERT_SPIKE_PERIOD}min): {volume_vs_avg:+.0f}% vs avg\n\n"
        message += f"💡 Rapid movement - check alt divergences!\n"

        if catalysts:
            message += f"\n📅 <b>Upcoming Catalysts:</b> {' | '.join(catalysts)}\n"

        message += f"\n⏰ {get_montevideo_time().strftime('%H:%M %Z')}"

        send_alert(message)
        print(f"  ⚡ SPIKE ALERT SENT!")

def check_alert_gold():
    """
    ALERT 4: Gold Key Level Breaks (ENHANCED - MORE RESPONSIVE)
    Triggers on:
    - 1h/4h/8h divergence with BTC (faster detection)
    - $50 level breaks (more granular)
    - 7-day high/low breaks
    - Volume spikes
    """
    global last_alert_gold_time, last_gold_check_price

    if not ALERT_ENABLED or not ALERT_GOLD_ENABLED:
        return

    # Check cooldown
    if not check_cooldown(last_alert_gold_time, ALERT_GOLD_COOLDOWN):
        return

    # Get gold data (30 days for volume, 7 days for levels)
    url_gold = "https://min-api.cryptocompare.com/data/v2/histohour"
    params_gold = {
        'fsym': 'PAXG',
        'tsym': 'USD',
        'limit': 720  # 30 days
    }

    try:
        response_gold = requests.get(url_gold, params=params_gold, timeout=10)
        if response_gold.status_code != 200:
            print(f"  🥇 Error fetching gold data")
            return

        data_gold = response_gold.json()
        if 'Data' not in data_gold or 'Data' not in data_gold['Data']:
            print(f"  🥇 Invalid gold data format")
            return

        candles_gold = data_gold['Data']['Data']
        if len(candles_gold) < 168:
            print(f"  🥇 Insufficient gold data")
            return

        # Current gold price
        gold_price = candles_gold[-1]['close']

        # Calculate Gold changes (1h, 4h, 8h, 24h) - MORE RESPONSIVE
        gold_1h_ago = candles_gold[-1]['close']
        gold_1h_change = 0
        if len(candles_gold) >= 2:
            gold_1h_ago = candles_gold[-2]['close']
            gold_1h_change = ((gold_price - gold_1h_ago) / gold_1h_ago) * 100

        gold_4h_ago = candles_gold[-4]['close']
        gold_4h_change = ((gold_price - gold_4h_ago) / gold_4h_ago) * 100

        gold_8h_ago = candles_gold[-8]['close']
        gold_8h_change = ((gold_price - gold_8h_ago) / gold_8h_ago) * 100

        gold_24h_ago = candles_gold[-24]['close']
        gold_24h_change = ((gold_price - gold_24h_ago) / gold_24h_ago) * 100

        # Calculate Gold volume (current hour vs 30d avg) - SPIKE DETECTION
        current_hour_volume = candles_gold[-1]['volumeto']
        total_30d_volume = sum([c['volumeto'] for c in candles_gold])
        avg_hourly_volume = total_30d_volume / len(candles_gold)
        volume_vs_avg = ((current_hour_volume / avg_hourly_volume) - 1) * 100 if avg_hourly_volume > 0 else 0

        # 7-day high and low
        prices_7d = [c['close'] for c in candles_gold[-168:]]
        high_7d = max(prices_7d)
        low_7d = min(prices_7d)

        # Previous check price (to detect crosses)
        prev_price = last_gold_check_price if last_gold_check_price else candles_gold[-2]['close']

        # Check for breakouts
        broke_high = prev_price < high_7d and gold_price >= high_7d
        broke_low = prev_price > low_7d and gold_price <= low_7d

        # Check for $50 level crosses (more granular than $100)
        current_level = (gold_price // 50) * 50
        prev_level = (prev_price // 50) * 50
        crossed_level = current_level != prev_level

        # Get BTC data (1h, 4h, 8h, 24h for multi-timeframe analysis)
        url_btc = "https://min-api.cryptocompare.com/data/v2/histohour"
        params_btc = {
            'fsym': 'BTC',
            'tsym': 'USD',
            'limit': 24
        }

        response_btc = requests.get(url_btc, params=params_btc, timeout=10)
        btc_1h_change = 0
        btc_4h_change = 0
        btc_8h_change = 0
        btc_24h_change = 0
        btc_current = 0
        divergence_1h = 0
        divergence_4h = 0
        divergence_8h = 0
        divergence_24h = 0
        paxg_btc_24h_change = 0

        if response_btc.status_code == 200:
            data_btc = response_btc.json()
            if 'Data' in data_btc and 'Data' in data_btc['Data']:
                candles_btc = data_btc['Data']['Data']
                btc_current = candles_btc[-1]['close']

                # BTC changes at different timeframes
                if len(candles_btc) >= 2:
                    btc_1h_ago_price = candles_btc[-2]['close']
                    btc_1h_change = ((btc_current - btc_1h_ago_price) / btc_1h_ago_price) * 100

                btc_4h_ago_price = candles_btc[-4]['close']
                btc_4h_change = ((btc_current - btc_4h_ago_price) / btc_4h_ago_price) * 100

                btc_8h_ago_price = candles_btc[-8]['close']
                btc_8h_change = ((btc_current - btc_8h_ago_price) / btc_8h_ago_price) * 100

                btc_24h_ago_price = candles_btc[0]['close']
                btc_24h_change = ((btc_current - btc_24h_ago_price) / btc_24h_ago_price) * 100

                # Calculate divergences at multiple timeframes
                divergence_1h = gold_1h_change - btc_1h_change
                divergence_4h = gold_4h_change - btc_4h_change
                divergence_8h = gold_8h_change - btc_8h_change
                divergence_24h = gold_24h_change - btc_24h_change

                # PAXG/BTC 24h change
                paxg_btc_ratio_now = gold_price / btc_current
                paxg_btc_ratio_24h_ago = gold_24h_ago / btc_24h_ago_price
                paxg_btc_24h_change = ((paxg_btc_ratio_now - paxg_btc_ratio_24h_ago) / paxg_btc_ratio_24h_ago) * 100

        # MULTI-TIMEFRAME DIVERGENCE DETECTION
        # Strong signal if multiple timeframes agree
        short_term_divergence = abs(divergence_1h) > 1.0 or abs(divergence_4h) > 2.0
        medium_term_divergence = abs(divergence_8h) > 3.0
        long_term_divergence = abs(divergence_24h) > 4.0

        # Volume spike detection
        volume_spike = volume_vs_avg > 100

        print(f"  GOLD ALERT:")
        print(f"    Current: ${gold_price:,.2f}")
        print(f"    Gold 1h: {gold_1h_change:+.2f}% | BTC 1h: {btc_1h_change:+.2f}% | Div: {divergence_1h:+.2f}%")
        print(f"    Gold 4h: {gold_4h_change:+.2f}% | BTC 4h: {btc_4h_change:+.2f}% | Div: {divergence_4h:+.2f}%")
        print(f"    Gold 8h: {gold_8h_change:+.2f}% | BTC 8h: {btc_8h_change:+.2f}% | Div: {divergence_8h:+.2f}%")
        print(f"    Gold 24h: {gold_24h_change:+.2f}% | BTC 24h: {btc_24h_change:+.2f}% | Div: {divergence_24h:+.2f}%")
        print(f"    Volume: {volume_vs_avg:+.0f}% vs 30d avg {'🔥 SPIKE!' if volume_spike else ''}")
        print(f"    7d High: ${high_7d:,.2f} {'🔴 BROKEN!' if broke_high else ''}")
        print(f"    7d Low: ${low_7d:,.2f} {'🔴 BROKEN!' if broke_low else ''}")
        print(f"    $50 level: ${current_level:,.0f} {'🔴 CROSSED!' if crossed_level else ''}")

        # Update last check price
        last_gold_check_price = gold_price

        # MINIMUM VOLUME CHECK
        if volume_vs_avg < -50:
            print(f"    ❌ Skipping Gold alert - volume too low ({volume_vs_avg:.0f}% < -50%)")
            return

        # TRIGGER CONDITIONS (more sensitive)
        trigger_level_break = broke_high or broke_low or crossed_level
        trigger_divergence = short_term_divergence or medium_term_divergence or long_term_divergence
        trigger_volume = volume_spike

        if trigger_level_break or trigger_divergence or trigger_volume:
            last_alert_gold_time = get_montevideo_time()

            # Determine primary alert type
            if broke_high:
                alert_type = "7-DAY HIGH BROKEN"
                emoji = "🚀"
                detail = f"Broke above ${high_7d:,.2f}"
            elif broke_low:
                alert_type = "7-DAY LOW BROKEN"
                emoji = "⚠️"
                detail = f"Broke below ${low_7d:,.2f}"
            elif volume_spike:
                alert_type = "VOLUME SPIKE"
                emoji = "💥"
                detail = f"Volume surge: {volume_vs_avg:+.0f}% vs avg"
            elif abs(divergence_4h) > 3.0:
                alert_type = "STRONG 4H DIVERGENCE"
                emoji = "🔔"
                if divergence_4h > 0:
                    detail = f"Gold outpacing BTC by {divergence_4h:+.1f}% (4h)"
                else:
                    detail = f"BTC outpacing Gold by {abs(divergence_4h):.1f}% (4h)"
            elif abs(divergence_1h) > 1.5:
                alert_type = "RAPID DIVERGENCE"
                emoji = "⚡"
                if divergence_1h > 0:
                    detail = f"Gold moving faster than BTC ({divergence_1h:+.1f}% 1h)"
                else:
                    detail = f"BTC moving faster than Gold ({abs(divergence_1h):.1f}% 1h)"
            elif crossed_level:
                alert_type = "$50 LEVEL CROSSED"
                emoji = "🔔"
                if gold_price > prev_price:
                    detail = f"Crossed above ${current_level:,.0f}"
                else:
                    detail = f"Crossed below ${current_level:,.0f}"
            else:
                alert_type = "DIVERGENCE DETECTED"
                emoji = "📊"
                detail = f"Multi-timeframe divergence spotted"

            # Determine overall macro signal
            if divergence_4h > 2.0 or divergence_8h > 3.0:
                div_emoji = "🔴"
                div_status = "RISK-OFF"
                div_detail = "Gold strengthening vs BTC - defensive mode"
            elif divergence_4h < -2.0 or divergence_8h < -3.0:
                div_emoji = "🟢"
                div_status = "RISK-ON"
                div_detail = "BTC strengthening vs Gold - growth mode"
            else:
                div_emoji = "⚪"
                div_status = "NEUTRAL"
                div_detail = "Balanced movement"

            # Volume interpretation
            if volume_vs_avg > 100:
                vol_status = "🔥 EXTREME Volume"
            elif volume_vs_avg > 50:
                vol_status = "🔥 Very High Volume"
            elif volume_vs_avg > 20:
                vol_status = "📈 High Volume"
            else:
                vol_status = "➡️ Normal Volume"

            message = f"{emoji} <b>GOLD ALERT!</b> {emoji}\n\n"
            message += f"🥇 Gold (PAXG): ${gold_price:,.2f}\n\n"
            message += f"<b>{alert_type}</b>\n"
            message += f"{detail}\n\n"

            message += f"📊 <b>MULTI-TIMEFRAME ANALYSIS:</b>\n"
            message += f"├─ 1h: Gold {gold_1h_change:+.2f}% vs BTC {btc_1h_change:+.2f}% (Δ {divergence_1h:+.2f}%)\n"
            message += f"├─ 4h: Gold {gold_4h_change:+.2f}% vs BTC {btc_4h_change:+.2f}% (Δ {divergence_4h:+.2f}%)\n"
            message += f"├─ 8h: Gold {gold_8h_change:+.2f}% vs BTC {btc_8h_change:+.2f}% (Δ {divergence_8h:+.2f}%)\n"
            message += f"└─ 24h: Gold {gold_24h_change:+.2f}% vs BTC {btc_24h_change:+.2f}% (Δ {divergence_24h:+.2f}%)\n\n"

            message += f"📈 <b>CONTEXT:</b>\n"
            message += f"├─ 7-day range: ${low_7d:,.2f} - ${high_7d:,.2f}\n"
            message += f"├─ PAXG/BTC 24h: {paxg_btc_24h_change:+.2f}%\n"
            message += f"└─ Volume: {vol_status} ({volume_vs_avg:+.0f}%)\n\n"

            message += f"{div_emoji} <b>MACRO: {div_status}</b>\n"
            message += f"{div_detail}\n\n"

            message += f"💡 Early detection - check positions!\n\n"
            message += f"⏰ {get_montevideo_time().strftime('%H:%M %Z')}"

            send_alert(message)
            print(f"  🥇 GOLD ALERT SENT! {alert_type}")

    except Exception as e:
        print(f"  🥇 Error checking gold: {e}")
        import traceback
        traceback.print_exc()

def check_alert_rotation():
    """
    ALERT 5: Gold/BTC Rotation Signal
    Triggers when PAXG/USD shows strong divergence with BTC
    Suggests rotation opportunities between gold and crypto
    """
    global last_alert_rotation_time

    if not ALERT_ENABLED or not ALERT_ROTATION_ENABLED:
        return

    # Check cooldown
    if not check_cooldown(last_alert_rotation_time, ALERT_ROTATION_COOLDOWN):
        return

    # Get current BTC price from CryptoCompare
    url_btc = "https://min-api.cryptocompare.com/data/price"
    params_btc = {'fsym': 'BTC', 'tsyms': 'USD'}

    try:
        response_btc = requests.get(url_btc, params=params_btc, timeout=10)
        if response_btc.status_code != 200:
            print(f"  🔄 Error fetching BTC price for rotation alert")
            return
        btc_price = response_btc.json().get('USD', 0)

        # Get current Gold price from CoinGecko
        url_gold = f"https://api.coingecko.com/api/v3/simple/price"
        params_gold = {
            'ids': 'pax-gold',
            'vs_currencies': 'usd',
            'include_24hr_change': 'true'
        }

        response_gold = requests.get(url_gold, params=params_gold, timeout=10)
        if response_gold.status_code != 200:
            print(f"  🔄 Error fetching Gold price for rotation alert")
            return

        gold_data = response_gold.json().get('pax-gold', {})
        gold_price = gold_data.get('usd', 0)
        gold_24h_change = gold_data.get('usd_24h_change', 0)

        if gold_price == 0 or btc_price == 0:
            print(f"  🔄 Invalid price data for rotation alert")
            return

        # Get BTC 24h change
        url_btc_hist = "https://min-api.cryptocompare.com/data/v2/histohour"
        params_btc_hist = {'fsym': 'BTC', 'tsym': 'USD', 'limit': 24}

        response_btc_hist = requests.get(url_btc_hist, params=params_btc_hist, timeout=10)
        if response_btc_hist.status_code != 200:
            print(f"  🔄 Error fetching BTC historical data")
            return

        hist_data = response_btc_hist.json()
        if 'Data' not in hist_data or 'Data' not in hist_data['Data']:
            return

        candles = hist_data['Data']['Data']
        btc_24h_ago = candles[0]['close']
        btc_24h_change = ((btc_price - btc_24h_ago) / btc_24h_ago) * 100

        # Calculate divergence
        divergence = gold_24h_change - btc_24h_change

        print(f"  ROTATION ALERT:")
        print(f"    BTC 24h: {btc_24h_change:+.2f}%")
        print(f"    Gold 24h: {gold_24h_change:+.2f}%")
        print(f"    Divergence: {divergence:+.2f}%")
        print(f"    Threshold: ±{ALERT_ROTATION_THRESHOLD_MODERATE}%")

        # Check if divergence meets threshold
        abs_divergence = abs(divergence)

        if abs_divergence >= ALERT_ROTATION_THRESHOLD_MODERATE:
            last_alert_rotation_time = get_montevideo_time()

            # Determine signal strength
            if abs_divergence >= ALERT_ROTATION_THRESHOLD_STRONG:
                strength = "STRONG"
                stars = "⭐⭐⭐"
            else:
                strength = "MODERATE"
                stars = "⭐⭐"

            # Determine direction
            if divergence > 0:
                # Gold outperforming BTC (risk-off)
                signal_color = "🔴"
                signal_type = "RISK-OFF SIGNAL"
                interpretation = "Gold is outperforming BTC significantly.\nMarket moving to risk-off/defensive mode."
                actions = [
                    "Consider LONG GOLD/BTC position",
                    "Or reduce BTC exposure",
                    "Or add PAXG hedge"
                ]
            else:
                # BTC outperforming Gold (risk-on)
                signal_color = "🟢"
                signal_type = "RISK-ON SIGNAL"
                interpretation = "BTC is outperforming Gold significantly.\nMarket moving to risk-on/growth mode."
                actions = [
                    "Consider SHORT GOLD/BTC position",
                    "Or add more BTC exposure",
                    "Or sell PAXG hedge"
                ]

            message = f"🔄 <b>GOLD/BTC ROTATION ALERT</b>\n"
            message += f"{stars} {signal_color} {strength} {signal_type}\n\n"
            message += f"📊 <b>MARKET STATE:</b>\n"
            message += f"├─ BTC 24h: {btc_24h_change:+.2f}%\n"
            message += f"├─ GOLD 24h: {gold_24h_change:+.2f}%\n"
            message += f"└─ Divergence: {divergence:+.2f}%\n\n"
            message += f"💡 <b>INTERPRETATION:</b>\n"
            message += f"{interpretation}\n\n"
            message += f"🎯 <b>POTENTIAL ACTIONS:</b>\n"
            for action in actions:
                message += f"• {action}\n"
            message += f"\n⏰ {get_montevideo_time().strftime('%Y-%m-%d %H:%M %Z')}"

            send_alert(message)
            print(f"  🔄 ROTATION ALERT SENT! {strength} {signal_type}")

    except Exception as e:
        print(f"  🔄 Error checking rotation signal: {e}")

def check_alert_eth_btc():
    """
    ALERT 7: ETH/BTC Ratio Breaks
    Triggers when:
    - ETH/BTC crosses key levels (0.035, 0.040, 0.045, etc.)
    - 4h divergence > threshold
    - Volume confirmation (ETH volume vs 30d avg)
    """
    global last_alert_eth_btc_time, last_eth_btc_check_ratio

    if not ALERT_ENABLED or not ALERT_ETH_BTC_ENABLED:
        return

    # Check cooldown
    if not check_cooldown(last_alert_eth_btc_time, ALERT_ETH_BTC_COOLDOWN):
        return

    # Get ETH/BTC ratio data (30 days for volume, 7 days for levels)
    url_eth_btc = "https://min-api.cryptocompare.com/data/v2/histohour"
    params_eth_btc = {
        'fsym': 'ETH',
        'tsym': 'BTC',
        'limit': 720  # 30 days
    }

    try:
        response_eth_btc = requests.get(url_eth_btc, params=params_eth_btc, timeout=10)
        if response_eth_btc.status_code != 200:
            print(f"  ⚖️ Error fetching ETH/BTC data")
            return

        data_eth_btc = response_eth_btc.json()
        if 'Data' not in data_eth_btc or 'Data' not in data_eth_btc['Data']:
            print(f"  ⚖️ Invalid ETH/BTC data format")
            return

        candles_eth_btc = data_eth_btc['Data']['Data']
        if len(candles_eth_btc) < 168:
            print(f"  ⚖️ Insufficient ETH/BTC data")
            return

        # Current ratio
        current_ratio = candles_eth_btc[-1]['close']

        # Calculate changes (1h, 4h, 8h, 24h)
        ratio_1h_ago = candles_eth_btc[-2]['close'] if len(candles_eth_btc) >= 2 else current_ratio
        ratio_1h_change = ((current_ratio - ratio_1h_ago) / ratio_1h_ago) * 100

        ratio_4h_ago = candles_eth_btc[-4]['close']
        ratio_4h_change = ((current_ratio - ratio_4h_ago) / ratio_4h_ago) * 100

        ratio_8h_ago = candles_eth_btc[-8]['close']
        ratio_8h_change = ((current_ratio - ratio_8h_ago) / ratio_8h_ago) * 100

        ratio_24h_ago = candles_eth_btc[-24]['close']
        ratio_24h_change = ((current_ratio - ratio_24h_ago) / ratio_24h_ago) * 100

        # 7-day high/low
        prices_7d = [c['close'] for c in candles_eth_btc[-168:]]
        high_7d = max(prices_7d)
        low_7d = min(prices_7d)

        # Get ETH volume (current hour vs 30d avg)
        url_eth_vol = "https://min-api.cryptocompare.com/data/v2/histohour"
        params_eth_vol = {
            'fsym': 'ETH',
            'tsym': 'USD',
            'limit': 720  # 30 days
        }

        response_eth_vol = requests.get(url_eth_vol, params=params_eth_vol, timeout=10)
        eth_volume_vs_avg = 0

        if response_eth_vol.status_code == 200:
            data_eth_vol = response_eth_vol.json()
            if 'Data' in data_eth_vol and 'Data' in data_eth_vol['Data']:
                candles_eth_vol = data_eth_vol['Data']['Data']

                current_hour_volume = candles_eth_vol[-1]['volumeto']
                total_30d_volume = sum([c['volumeto'] for c in candles_eth_vol])
                avg_hourly_volume = total_30d_volume / len(candles_eth_vol)
                eth_volume_vs_avg = ((current_hour_volume / avg_hourly_volume) - 1) * 100 if avg_hourly_volume > 0 else 0

        # Previous check ratio
        prev_ratio = last_eth_btc_check_ratio if last_eth_btc_check_ratio else candles_eth_btc[-2]['close']

        # Check for key level crosses
        crossed_level = False
        crossed_level_value = None

        for level in ALERT_ETH_BTC_LEVELS:
            if (prev_ratio < level <= current_ratio) or (prev_ratio > level >= current_ratio):
                crossed_level = True
                crossed_level_value = level
                break

        # Check for 7d high/low breaks
        broke_high = prev_ratio < high_7d and current_ratio >= high_7d
        broke_low = prev_ratio > low_7d and current_ratio <= low_7d

        # Check for strong divergence
        strong_divergence_4h = abs(ratio_4h_change) >= ALERT_ETH_BTC_DIVERGENCE_THRESHOLD

        print(f"  ETH/BTC RATIO ALERT:")
        print(f"    Current ratio: {current_ratio:.6f}")
        print(f"    1h: {ratio_1h_change:+.2f}% | 4h: {ratio_4h_change:+.2f}% | 8h: {ratio_8h_change:+.2f}% | 24h: {ratio_24h_change:+.2f}%")
        print(f"    7d range: {low_7d:.6f} - {high_7d:.6f}")
        print(f"    ETH volume: {eth_volume_vs_avg:+.0f}% vs 30d avg")
        print(f"    Key level crossed: {'YES' if crossed_level else 'No'} {f'({crossed_level_value:.3f})' if crossed_level_value else ''}")
        print(f"    7d high broken: {'YES' if broke_high else 'No'}")
        print(f"    7d low broken: {'YES' if broke_low else 'No'}")
        print(f"    Strong 4h divergence: {'YES' if strong_divergence_4h else 'No'}")

        # Update last check ratio
        last_eth_btc_check_ratio = current_ratio

        # MINIMUM VOLUME CHECK
        if eth_volume_vs_avg < ALERT_ETH_BTC_MIN_VOLUME:
            print(f"    ❌ Skipping alert - volume too low ({eth_volume_vs_avg:.0f}% < {ALERT_ETH_BTC_MIN_VOLUME}%)")
            return

        # Trigger conditions
        should_trigger = crossed_level or broke_high or broke_low or strong_divergence_4h

        if should_trigger:
            last_alert_eth_btc_time = get_montevideo_time()

            # Determine alert type
            if broke_high:
                alert_type = "7-DAY HIGH BROKEN"
                emoji = "🚀"
                detail = f"ETH/BTC broke above {high_7d:.6f}"
            elif broke_low:
                alert_type = "7-DAY LOW BROKEN"
                emoji = "⚠️"
                detail = f"ETH/BTC broke below {low_7d:.6f}"
            elif crossed_level:
                alert_type = "KEY LEVEL CROSSED"
                emoji = "🔔"
                if current_ratio > prev_ratio:
                    detail = f"ETH/BTC crossed above {crossed_level_value:.3f}"
                else:
                    detail = f"ETH/BTC crossed below {crossed_level_value:.3f}"
            else:  # strong_divergence_4h
                alert_type = "STRONG 4H MOVEMENT"
                emoji = "⚡"
                detail = f"ETH/BTC moved {ratio_4h_change:+.2f}% in 4 hours"

            # Determine macro signal
            if ratio_4h_change > 2.0 or ratio_8h_change > 3.0:
                signal_emoji = "🟢"
                signal_status = "ETH STRENGTHENING"
                signal_detail = "ETH outperforming BTC - alt season signal"
            elif ratio_4h_change < -2.0 or ratio_8h_change < -3.0:
                signal_emoji = "🔴"
                signal_status = "ETH WEAKENING"
                signal_detail = "BTC outperforming ETH - BTC dominance"
            else:
                signal_emoji = "⚪"
                signal_status = "NEUTRAL"
                signal_detail = "Balanced movement"

            # Trend determination
            if ratio_24h_change > 3.0:
                trend = "📈 STRONG UPTREND"
            elif ratio_24h_change > 1.0:
                trend = "📈 UPTREND"
            elif ratio_24h_change < -3.0:
                trend = "📉 STRONG DOWNTREND"
            elif ratio_24h_change < -1.0:
                trend = "📉 DOWNTREND"
            else:
                trend = "➡️ CONSOLIDATION"

            # Volume interpretation
            if eth_volume_vs_avg > 100:
                vol_status = "🔥 EXTREME Volume"
            elif eth_volume_vs_avg > 50:
                vol_status = "🔥 Very High Volume"
            elif eth_volume_vs_avg > 20:
                vol_status = "📈 High Volume"
            else:
                vol_status = "➡️ Normal Volume"

            message = f"{emoji} <b>ETH/BTC RATIO ALERT!</b> {emoji}\n\n"
            message += f"⚖️ ETH/BTC: {current_ratio:.6f}\n\n"
            message += f"<b>{alert_type}</b>\n"
            message += f"{detail}\n\n"

            message += f"📊 <b>MULTI-TIMEFRAME ANALYSIS:</b>\n"
            message += f"├─ 1h: {ratio_1h_change:+.2f}%\n"
            message += f"├─ 4h: {ratio_4h_change:+.2f}%\n"
            message += f"├─ 8h: {ratio_8h_change:+.2f}%\n"
            message += f"└─ 24h: {ratio_24h_change:+.2f}%\n\n"

            message += f"📈 <b>CONTEXT:</b>\n"
            message += f"├─ 7-day range: {low_7d:.6f} - {high_7d:.6f}\n"
            message += f"├─ ETH Volume: {vol_status} ({eth_volume_vs_avg:+.0f}% vs 30d)\n"
            message += f"└─ Trend: {trend}\n\n"

            message += f"{signal_emoji} <b>SIGNAL: {signal_status}</b>\n"
            message += f"{signal_detail}\n\n"

            message += f"💡 Check rotation opportunities!\n\n"
            message += f"⏰ {get_montevideo_time().strftime('%H:%M %Z')}"

            send_alert(message)
            print(f"  ⚖️ ETH/BTC ALERT SENT! {alert_type}")

    except Exception as e:
        print(f"  ⚖️ Error checking ETH/BTC ratio: {e}")
        import traceback
        traceback.print_exc()

def calculate_rsi_local(prices, period=14):
    """Calculate RSI locally"""
    if len(prices) < period + 1:
        return None

    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return round(rsi, 1)

def check_alert_btc_level():
    """
    ALERT 6: BTC Key Level Breaks (ENHANCED)
    Triggers when BTC crosses $1000 increments
    Full analysis: Volume, RSI, PAXG/BTC, trend, Fear & Greed, altcoin context
    """
    global last_alert_btc_level_time, last_btc_check_price

    if not ALERT_ENABLED or not ALERT_BTC_LEVEL_ENABLED:
        return

    # Check cooldown
    if not check_cooldown(last_alert_btc_level_time, ALERT_BTC_COOLDOWN):
        return

    # Get BTC data (30 days for volume, 7 days for trend)
    url_btc = "https://min-api.cryptocompare.com/data/v2/histohour"
    params_btc = {
        'fsym': 'BTC',
        'tsym': 'USD',
        'limit': 720  # 30 days
    }

    try:
        response_btc = requests.get(url_btc, params=params_btc, timeout=10)
        if response_btc.status_code != 200:
            print(f"  ₿ Error fetching BTC data")
            return

        data_btc = response_btc.json()
        if 'Data' not in data_btc or 'Data' not in data_btc['Data']:
            print(f"  ₿ Invalid BTC data format")
            return

        candles_btc = data_btc['Data']['Data']
        if len(candles_btc) < 168:
            print(f"  ₿ Insufficient BTC data")
            return

        # Current BTC price
        btc_price = candles_btc[-1]['close']

        # Calculate BTC changes (1h, 24h, 7d, 14d)
        btc_1h_ago = candles_btc[-1]['close']
        btc_1h_change = 0  # Will calculate if needed

        btc_24h_ago = candles_btc[-24]['close']
        btc_24h_change = ((btc_price - btc_24h_ago) / btc_24h_ago) * 100

        btc_7d_ago = candles_btc[-168]['close']
        btc_7d_change = ((btc_price - btc_7d_ago) / btc_7d_ago) * 100

        # 7-day high/low
        prices_7d = [c['close'] for c in candles_btc[-168:]]
        high_7d = max(prices_7d)
        low_7d = min(prices_7d)

        # Calculate BTC volume (current hour vs 30d avg)
        current_hour_volume = candles_btc[-1]['volumeto']
        total_30d_volume = sum([c['volumeto'] for c in candles_btc])
        avg_hourly_volume = total_30d_volume / len(candles_btc)
        volume_vs_avg = ((current_hour_volume / avg_hourly_volume) - 1) * 100 if avg_hourly_volume > 0 else 0

        # Previous check price (to detect crosses)
        prev_price = last_btc_check_price if last_btc_check_price else candles_btc[-2]['close']

        # Check for round level crosses
        current_level = (btc_price // ALERT_BTC_ROUND_INCREMENT) * ALERT_BTC_ROUND_INCREMENT
        prev_level = (prev_price // ALERT_BTC_ROUND_INCREMENT) * ALERT_BTC_ROUND_INCREMENT
        crossed_round_level = current_level != prev_level

        # Check if broke 7d high/low
        broke_7d_high = prev_price < high_7d and btc_price >= high_7d
        broke_7d_low = prev_price > low_7d and btc_price <= low_7d

        # Get BTC RSI
        prices_for_rsi = [c['close'] for c in candles_btc[-50:]]
        btc_rsi = calculate_rsi_local(prices_for_rsi)

        # Get Gold data for PAXG/BTC
        url_gold = "https://min-api.cryptocompare.com/data/v2/histohour"
        params_gold = {
            'fsym': 'PAXG',
            'tsym': 'USD',
            'limit': 24
        }

        response_gold = requests.get(url_gold, params=params_gold, timeout=10)
        gold_24h_change = 0
        paxg_btc_24h_change = 0
        paxg_btc_ratio = 0

        if response_gold.status_code == 200:
            data_gold = response_gold.json()
            if 'Data' in data_gold and 'Data' in data_gold['Data']:
                candles_gold = data_gold['Data']['Data']
                gold_price = candles_gold[-1]['close']
                gold_24h_ago_price = candles_gold[0]['close']

                gold_24h_change = ((gold_price - gold_24h_ago_price) / gold_24h_ago_price) * 100

                # PAXG/BTC ratio and change
                paxg_btc_ratio = gold_price / btc_price
                paxg_btc_ratio_24h_ago = gold_24h_ago_price / btc_24h_ago
                paxg_btc_24h_change = ((paxg_btc_ratio - paxg_btc_ratio_24h_ago) / paxg_btc_ratio_24h_ago) * 100

        # Get Fear & Greed Index
        try:
            fg_url = "https://api.alternative.me/fng/?limit=1"
            fg_response = requests.get(fg_url, timeout=10)
            fg_value = None
            fg_classification = None

            if fg_response.status_code == 200:
                fg_data = fg_response.json()
                if 'data' in fg_data and len(fg_data['data']) > 0:
                    fg_value = int(fg_data['data'][0]['value'])
                    fg_classification = fg_data['data'][0]['value_classification']
        except:
            fg_value = None
            fg_classification = None

        print(f"  BTC LEVEL ALERT:")
        print(f"    Current: ${btc_price:,.0f}")
        print(f"    BTC 24h: {btc_24h_change:+.2f}%")
        print(f"    BTC 7d: {btc_7d_change:+.2f}%")
        print(f"    7d range: ${low_7d:,.0f} - ${high_7d:,.0f}")
        print(f"    RSI: {btc_rsi}")
        print(f"    Volume: {volume_vs_avg:+.0f}% vs 30d avg")
        print(f"    PAXG/BTC 24h: {paxg_btc_24h_change:+.2f}%")
        print(f"    F&G: {fg_value} ({fg_classification})" if fg_value else "    F&G: N/A")
        print(f"    Round level: ${current_level:,.0f} {'🔴 CROSSED!' if crossed_round_level else ''}")
        print(f"    7d high broken: {'🔴 YES' if broke_7d_high else 'No'}")
        print(f"    7d low broken: {'🔴 YES' if broke_7d_low else 'No'}")

        # Update last check price
        last_btc_check_price = btc_price

        # MINIMUM VOLUME CHECK
        if volume_vs_avg < -50:
            print(f"    ❌ Skipping BTC alert - volume too low ({volume_vs_avg:.0f}% < -50%)")
            return

        # Trigger alert if level crossed OR 7d high/low broken
        if crossed_round_level or broke_7d_high or broke_7d_low:
            last_alert_btc_level_time = get_montevideo_time()

            # Determine alert type
            if broke_7d_high:
                emoji = "🚀"
                alert_type = "7-DAY HIGH BROKEN"
                direction = "UP"
                detail = f"Broke above 7-day high: ${high_7d:,.0f}"
            elif broke_7d_low:
                emoji = "⚠️"
                alert_type = "7-DAY LOW BROKEN"
                direction = "DOWN"
                detail = f"Broke below 7-day low: ${low_7d:,.0f}"
            elif btc_price > prev_price:
                emoji = "🚀"
                alert_type = "KEY LEVEL CROSSED"
                direction = "UP"
                detail = f"Crossed above ${current_level:,.0f}"
            else:
                emoji = "⚠️"
                alert_type = "KEY LEVEL CROSSED"
                direction = "DOWN"
                detail = f"Crossed below ${current_level:,.0f}"

            # Volume interpretation
            if volume_vs_avg > 100:
                vol_status = "🔥 EXTREME Volume"
                vol_confidence = "Very high conviction"
            elif volume_vs_avg > 50:
                vol_status = "🔥 Very High Volume"
                vol_confidence = "Strong conviction"
            elif volume_vs_avg > 20:
                vol_status = "📈 High Volume"
                vol_confidence = "Good conviction"
            elif volume_vs_avg < -50:
                vol_status = "💤 Very Low Volume"
                vol_confidence = "Weak conviction - caution"
            elif volume_vs_avg < -20:
                vol_status = "📉 Low Volume"
                vol_confidence = "Limited conviction"
            else:
                vol_status = "➡️ Normal Volume"
                vol_confidence = "Average conviction"

            # RSI interpretation
            if btc_rsi is not None:
                if btc_rsi < 25:
                    rsi_status = "🟢 EXTREMELY OVERSOLD"
                    rsi_signal = "Strong bounce potential"
                elif btc_rsi < 30:
                    rsi_status = "🟢 OVERSOLD"
                    rsi_signal = "Bounce opportunity"
                elif btc_rsi > 75:
                    rsi_status = "🔴 EXTREMELY OVERBOUGHT"
                    rsi_signal = "High correction risk"
                elif btc_rsi > 70:
                    rsi_status = "🔴 OVERBOUGHT"
                    rsi_signal = "Correction risk"
                else:
                    rsi_status = "⚪ NEUTRAL"
                    rsi_signal = "Room to move"
                rsi_text = f"RSI: {btc_rsi:.0f} {rsi_status}"
            else:
                rsi_text = "RSI: N/A"
                rsi_signal = ""

            # PAXG/BTC interpretation (macro context)
            btc_gold_divergence = btc_24h_change - gold_24h_change

            if paxg_btc_24h_change > 2.0:
                paxg_emoji = "🥇"
                paxg_status = "GOLD SURGING"
                paxg_detail = "Flight to safety - risk-off mode"
            elif paxg_btc_24h_change > 0.5:
                paxg_emoji = "🥇"
                paxg_status = "GOLD STRENGTHENING"
                paxg_detail = "Defensive sentiment"
            elif paxg_btc_24h_change < -2.0:
                paxg_emoji = "₿"
                paxg_status = "BTC DOMINATING"
                paxg_detail = "Strong risk-on momentum"
            elif paxg_btc_24h_change < -0.5:
                paxg_emoji = "₿"
                paxg_status = "BTC STRENGTHENING"
                paxg_detail = "Risk-on sentiment"
            else:
                paxg_emoji = "⚖️"
                paxg_status = "BALANCED"
                paxg_detail = "Neutral macro environment"

            # Fear & Greed interpretation
            if fg_value:
                if fg_value < 20:
                    fg_emoji = "😱"
                    fg_status = "EXTREME FEAR"
                    fg_detail = "Market in panic - potential bottom"
                elif fg_value < 40:
                    fg_emoji = "😰"
                    fg_status = "FEAR"
                    fg_detail = "Cautious sentiment - accumulation zone"
                elif fg_value < 60:
                    fg_emoji = "😐"
                    fg_status = "NEUTRAL"
                    fg_detail = "Balanced market psychology"
                elif fg_value < 80:
                    fg_emoji = "😊"
                    fg_status = "GREED"
                    fg_detail = "Bullish sentiment - watch for excess"
                else:
                    fg_emoji = "🤑"
                    fg_status = "EXTREME GREED"
                    fg_detail = "Market euphoria - potential top"
                fg_text = f"{fg_emoji} Fear & Greed: {fg_value} ({fg_status})"
            else:
                fg_text = ""
                fg_detail = ""

            # Trend determination (more detailed)
            if btc_7d_change > 10.0 and btc_24h_change > 2.0:
                trend = "🔥 PARABOLIC UPTREND"
                trend_detail = "Exceptional rally - watch for overextension"
            elif btc_7d_change > 5.0 and btc_24h_change > 0:
                trend = "📈 STRONG UPTREND"
                trend_detail = "Multi-day rally - momentum strong"
            elif btc_7d_change > 2.0 and btc_24h_change > 0:
                trend = "📈 UPTREND"
                trend_detail = "Positive momentum building"
            elif btc_7d_change < -10.0 and btc_24h_change < -2.0:
                trend = "❄️ STEEP DOWNTREND"
                trend_detail = "Sharp decline - potential capitulation"
            elif btc_7d_change < -5.0 and btc_24h_change < 0:
                trend = "📉 STRONG DOWNTREND"
                trend_detail = "Multi-day weakness - caution"
            elif btc_7d_change < -2.0 and btc_24h_change < 0:
                trend = "📉 DOWNTREND"
                trend_detail = "Negative momentum present"
            elif abs(btc_24h_change) < 1.0:
                trend = "➡️ CONSOLIDATION"
                trend_detail = "Range-bound - awaiting catalyst"
            elif btc_7d_change > 2.0 and btc_24h_change < -1.0:
                trend = "⚠️ PULLBACK IN UPTREND"
                trend_detail = "Short-term weakness - potential entry"
            elif btc_7d_change < -2.0 and btc_24h_change > 1.0:
                trend = "🔄 BOUNCE IN DOWNTREND"
                trend_detail = "Relief rally - watch for resistance"
            else:
                trend = "🔀 CHOPPY"
                trend_detail = "Mixed signals - no clear direction"

            # Get upcoming catalysts
            catalysts = get_altcoin_catalysts_summary()

            # Build the alert message
            message = f"{emoji} <b>BTC ALERT! {alert_type}</b> {emoji}\n\n"
            message += f"₿ Bitcoin: ${btc_price:,.0f}\n"
            message += f"   24h: {btc_24h_change:+.2f}% | 7d: {btc_7d_change:+.2f}%\n\n"
            message += f"<b>{detail}</b>\n\n"

            # Get market context
            print("  Fetching market context for alert...")
            market_context = get_market_context()

            # Market Context Section
            message += f"🌍 <b>MARKET CONTEXT (Alt Season Check):</b>\n"

            if market_context['btc_dominance']:
                btc_dom = market_context['btc_dominance']
                dom_signal = market_context['btc_dom_signal']

                if dom_signal == 'BUY':
                    dom_emoji = "🟢"
                    dom_text = "ALT SEASON"
                elif dom_signal == 'SELL':
                    dom_emoji = "🔴"
                    dom_text = "BTC SEASON"
                else:
                    dom_emoji = "🟡"
                    dom_text = "NEUTRAL"

                message += f"{dom_emoji} BTC.D: {btc_dom:.1f}% ({dom_text}) "

            if market_context['eth_btc_ratio']:
                ratio = market_context['eth_btc_ratio']
                trend = market_context['eth_btc_trend']
                signal = market_context['eth_btc_signal']

                if signal == 'BUY':
                    ratio_emoji = "🟢"
                elif signal == 'SELL':
                    ratio_emoji = "🔴"
                else:
                    ratio_emoji = "🟡"

                message += f"| {ratio_emoji} ETH/BTC: {ratio:.5f} ({trend:+.1f}%) "

            if market_context['alt_volume_share']:
                vol_share = market_context['alt_volume_share']
                vol_signal = market_context['alt_vol_signal']

                if vol_signal == 'BUY':
                    vol_emoji = "🟢"
                elif vol_signal == 'CAUTION':
                    vol_emoji = "🔴"
                else:
                    vol_emoji = "🟡"

                message += f"| {vol_emoji} AltVol: {vol_share:.0f}%"

            message += f"\n\n"

            message += f"📊 <b>TECHNICAL ANALYSIS:</b>\n"
            message += f"├─ 7-day range: ${low_7d:,.0f} - ${high_7d:,.0f}\n"
            message += f"├─ {vol_status}\n"
            message += f"│  {vol_confidence} ({volume_vs_avg:+.0f}% vs 30d avg)\n"
            message += f"├─ {rsi_text}\n"
            if rsi_signal:
                message += f"│  {rsi_signal}\n"
            message += f"└─ <b>{trend}</b>\n"
            message += f"   {trend_detail}\n\n"

            message += f"🌍 <b>MACRO CONTEXT:</b>\n"
            message += f"├─ PAXG/BTC: {paxg_btc_ratio:.4f} BTC\n"
            message += f"│  24h: {paxg_btc_24h_change:+.2f}%\n"
            message += f"├─ {paxg_emoji} <b>{paxg_status}</b>\n"
            message += f"│  {paxg_detail}\n"

            if fg_text:
                message += f"└─ {fg_text}\n"
                message += f"   {fg_detail}\n\n"
            else:
                message += f"\n"

            # Actionable insights
            message += f"💡 <b>TRADING CONTEXT:</b>\n"

            if direction == "UP":
                if btc_rsi and btc_rsi > 75:
                    insight = "⚠️ Extreme overbought - high correction risk"
                elif btc_rsi and btc_rsi > 70:
                    insight = "⚠️ Overbought - watch for profit-taking"
                elif volume_vs_avg > 50:
                    insight = "✅ High volume breakout - strong conviction"
                elif broke_7d_high:
                    insight = "🚀 Breakout confirmed - momentum accelerating"
                else:
                    insight = "📊 Upside move - monitor for continuation"
            else:  # DOWN
                if btc_rsi and btc_rsi < 25:
                    insight = "💡 Extreme oversold - strong bounce potential"
                elif btc_rsi and btc_rsi < 30:
                    insight = "💡 Oversold - potential accumulation zone"
                elif volume_vs_avg > 50:
                    insight = "⚠️ High volume selloff - caution warranted"
                elif broke_7d_low:
                    insight = "⚠️ Breakdown confirmed - support lost"
                else:
                    insight = "📊 Downside move - monitor support levels"

            message += f"{insight}\n\n"

            # Add catalyst context if any
            if catalysts:
                message += f"📅 <b>Upcoming Catalysts:</b>\n"
                message += f"{' | '.join(catalysts)}\n\n"

            message += f"💬 Check divergence report for altcoin opportunities!\n\n"
            message += f"⏰ {get_montevideo_time().strftime('%H:%M %Z')}"

            send_alert(message)
            print(f"  ₿ BTC ALERT SENT! {alert_type}")

    except Exception as e:
        print(f"  ₿ Error checking BTC level: {e}")
        import traceback
        traceback.print_exc()

def check_alert_btc_dominance():
    """Check for BTC Dominance threshold crossings and momentum shifts"""
    global last_alert_btc_dom_time, last_btc_dom_check

    if not ALERT_ENABLED or not ALERT_BTC_DOM_ENABLED:
        print("  ⚖️ BTC.D alerts disabled")
        return

    try:
        # Check cooldown
        now = datetime.now()
        if last_alert_btc_dom_time:
            minutes_since = (now - last_alert_btc_dom_time).total_seconds() / 60
            if minutes_since < ALERT_BTC_DOM_COOLDOWN:
                print(f"  ⚖️ BTC.D alert on cooldown ({minutes_since:.0f}/{ALERT_BTC_DOM_COOLDOWN} min)")
                return

        # Get BTC dominance data
        print("  ⚖️ Checking BTC Dominance...")

        # Fetch from CoinGecko
        url = "https://api.coingecko.com/api/v3/global"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            print(f"  ⚖️ Failed to fetch dominance data: {response.status_code}")
            return

        data = response.json()
        current_dom = data.get('data', {}).get('market_cap_percentage', {}).get('btc')

        if not current_dom:
            print("  ⚖️ No dominance data available")
            return

        current_dom = round(current_dom, 2)

        # Get historical dominance for momentum calculation
        # Using CryptoCompare for BTC historical data to estimate dominance change
        url_hist = "https://min-api.cryptocompare.com/data/v2/histohour"
        params = {'fsym': 'BTC', 'tsym': 'USD', 'limit': 168}  # 7 days
        response_hist = requests.get(url_hist, params=params, timeout=10)

        dom_24h_ago = None
        dom_7d_ago = None

        if response_hist.status_code == 200:
            hist_data = response_hist.json()
            if 'Data' in hist_data and 'Data' in hist_data['Data']:
                candles = hist_data['Data']['Data']

                # Rough dominance estimation based on BTC price change
                # (Not perfect, but gives momentum indication)
                btc_now = candles[-1]['close']
                btc_24h = candles[-24]['close']
                btc_7d = candles[-168]['close'] if len(candles) >= 168 else candles[0]['close']

                # Estimate dominance changes (conservative factor)
                price_change_24h = ((btc_now - btc_24h) / btc_24h) * 100
                price_change_7d = ((btc_now - btc_7d) / btc_7d) * 100

                dom_change_24h = price_change_24h * 0.3  # Conservative correlation
                dom_change_7d = price_change_7d * 0.3

                dom_24h_ago = round(current_dom - dom_change_24h, 2)
                dom_7d_ago = round(current_dom - dom_change_7d, 2)

        print(f"  ⚖️ Current: {current_dom}% | 24h ago: {dom_24h_ago}% | 7d ago: {dom_7d_ago}%")

        # Determine current level and signal
        if current_dom < 54:
            level = "🔄 REVERSE COMING"
            level_zone = "REVERSE"
            action = "⚠️ Peak alt season risk - consider profit-taking"
        elif current_dom < 56:
            level = "🟢 ALT BUY ZONE"
            level_zone = "ALT_BUY"
            action = "✅ Active alt rotation - quality setups favored"
        elif current_dom < 57.5:
            level = "🟡 PREPARE ALTS"
            level_zone = "PREPARE_ALTS"
            action = "📋 Build watchlist - rotation likely coming"
        elif current_dom < 58.5:
            level = "🟠 PREPARE BTC"
            level_zone = "PREPARE_BTC"
            action = "🎯 Alt profits to BTC - rotation ending"
        else:
            level = "🔴 SELL ALTS"
            level_zone = "SELL_ALTS"
            action = "❌ BTC dominance - alts underperform"

        # Determine momentum
        momentum = "STABLE"
        momentum_emoji = "➡️"

        if dom_24h_ago:
            change_24h = current_dom - dom_24h_ago

            if abs(change_24h) >= ALERT_BTC_DOM_MOMENTUM_THRESHOLD:
                if change_24h > 0:
                    momentum = "RISING"
                    momentum_emoji = "⬆️"
                else:
                    momentum = "FALLING"
                    momentum_emoji = "⬇️"

        # Check for alert triggers
        should_alert = False
        alert_reason = []

        # 1. Threshold crossing check
        if last_btc_dom_check:
            for threshold in ALERT_BTC_DOM_THRESHOLDS:
                crossed_up = last_btc_dom_check < threshold <= current_dom
                crossed_down = last_btc_dom_check > threshold >= current_dom

                if crossed_up:
                    should_alert = True
                    alert_reason.append(f"Crossed {threshold}% upward")
                elif crossed_down:
                    should_alert = True
                    alert_reason.append(f"Crossed {threshold}% downward")

        # 2. Momentum shift detection (if we have historical data)
        if dom_24h_ago and abs(current_dom - dom_24h_ago) >= ALERT_BTC_DOM_MOMENTUM_THRESHOLD:
            should_alert = True
            direction = "rising" if current_dom > dom_24h_ago else "falling"
            alert_reason.append(f"Momentum shift: {direction}")

        # 3. Edge opportunity detection (conflicting signals)
        edge = None
        if level_zone in ["SELL_ALTS", "PREPARE_BTC"] and momentum == "FALLING":
            should_alert = True
            edge = "⚡ Alt rotation likely accelerating despite high dominance"
            alert_reason.append("Edge: Momentum favors alts")
        elif level_zone in ["ALT_BUY", "PREPARE_ALTS"] and momentum == "RISING":
            should_alert = True
            edge = "⚠️ BTC rotation likely despite lower dominance"
            alert_reason.append("Edge: Momentum favors BTC")

        # Send alert if triggered
        if should_alert:
            message = f"⚖️ <b>BTC DOMINANCE ALERT</b>\n\n"
            message += f"<b>Current:</b> {current_dom}%\n"
            message += f"<b>Level:</b> {level}\n"
            message += f"<b>Momentum:</b> {momentum_emoji} {momentum}\n"

            if dom_24h_ago:
                change_24h = current_dom - dom_24h_ago
                message += f"   24h: {change_24h:+.1f}%"
            if dom_7d_ago:
                change_7d = current_dom - dom_7d_ago
                message += f" | 7d: {change_7d:+.1f}%"
            message += "\n\n"

            message += f"<b>Action:</b> {action}\n"

            if edge:
                message += f"\n<b>Edge:</b> {edge}\n"

            message += f"\n<b>Trigger:</b> {', '.join(alert_reason)}\n"
            message += f"\n⏰ {get_montevideo_time().strftime('%H:%M %Z')}"

            send_alert(message)
            last_alert_btc_dom_time = now
            print(f"  ⚖️ BTC.D ALERT SENT! Reasons: {', '.join(alert_reason)}")
        else:
            print(f"  ⚖️ No alert: {level} ({momentum})")

        # Update last check
        last_btc_dom_check = current_dom

    except Exception as e:
        print(f"  ⚖️ Error checking BTC dominance: {e}")
        import traceback
        traceback.print_exc()

def check_alert_derivatives():
    """
    ALERT 9: Derivatives Market Extremes
    Triggers on dangerous leverage conditions:
    - Extreme positive funding + high OI = overleveraged longs, flush coming
    - Extreme negative funding + high OI = overleveraged shorts, squeeze coming
    - Very extreme funding alone = immediate danger

    Based on Day 12 education: Funding rate + OI = market structure signal
    """
    global last_alert_derivatives_time

    if not ALERT_ENABLED or not ALERT_DERIVATIVES_ENABLED:
        print("  ⚡ Derivatives alerts disabled")
        return

    # Check cooldown
    if not check_cooldown(last_alert_derivatives_time, ALERT_DERIVATIVES_COOLDOWN):
        return

    try:
        print("  ⚡ Checking derivatives market...")

        # Try to get funding rate and OI from Binance
        # NOTE: This will fail on PythonAnywhere until network whitelist updated
        # Will work when moved to new platform

        funding_url = "https://fapi.binance.com/fapi/v1/premiumIndex"
        funding_params = {'symbol': 'BTCUSDT'}

        oi_url = "https://fapi.binance.com/fapi/v1/openInterest"
        oi_params = {'symbol': 'BTCUSDT'}

        price_url = "https://api.binance.com/api/v3/ticker/price"
        price_params = {'symbol': 'BTCUSDT'}

        # Get funding rate
        response_funding = requests.get(funding_url, params=funding_params, timeout=10)
        if response_funding.status_code != 200:
            print(f"  ⚡ Derivatives API unavailable (will work on new platform)")
            return

        funding_data = response_funding.json()
        funding_rate = float(funding_data.get('lastFundingRate', 0))
        funding_pct = funding_rate * 100  # Convert to percentage

        # Get open interest
        response_oi = requests.get(oi_url, params=oi_params, timeout=10)
        if response_oi.status_code != 200:
            print(f"  ⚡ OI API unavailable")
            return

        oi_data = response_oi.json()
        oi_contracts = float(oi_data.get('openInterest', 0))

        # Get BTC price for USD calculation
        response_price = requests.get(price_url, params=price_params, timeout=10)
        btc_price = 100000  # Fallback
        if response_price.status_code == 200:
            btc_price = float(response_price.json().get('price', 100000))

        # Calculate OI in billions
        oi_usd = oi_contracts * btc_price
        oi_billions = oi_usd / 1_000_000_000

        # Annualized funding
        funding_annualized = funding_pct * 3 * 365

        print(f"  ⚡ Funding: {funding_pct:.4f}% ({funding_annualized:.1f}% annual)")
        print(f"  ⚡ OI: ${oi_billions:.2f}B")

        # TRIGGER CONDITIONS (from Day 12)
        extreme_positive_funding = funding_pct >= ALERT_DERIVATIVES_FUNDING_EXTREME
        extreme_negative_funding = funding_pct <= -ALERT_DERIVATIVES_FUNDING_EXTREME
        very_extreme_funding = abs(funding_pct) >= ALERT_DERIVATIVES_FUNDING_VERY_EXTREME
        high_oi = oi_billions >= ALERT_DERIVATIVES_OI_HIGH
        extreme_oi = oi_billions >= ALERT_DERIVATIVES_OI_EXTREME

        should_alert = False
        alert_type = None
        alert_emoji = None
        alert_detail = None
        alert_action = None
        risk_level = None

        # Condition 1: Extreme positive funding + high OI = TOP RISK
        if extreme_positive_funding and high_oi:
            should_alert = True
            alert_type = "🔴 DANGER ZONE - TOP RISK"
            alert_emoji = "🚨"
            alert_detail = "Overleveraged LONGS with high open interest"
            alert_action = "⚠️ DO NOT BUY - Liquidation cascade imminent\n   Wait for flush, then deploy at lower levels"
            risk_level = "EXTREME" if extreme_oi else "HIGH"

        # Condition 2: Extreme negative funding + high OI = BOTTOM OPPORTUNITY
        elif extreme_negative_funding and high_oi:
            should_alert = True
            alert_type = "🟢 OPPORTUNITY - BOTTOM SIGNAL"
            alert_emoji = "💡"
            alert_detail = "Overleveraged SHORTS with high open interest"
            alert_action = "✅ ACCUMULATE - Short squeeze likely\n   Deploy Finst ladder, watch for bounce"
            risk_level = "OPPORTUNITY"

        # Condition 3: Very extreme funding alone (regardless of OI)
        elif very_extreme_funding:
            should_alert = True
            if funding_pct > 0:
                alert_type = "🔴 EXTREME BULLISH FUNDING"
                alert_emoji = "⚠️"
                alert_detail = "Market maximally long-biased"
                alert_action = "⚠️ CAUTION - High correction risk\n   Reduce exposure, wait for reset"
                risk_level = "HIGH"
            else:
                alert_type = "🟢 EXTREME BEARISH FUNDING"
                alert_emoji = "💡"
                alert_detail = "Market maximally short-biased"
                alert_action = "💡 CONTRARIAN OPPORTUNITY\n   Shorts likely to be squeezed"
                risk_level = "OPPORTUNITY"

        print(f"  ⚡ Alert trigger: {'YES' if should_alert else 'NO'}")

        if should_alert:
            last_alert_derivatives_time = get_montevideo_time()

            # Build comprehensive alert message
            message = f"{alert_emoji} <b>DERIVATIVES ALERT!</b> {alert_emoji}\n\n"
            message += f"<b>{alert_type}</b>\n\n"
            message += f"📊 <b>MARKET STRUCTURE:</b>\n"
            message += f"├─ Funding Rate: {funding_pct:.4f}% per 8hrs\n"
            message += f"│  Annualized: {funding_annualized:.1f}%\n"
            message += f"├─ Open Interest: ${oi_billions:.2f}B\n"
            message += f"└─ Risk Level: <b>{risk_level}</b>\n\n"

            message += f"💡 <b>WHAT THIS MEANS:</b>\n"
            message += f"{alert_detail}\n\n"

            message += f"🎯 <b>RECOMMENDED ACTION:</b>\n"
            message += f"{alert_action}\n\n"

            message += f"📚 <b>CONTEXT (Day 12):</b>\n"
            if extreme_positive_funding and high_oi:
                message += f"• Too many longs using leverage\n"
                message += f"• If BTC drops, forced selling cascade\n"
                message += f"• Seen before: Nov 2024 $93k→$90k flush\n"
            elif extreme_negative_funding and high_oi:
                message += f"• Too many shorts using leverage\n"
                message += f"• If BTC rises, forced buying cascade\n"
                message += f"• Classic short squeeze setup\n"
            elif very_extreme_funding:
                message += f"• Market one-sided, reset incoming\n"
                message += f"• Funding this extreme unsustainable\n"
                message += f"• Expect volatility + mean reversion\n"

            message += f"\n⚠️ <b>CRITICAL:</b> This is WHY crypto moves 10-15% in minutes\n"
            message += f"Leverage liquidations cascade both ways\n\n"

            message += f"⏰ {get_montevideo_time().strftime('%H:%M %Z')}"

            send_alert(message)
            print(f"  ⚡ DERIVATIVES ALERT SENT! {alert_type}")

    except Exception as e:
        print(f"  ⚡ Error checking derivatives (expected on PythonAnywhere): {e}")
        # Don't print full traceback - expected failure until platform migration

def check_all_signals():
    """Main function to check all signal types"""

    print(f"\n{'='*70}")
    print(f"Signal Check at {get_montevideo_time().strftime('%H:%M:%S')}")
    print(f"{'='*70}")

    try:
        # Get BTC data
        data = get_cryptocompare_data()

        if not data:
            print("Failed to fetch data")
            return

        btc_price = data['current_price']
        hist_data = data['historical']

        if 'Data' not in hist_data or 'Data' not in hist_data['Data']:
            print("Invalid historical data format")
            return

        candles = hist_data['Data']['Data']

        if len(candles) < 130:
            print(f"Insufficient historical data (need 130, got {len(candles)})")
            return

        print(f"  Current BTC: ${btc_price:,.2f}\n")

        # Check all alerts
        check_alert_acceleration(candles, btc_price)
        check_alert_momentum(candles, btc_price)
        check_alert_spike(candles, btc_price)
        check_alert_gold()
        check_alert_rotation()
        check_alert_btc_level()
        check_alert_eth_btc()
        check_alert_btc_dominance()
        check_alert_derivatives()

        print(f"{'='*70}\n")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_all_signals()
