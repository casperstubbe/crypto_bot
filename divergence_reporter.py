#!/usr/bin/env python3
"""
DIVERGENCE UTILITIES
Shared calculation functions used by morning and evening reports

TWO TYPES OF DIVERGENCE:
1. Short-term (14-day): Snapback trading signals
2. Structural (90-day): Portfolio positioning & health checks

Updated: November 9, 2025 - Added 90-day structural divergence analysis
"""

import requests
import time
from datetime import datetime
from config import ALTCOINS, BITCOIN_ID

# ========== SHORT-TERM DIVERGENCE (14-DAY SNAPBACK) ==========
# These functions are for TRADING signals - mean reversion plays

def get_rsi_for_coin_daily(coin_symbol):
    """Get RSI for any coin using DAILY data (14-period)"""
    url = "https://min-api.cryptocompare.com/data/v2/histoday"
    params = {
        'fsym': coin_symbol,
        'tsym': 'USD',
        'limit': 30
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'Data' in data and 'Data' in data['Data']:
                candles = data['Data']['Data']
                prices = [candle['close'] for candle in candles]
                return calculate_rsi(prices, period=14)
        return None
    except Exception as e:
        print(f"Error calculating daily RSI for {coin_symbol}: {e}")
        return None


def calculate_quality_score(alt, macro_regime=None, macro_reason=None):
    """
    Calculate divergence quality score (0-10)
    Used for filtering trade signals based on technical + macro factors
    """
    score = 0
    signals = []

    # Macro filter first
    if macro_regime:
        if macro_regime == 'AVOID':
            score -= 5
            signals.insert(0, f"🚨 MACRO: {macro_reason}")
        elif macro_regime == 'CAUTION':
            score -= 2
            signals.insert(0, f"⚠️ MACRO: {macro_reason}")
        elif macro_regime == 'BUY':
            score += 2
            signals.insert(0, f"🟢 MACRO: {macro_reason}")

    # RSI signals
    if alt['rsi'] is not None:
        if alt['rsi'] < 30:
            score += 3
            signals.append("🟢 Extreme oversold")
        elif alt['rsi'] < 35:
            score += 2
            signals.append("🟢 Oversold")
        elif alt['rsi'] >= 50 and alt['rsi'] < 70:
            score -= 1
            signals.append("⚠️ Not oversold")

    # Support level signals
    if alt['pct_from_60d_low'] is not None:
        if alt['pct_from_60d_low'] < 0:
            score -= 3
            signals.append("🚨 Broke 60d low")
        elif alt['pct_from_60d_low'] <= 5:
            score += 2
            signals.append("🟢 At support")
        elif alt['pct_from_60d_low'] <= 10:
            score += 1
            signals.append("🟡 Near support")

    # Volume relative to other alts
    if alt['volume_relative'] is not None:
        if alt['volume_relative'] < -15:
            score -= 2
            signals.append("🔴 Abandoned (vol)")
        elif alt['volume_relative'] > 15:
            score += 2
            signals.append("🟢 Strong volume")
        elif alt['volume_relative'] > 10:
            score += 1
            signals.append("🟢 Vol holding up")

    # Momentum trend
    if alt['div_7d'] is not None and alt['div'] is not None:
        momentum_change = alt['div_7d'] - alt['div']

        if alt['div'] < 0:  # LONG signals
            if momentum_change > 2 and alt['div_7d'] > -3:
                score += 2
                signals.append("🟢 Stabilizing")
            elif momentum_change > 2:
                signals.append("🟡 Declining slower")
            elif momentum_change < -2:
                score -= 2
                signals.append("🔴 Accelerating down")
        else:  # SHORT signals
            if momentum_change < -2 and alt['div_7d'] < 3:
                score += 2
                signals.append("🟢 Topping out")
            elif momentum_change < -2:
                signals.append("🟡 Rising slower")
            elif momentum_change > 2:
                score -= 2
                signals.append("🔴 Accelerating up")

    # Volume spike confirmation
    if alt['volume_vs_avg'] is not None and alt['volume_vs_avg'] > 50:
        score += 1
        signals.append("💰 Volume spike")

    # Classify quality
    if score >= 7:
        quality = "EXCELLENT"
        stars = "⭐⭐⭐"
    elif score >= 5:
        quality = "GOOD"
        stars = "⭐⭐"
    elif score >= 2:
        quality = "MIXED"
        stars = "⭐"
    else:
        quality = "POOR"
        stars = "❌"

    return {
        'score': score,
        'quality': quality,
        'stars': stars,
        'signals': signals
    }


def get_macro_regime(btc_price, gold_divergence, btc_dominance, eth_btc_signal, btc_rsi=None):
    """
    Determine if we're in a favorable environment for alt entries
    Returns: ('BUY'/'CAUTION'/'AVOID', reason_string)
    """
    # AVOID regime - multiple red flags
    if gold_divergence and gold_divergence > 3.0:
        return 'AVOID', "Flight to safety active"

    if btc_dominance and btc_dominance > 59.5:
        return 'AVOID', "BTC.D too high (alts bleeding)"

    if eth_btc_signal == 'SELL':
        return 'AVOID', "ETH/BTC breakdown"

    # CAUTION regime - waiting for confirmation
    if btc_price and btc_price < 125000:
        return 'CAUTION', "BTC below $125k resistance"

    if btc_rsi and btc_rsi < 25:
        return 'CAUTION', "BTC oversold (wait for bounce)"

    # BUY regime - breakout confirmed
    if btc_price and btc_price > 130000:
        if btc_dominance and btc_dominance < 58:
            return 'BUY', "Breakout confirmed + altseason signal"
        return 'BUY', "BTC breakout confirmed"

    # Default: wait and see
    return 'CAUTION', "Consolidation phase - defensive"


def get_fear_greed_index():
    """Get Fear & Greed Index from alternative.me API"""
    url = "https://api.alternative.me/fng/?limit=1"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and len(data['data']) > 0:
                value = int(data['data'][0]['value'])
                classification = data['data'][0]['value_classification']
                return value, classification
        return None, None
    except Exception as e:
        print(f"Error fetching Fear & Greed: {e}")
        return None, None


def calculate_rsi(prices, period=14):
    """Calculate RSI (Relative Strength Index)"""
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


def get_rsi_for_coin(coin_symbol):
    """Get RSI for any coin using hourly data"""
    url = "https://min-api.cryptocompare.com/data/v2/histohour"
    params = {
        'fsym': coin_symbol,
        'tsym': 'USD',
        'limit': 50
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'Data' in data and 'Data' in data['Data']:
                candles = data['Data']['Data']
                prices = [candle['close'] for candle in candles]
                return calculate_rsi(prices, period=14)
        return None
    except Exception as e:
        print(f"Error calculating RSI for {coin_symbol}: {e}")
        return None


def get_volume_comparison(symbol):
    """Get 7-day average volume vs 30-day average volume"""
    try:
        url = "https://min-api.cryptocompare.com/data/v2/histohour"
        params = {
            'fsym': symbol,
            'tsym': 'USD',
            'limit': 720  # 30 days of hourly data
        }

        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            return None

        data = response.json()
        if 'Data' not in data or 'Data' not in data['Data']:
            return None

        candles = data['Data']['Data']

        if len(candles) < 168:  # Need at least 7 days
            return None

        # Last 7 days volume (168 hours)
        volume_7d = sum([c['volumeto'] for c in candles[-168:]])
        avg_hourly_7d = volume_7d / 168

        # 30 days average hourly volume
        total_volume_30d = sum([c['volumeto'] for c in candles])
        avg_hourly_30d = total_volume_30d / len(candles)

        # Compare 7d average to 30d average
        volume_vs_avg = ((avg_hourly_7d / avg_hourly_30d) - 1) * 100 if avg_hourly_30d > 0 else 0

        return round(volume_vs_avg, 1)

    except:
        return None


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
        # BTC Dominance
        print("Fetching BTC Dominance...")
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

        # ETH/BTC ratio
        print("Fetching ETH/BTC ratio...")
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

        # Alt Volume Share
        print("Calculating alt volume share...")
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


# ========== STRUCTURAL DIVERGENCE (90-DAY PORTFOLIO POSITIONING) ==========
# These functions are for PORTFOLIO decisions - strength/weakness identification

def get_long_term_price_change(coin_symbol, days=90, retries=3):
    """
    Get long-term price change using CryptoCompare API (same as old divergence_reporter)

    Args:
        coin_symbol: Coin symbol like 'BTC', 'ETH', 'SOL' (from ALTCOINS values in config)
        days: Number of days to look back (60, 90, 120, 180)
        retries: Number of retry attempts

    Returns: percentage change or None
    """
    url = "https://min-api.cryptocompare.com/data/v2/histoday"
    params = {
        'fsym': coin_symbol,
        'tsym': 'USD',
        'limit': days
    }

    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if 'Data' in data and 'Data' in data['Data']:
                    candles = data['Data']['Data']
                    if len(candles) >= 2:
                        price_start = candles[0]['close']
                        price_now = candles[-1]['close']

                        if price_start > 0:
                            change_pct = ((price_now - price_start) / price_start) * 100
                            return round(change_pct, 2)

            if attempt < retries - 1:
                time.sleep(2)

        except Exception as e:
            print(f"Error fetching {days}d data for {coin_symbol}: {e}")
            if attempt < retries - 1:
                time.sleep(2)

    return None


def calculate_structural_divergence(alt_change, btc_change):
    """
    Calculate structural divergence and categorize position

    NOTE: This is INFORMATION about market dynamics, not a direct trade signal.
    Use this to understand which assets are winning/losing their sector competition.
    Combine with 14-day divergence for actual entry/exit timing.

    Returns: {
        'divergence': float,
        'category': str,  # 'LEADER', 'STRONG', 'TRACKER', 'WEAK', 'LAGGARD'
        'signal': str     # Informational - what happened over 90 days
    }
    """
    if alt_change is None or btc_change is None:
        return None

    divergence = alt_change - btc_change

    # Categorization thresholds (adjusted for 90-day timeframe)
    if divergence > 35:
        category = "LEADER"
        signal = "🟢 Strongly outperformed BTC"
    elif divergence > 15:
        category = "STRONG"
        signal = "🟢 Outperformed BTC"
    elif divergence > -15:
        category = "TRACKER"
        signal = "🟡 Tracked BTC (neutral)"
    elif divergence > -35:
        category = "WEAK"
        signal = "🟠 Underperformed BTC"
    else:
        category = "LAGGARD"
        signal = "🔴 Strongly underperformed BTC"

    return {
        'divergence': round(divergence, 2),
        'category': category,
        'signal': signal
    }


def get_sector_leaders(category='infrastructure', days=90):
    """
    Compare coins within a sector to find structural leaders

    Args:
        category: 'infrastructure', 'defi', or 'all'
        days: Lookback period (60, 90, 120, 180) - default 90

    Returns: Analysis dict with categorized results
    """

    # Define sectors
    sectors = {
        'infrastructure': [
            'ethereum', 'solana', 'cardano', 'polkadot', 'avalanche-2', 'internet-computer',
            'injective-protocol', 'sui', 'sei-network', 'celestia'
        ],
        'defi': ['chainlink'],
        'pow': ['bitcoin', 'litecoin', 'kaspa', 'zcash'],
        'all': [k for k in ALTCOINS.keys() if k != 'pax-gold']
    }

    if category not in sectors:
        category = 'all'

    coins_to_analyze = sectors[category]

    print(f"\n{'='*70}")
    print(f"STRUCTURAL ANALYSIS - {category.upper()} SECTOR ({days} days)")
    print(f"{'='*70}\n")

    # Get BTC baseline
    print(f"Fetching BTC {days}-day performance...")
    btc_change = get_long_term_price_change('BTC', days)

    if not btc_change:
        print("❌ Could not fetch BTC data")
        return None

    print(f"✅ BTC {days}d: {btc_change:+.2f}%\n")

    # Analyze each coin
    results = []

    for coin_id in coins_to_analyze:
        symbol = ALTCOINS.get(coin_id, coin_id.upper())
        print(f"Analyzing {symbol}...", end=" ")

        # Use symbol for CryptoCompare API
        alt_change = get_long_term_price_change(symbol, days)

        if alt_change is None:
            print("❌ No data")
            continue

        analysis = calculate_structural_divergence(alt_change, btc_change)

        if analysis:
            results.append({
                'symbol': symbol,
                'coin_id': coin_id,
                f'change_{days}d': alt_change,
                **analysis
            })
            print(f"✅ {analysis['category']}")

    # Sort by divergence (best to worst)
    results.sort(key=lambda x: x['divergence'], reverse=True)

    return {
        'btc_baseline': btc_change,
        'coins': results,
        'timeframe_days': days,
        'timestamp': datetime.now().isoformat()
    }


def print_structural_report(analysis):
    """Print formatted structural analysis report"""

    if not analysis or not analysis['coins']:
        print("No data available")
        return

    days = analysis.get('timeframe_days', 90)

    print(f"\n{'='*70}")
    print(f"STRUCTURAL DIVERGENCE REPORT")
    print(f"{days}-Day Performance vs BTC (Baseline: {analysis['btc_baseline']:+.2f}%)")
    print(f"{'='*70}\n")

    # Group by category
    categories = {
        'LEADER': [],
        'STRONG': [],
        'TRACKER': [],
        'WEAK': [],
        'LAGGARD': []
    }

    for coin in analysis['coins']:
        categories[coin['category']].append(coin)

    # Print each category
    for category, coins in categories.items():
        if not coins:
            continue

        # Header emoji
        emoji_map = {
            'LEADER': "🏆",
            'STRONG': "💪",
            'TRACKER': "➡️",
            'WEAK': "⚠️",
            'LAGGARD': "🚨"
        }

        emoji = emoji_map.get(category, "❓")

        print(f"{emoji} {category} ({len(coins)} coins)")
        print("-" * 70)

        for coin in coins:
            change_key = f'change_{days}d'
            print(f"\n{coin['symbol']}:")
            print(f"  {days}d change: {coin[change_key]:+.2f}%")
            print(f"  Divergence: {coin['divergence']:+.2f}% vs BTC")
            print(f"  {coin['signal']}")

        print()

    # Key insights section (no prescriptive actions)
    print(f"{'='*70}")
    print("KEY INSIGHTS")
    print(f"{'='*70}\n")

    leaders = categories['LEADER'] + categories['STRONG']
    laggards = categories['LAGGARD'] + categories['WEAK']

    if leaders:
        leader_symbols = [c['symbol'] for c in leaders]
        print(f"💪 Sector Winners: {', '.join(leader_symbols)}")
        print(f"   These outperformed BTC over {days} days\n")

    if laggards:
        laggard_symbols = [c['symbol'] for c in laggards]
        print(f"📉 Sector Laggards: {', '.join(laggard_symbols)}")
        print(f"   These underperformed BTC over {days} days\n")

    trackers = categories['TRACKER']
    if trackers:
        tracker_symbols = [c['symbol'] for c in trackers]
        print(f"➡️  Neutral Performance: {', '.join(tracker_symbols)}")
        print(f"   These tracked BTC closely\n")

    print(f"💡 Use this info to ask: Why are winners outperforming?")
    print(f"   Combine with seasonal patterns & catalysts for context.")


def get_portfolio_health_check(holdings, days=90):
    """
    Check structural health of your actual portfolio

    Args:
        holdings: dict like {'ethereum': 2000, 'cosmos': 1000, ...}
                  Keys must match coin_ids, values are $ amounts
        days: Lookback period (60, 90, 120, 180)

    Returns: Portfolio health analysis
    """

    print(f"\n{'='*70}")
    print(f"PORTFOLIO HEALTH CHECK ({days} days)")
    print(f"{'='*70}\n")

    # Get BTC baseline
    btc_change = get_long_term_price_change('BTC', days)
    if not btc_change:
        print("❌ Could not fetch BTC data")
        return None

    print(f"BTC {days}d baseline: {btc_change:+.2f}%\n")

    # Analyze each holding
    total_value = sum(holdings.values())
    results = []

    for coin_id, value in holdings.items():
        if coin_id == BITCOIN_ID:  # Skip BTC itself
            continue

        symbol = ALTCOINS.get(coin_id, coin_id.upper())
        weight_pct = (value / total_value) * 100

        print(f"Analyzing {symbol} ({weight_pct:.1f}% of portfolio)...", end=" ")

        # Use symbol for CryptoCompare
        alt_change = get_long_term_price_change(symbol, days)

        if alt_change is None:
            print("❌ No data")
            continue

        analysis = calculate_structural_divergence(alt_change, btc_change)

        if analysis:
            results.append({
                'symbol': symbol,
                'coin_id': coin_id,
                'value': value,
                'weight_pct': weight_pct,
                f'change_{days}d': alt_change,
                **analysis
            })
            print(f"✅ {analysis['category']}")

    # Calculate portfolio health score
    health_score = 0
    for holding in results:
        # Weight each position's divergence by portfolio weight
        weighted_contribution = holding['divergence'] * (holding['weight_pct'] / 100)
        health_score += weighted_contribution

    # Print results
    print(f"\n{'='*70}")
    print("PORTFOLIO COMPOSITION")
    print(f"{'='*70}\n")

    change_key = f'change_{days}d'
    for holding in sorted(results, key=lambda x: x['weight_pct'], reverse=True):
        print(f"{holding['symbol']}: ${holding['value']:,.0f} ({holding['weight_pct']:.1f}%)")
        print(f"  {holding['signal']}")
        print(f"  {days}d: {holding[change_key]:+.2f}% (div: {holding['divergence']:+.2f}%)\n")

    # Overall assessment
    print(f"{'='*70}")
    print("OVERALL PORTFOLIO HEALTH")
    print(f"{'='*70}\n")

    print(f"Weighted divergence score: {health_score:+.2f}%\n")

    if health_score > 10:
        assessment = "🟢 STRONG - Portfolio outperformed BTC over {days} days"
    elif health_score > -5:
        assessment = "🟡 NEUTRAL - Portfolio tracked BTC over {days} days"
    else:
        assessment = "🔴 WEAK - Portfolio underperformed BTC over {days} days"

    print(f"Assessment: {assessment}\n")

    # Informational breakdown
    laggards = [h for h in results if h['category'] in ['LAGGARD', 'WEAK']]
    if laggards:
        total_laggard_value = sum(h['value'] for h in laggards)
        laggard_pct = (total_laggard_value / total_value) * 100

        print(f"📊 Info: {laggard_pct:.1f}% of portfolio in underperforming assets")
        print(f"   {', '.join(h['symbol'] for h in laggards)}\n")

    leaders = [h for h in results if h['category'] in ['LEADER', 'STRONG']]
    if leaders:
        total_leader_value = sum(h['value'] for h in leaders)
        leader_pct = (total_leader_value / total_value) * 100

        print(f"📊 Info: {leader_pct:.1f}% of portfolio in outperforming assets")
        print(f"   {', '.join(h['symbol'] for h in leaders)}\n")

    return {
        'holdings': results,
        'health_score': health_score,
        'assessment': assessment,
        'btc_baseline': btc_change,
        'timeframe_days': days
    }


# ========== COMMAND LINE USAGE ==========

if __name__ == "__main__":
    import sys

    print("DIVERGENCE REPORTER - Structural Analysis Mode")
    print("="*70)

    # Command line usage
    if len(sys.argv) > 1:
        command = sys.argv[1]

        # Optional: specify days (default 90)
        days = 90
        if len(sys.argv) > 2:
            try:
                days = int(sys.argv[2])
            except:
                days = 90

        if command == 'infrastructure':
            analysis = get_sector_leaders('infrastructure', days)
            if analysis:
                print_structural_report(analysis)

        elif command == 'all':
            analysis = get_sector_leaders('all', days)
            if analysis:
                print_structural_report(analysis)

        elif command == 'portfolio':
            # Example portfolio - replace with your actual holdings
            my_holdings = {
                'ethereum': 2000,
                'cosmos': 1000,
            }

            health = get_portfolio_health_check(my_holdings, days)

        else:
            print("Usage:")
            print("  python divergence_reporter.py infrastructure [days]  # Analyze L1s")
            print("  python divergence_reporter.py all [days]             # Analyze all alts")
            print("  python divergence_reporter.py portfolio [days]       # Check portfolio")
            print("\nOptional: Specify days (60, 90, 120, 180) - default is 90")

    else:
        # Default: analyze ALL alts with 90 days
        print("Running analysis on ALL altcoins (90 days)...\n")
        analysis = get_sector_leaders('all', 90)
        if analysis:
            print_structural_report(analysis)

        print("\n" + "="*70)
        print("TIP: Run with 'infrastructure' for L1s only, or add timeframe:")
        print("     python divergence_reporter.py all 120")
        print("="*70)
