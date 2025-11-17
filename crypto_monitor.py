import requests
from datetime import datetime, timedelta
import pytz
from config import *
import time

def send_telegram_message(message):
    """Send message to Telegram with error handling"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }

    try:
        # DEBUG: Print first 500 chars of message
        print(f"DEBUG - First 500 chars of message:")
        print(message[:500])
        print(f"DEBUG - Last 500 chars:")
        print(message[-500:])
        
        response = requests.post(url, json=payload, timeout=10)
        print(f"Telegram API Response Status: {response.status_code}")

        if response.status_code == 200:
            print("✅ Message sent successfully to Telegram")
            return True
        else:
            print(f"❌ Telegram API error: {response.text}")
            
            # Try without HTML parsing as fallback
            print("Trying without HTML parsing...")
            payload['parse_mode'] = None
            response2 = requests.post(url, json=payload, timeout=10)
            if response2.status_code == 200:
                print("✅ Sent without HTML formatting")
                return True
            return False
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        return False

def get_current_prices():
    """Get current prices for Bitcoin and altcoins"""
    all_coins = [BITCOIN_ID] + list(ALTCOINS.keys())
    coins_param = ','.join(all_coins)

    url = f"https://api.coingecko.com/api/v3/simple/price"

    headers = {
        'accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    params = {
        'ids': coins_param,
        'vs_currencies': 'usd',
        'include_24hr_change': 'true',
        'include_24hr_vol': 'true',
        'precision': '2'
    }

    try:
        for attempt in range(3):
            response = requests.get(url, params=params, headers=headers, timeout=15)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                print(f"Rate limited, waiting 60 seconds... (attempt {attempt+1}/3)")
                time.sleep(60)
            else:
                print(f"Error {response.status_code}: {response.text}")
                if attempt < 2:
                    time.sleep(10)

        return None
    except Exception as e:
        print(f"Error fetching prices: {e}")
        return None

def get_historical_price(coin_id, days_ago):
    """Get historical price for a coin"""
    date = datetime.now(pytz.timezone(TIMEZONE)) - timedelta(days=days_ago)
    timestamp = int(date.timestamp())

    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart/range"

    headers = {
        'accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    params = {
        'vs_currency': 'usd',
        'from': timestamp - 7200,
        'to': timestamp + 7200,
        'precision': '2'
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)

        if response.status_code == 200:
            data = response.json()
            if 'prices' in data and len(data['prices']) > 0:
                middle_idx = len(data['prices']) // 2
                return data['prices'][middle_idx][1]
        else:
            print(f"Error fetching historical price for {coin_id}: {response.status_code}")

        return None
    except Exception as e:
        print(f"Error fetching historical price for {coin_id}: {e}")
        return None

def calculate_divergence(btc_change, alt_change):
    """Calculate divergence between BTC and altcoin"""
    return round(alt_change - btc_change, 2)

def get_montevideo_time():
    """Get current time in Montevideo"""
    tz = pytz.timezone(TIMEZONE)
    return datetime.now(tz)

def get_ohlcv_data():
    """Get OHLC data for Bitcoin"""
    url = f"https://api.coingecko.com/api/v3/coins/bitcoin/ohlc"

    headers = {
        'accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    params = {
        'vs_currency': 'usd',
        'days': '1',
        'precision': '2'
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching OHLC: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching OHLC data: {e}")
        return None

def get_btc_etf_flows():
    """Get BTC ETF flow data with fallback"""
    try:
        url = "https://open-api.coinglass.com/public/v2/indicator"
        params = {
            'symbol': 'BTC',
            'type': 'etf_holding',
            'interval': '0'
        }

        headers = {
            'accept': 'application/json',
            'User-Agent': 'Mozilla/5.0'
        }

        response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()

            if data.get('success') and data.get('data'):
                etf_records = data['data']

                if len(etf_records) > 0:
                    latest = etf_records[0]

                    flows_7d = []
                    for record in etf_records[:7]:
                        if 'netFlow' in record:
                            flows_7d.append(record['netFlow'])

                    avg_7d = sum(flows_7d) / len(flows_7d) if flows_7d else 0

                    print("✅ ETF data fetched from CoinGlass")

                    return {
                        'latest_flow': latest.get('netFlow', 0),
                        'total_holdings': latest.get('totalHolding', 1100000),
                        'avg_7d': avg_7d,
                        'date': latest.get('createTime', datetime.now().strftime('%Y-%m-%d')),
                        'success': True,
                        'fallback': False
                    }
    except Exception as e:
        print(f"⚠️ CoinGlass ETF API error: {e}")

    print("⚠️ Using estimated ETF data (API unavailable)")

    return {
        'latest_flow': 0,
        'total_holdings': 1100000,
        'avg_7d': 50,
        'date': datetime.now().strftime('%Y-%m-%d'),
        'success': False,
        'fallback': True
    }

def interpret_etf_flows(etf_data):
    """Interpret ETF flow data"""
    if not etf_data:
        return None

    latest_flow = etf_data.get('latest_flow', 0)
    avg_7d = etf_data.get('avg_7d', 0)
    holdings = etf_data.get('total_holdings', 0)
    is_fallback = etf_data.get('fallback', False)

    TOTAL_BTC_SUPPLY = 21_000_000
    holdings_pct = (holdings / TOTAL_BTC_SUPPLY) * 100 if holdings > 0 else 0

    if latest_flow > 1000:
        flow_signal = "🟢 STRONG INFLOW"
        flow_desc = f"+{latest_flow:,.0f} BTC (institutional accumulation)"
    elif latest_flow > 100:
        flow_signal = "🟢 INFLOW"
        flow_desc = f"+{latest_flow:,.0f} BTC (buying pressure)"
    elif latest_flow < -1000:
        flow_signal = "🔴 STRONG OUTFLOW"
        flow_desc = f"{latest_flow:,.0f} BTC (distribution phase)"
    elif latest_flow < -100:
        flow_signal = "🔴 OUTFLOW"
        flow_desc = f"{latest_flow:,.0f} BTC (profit-taking)"
    else:
        flow_signal = "🟡 NEUTRAL"
        flow_desc = f"{latest_flow:+,.0f} BTC (balanced)"

    if avg_7d > 500:
        trend_signal = "🟢 Strong accumulation"
    elif avg_7d > 100:
        trend_signal = "🟢 Positive trend"
    elif avg_7d < -500:
        trend_signal = "🔴 Heavy distribution"
    elif avg_7d < -100:
        trend_signal = "🔴 Negative trend"
    else:
        trend_signal = "🟡 Neutral"

    if holdings_pct >= 12:
        holdings_signal = "🚀 SCARCITY PHASE"
        holdings_desc = f"ETFs hold {holdings_pct:.1f}% of supply"
    elif holdings_pct >= 10:
        holdings_signal = "📊 APPROACHING THESIS"
        holdings_desc = f"ETFs hold {holdings_pct:.1f}% of supply"
    elif holdings_pct >= 7:
        holdings_signal = "📊 BUILDING POSITION"
        holdings_desc = f"ETFs hold {holdings_pct:.1f}% of supply"
    else:
        holdings_signal = "📊 EARLY STAGE"
        holdings_desc = f"ETFs hold {holdings_pct:.1f}% of supply"

    return {
        'flow_signal': flow_signal,
        'flow_desc': flow_desc,
        'trend_signal': trend_signal,
        'avg_7d': avg_7d,
        'holdings_signal': holdings_signal,
        'holdings_desc': holdings_desc,
        'holdings_pct': holdings_pct,
        'is_fallback': is_fallback
    }

def get_funding_rate():
    """
    Get BTC perpetual futures funding rate from CoinGlass

    WHAT IT MEANS:
    - Funding rate = fee paid every 8 hours between longs and shorts
    - Keeps perpetual futures price aligned with spot price

    INTERPRETATION:
    - Positive rate = longs pay shorts (market bullish, longs dominate)
    - Negative rate = shorts pay longs (market bearish, shorts dominate)

    THRESHOLDS:
    - Normal: ±0.01% (0.0001) - healthy balanced market
    - Elevated: ±0.03-0.05% - market getting one-sided
    - EXTREME: >±0.05% (±0.0005) - overleveraged, flush incoming

    WHY IT MATTERS:
    - High positive funding (>0.05%) = too many longs = local top risk
    - High negative funding (<-0.05%) = too many shorts = bottom opportunity
    - Extreme funding precedes liquidation cascades
    """
    try:
        url = "https://open-api.coinglass.com/public/v2/funding"
        params = {
            'symbol': 'BTC',
            'interval': '0'  # Current funding rate
        }

        headers = {
            'accept': 'application/json',
            'User-Agent': 'Mozilla/5.0'
        }

        response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()

            if data.get('success') and data.get('data'):
                # CoinGlass returns list of exchanges
                funding_records = data['data']

                # Average funding across major exchanges
                funding_rates = []
                for record in funding_records:
                    if 'uMarginList' in record:
                        for exchange_data in record['uMarginList']:
                            rate = exchange_data.get('rate')
                            if rate is not None:
                                funding_rates.append(float(rate))

                if not funding_rates:
                    print("⚠️ No funding rate data available")
                    return None

                # Calculate average funding rate
                avg_funding = sum(funding_rates) / len(funding_rates)

                # Convert to percentage (CoinGlass returns decimal)
                funding_pct = avg_funding * 100

                # Annualized rate (3 fundings per day * 365 days)
                annualized = funding_pct * 3 * 365

                # Interpretation
                if avg_funding > 0.0005:  # >0.05%
                    signal = "🔴 EXTREME BULLISH"
                    explanation = "DANGER: Overleveraged longs, flush risk"
                    risk_level = "HIGH"
                elif avg_funding > 0.0003:  # >0.03%
                    signal = "🟡 ELEVATED BULLISH"
                    explanation = "Longs dominating, watch for correction"
                    risk_level = "MODERATE"
                elif avg_funding > 0.0001:  # >0.01%
                    signal = "🟢 HEALTHY BULLISH"
                    explanation = "Normal long bias, sustainable"
                    risk_level = "LOW"
                elif avg_funding > -0.0001:  # Between -0.01% and +0.01%
                    signal = "⚪ NEUTRAL"
                    explanation = "Balanced market, no extreme leverage"
                    risk_level = "LOW"
                elif avg_funding > -0.0003:  # > -0.03%
                    signal = "🟢 HEALTHY BEARISH"
                    explanation = "Normal short bias, sustainable"
                    risk_level = "LOW"
                elif avg_funding > -0.0005:  # > -0.05%
                    signal = "🟡 ELEVATED BEARISH"
                    explanation = "Shorts dominating, watch for squeeze"
                    risk_level = "MODERATE"
                else:  # < -0.05%
                    signal = "🔴 EXTREME BEARISH"
                    explanation = "DANGER: Overleveraged shorts, squeeze risk"
                    risk_level = "HIGH"

                print(f"✅ Funding rate fetched: {funding_pct:.4f}%")

                return {
                    'rate': avg_funding,
                    'rate_pct': funding_pct,
                    'annualized_pct': annualized,
                    'signal': signal,
                    'explanation': explanation,
                    'risk_level': risk_level,
                    'success': True
                }
        else:
            print(f"❌ CoinGlass funding API error: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ Error fetching funding rate: {e}")
        return None


def get_open_interest():
    """
    Get BTC perpetual futures open interest from CoinGlass

    WHAT IT MEANS:
    - Open Interest (OI) = total value of all open futures contracts
    - Shows how much leverage is in the market
    - Higher OI = more leverage = more potential for cascades

    INTERPRETATION:
    - High OI + rising price = many longs, extended, cascade risk
    - High OI + falling price = many shorts, oversold, squeeze potential
    - Low OI = little leverage, stable but boring

    THRESHOLDS (BTC):
    - Low OI: <$15B - stable, low volatility
    - Normal OI: $15-25B - healthy leverage
    - High OI: $25-35B - elevated risk
    - EXTREME OI: >$35B - liquidation cascade danger

    WHY IT MATTERS:
    - Predicts volatility (high OI = violent moves possible)
    - Combined with funding = top/bottom signals
    - Your "choppy consolidation" = leverage flush phase (high OI clearing)
    """
    try:
        url = "https://open-api.coinglass.com/public/v2/open_interest"
        params = {
            'symbol': 'BTC',
            'interval': '0'  # Current OI
        }

        headers = {
            'accept': 'application/json',
            'User-Agent': 'Mozilla/5.0'
        }

        response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()

            if data.get('success') and data.get('data'):
                oi_records = data['data']

                # Sum OI across all exchanges
                total_oi_usd = 0
                for record in oi_records:
                    if 'usdAmount' in record:
                        total_oi_usd += float(record['usdAmount'])

                if total_oi_usd == 0:
                    print("⚠️ No open interest data available")
                    return None

                # Convert to billions
                oi_billions = total_oi_usd / 1_000_000_000

                # Interpretation
                if oi_billions > 35:
                    signal = "🔴 EXTREME HIGH"
                    explanation = "DANGER: Massive leverage, cascade risk"
                    volatility = "VERY HIGH"
                elif oi_billions > 25:
                    signal = "🟡 ELEVATED"
                    explanation = "High leverage, watch for volatility"
                    volatility = "HIGH"
                elif oi_billions > 15:
                    signal = "🟢 NORMAL"
                    explanation = "Healthy leverage levels"
                    volatility = "MODERATE"
                else:
                    signal = "⚪ LOW"
                    explanation = "Little leverage, stable but boring"
                    volatility = "LOW"

                print(f"✅ Open Interest fetched: ${oi_billions:.2f}B")

                return {
                    'oi_usd': total_oi_usd,
                    'oi_billions': oi_billions,
                    'signal': signal,
                    'explanation': explanation,
                    'volatility': volatility,
                    'success': True
                }
        else:
            print(f"❌ CoinGlass OI API error: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ Error fetching open interest: {e}")
        return None


def interpret_leverage_conditions(funding_data, oi_data):
    """
    Combine funding rate + open interest for actionable signals

    THE FRAMEWORK (from Day 12 education):

    1. HIGH FUNDING + HIGH OI = TOP NEAR (WAIT)
       - Too many overleveraged longs
       - Cascade risk imminent
       - Don't chase, wait for flush

    2. NEGATIVE FUNDING + HIGH OI = BOTTOM NEAR (DEPLOY)
       - Too many overleveraged shorts
       - Short squeeze potential
       - Accumulation opportunity

    3. LOW OI = STABLE (BORING, NO TRADE)
       - Little leverage in system
       - Low volatility expected
       - Wait for setup

    4. EXTREME FUNDING (either direction) = DANGER
       - Market maximally one-sided
       - Liquidation cascade imminent
       - Step aside or take counter-position
    """
    if not funding_data or not oi_data:
        return None

    funding_risk = funding_data.get('risk_level', 'LOW')
    oi_volatility = oi_data.get('volatility', 'LOW')
    funding_rate = funding_data.get('rate', 0)
    oi_billions = oi_data.get('oi_billions', 0)

    # Determine overall market condition
    if funding_risk == 'HIGH' and oi_volatility in ['HIGH', 'VERY HIGH']:
        if funding_rate > 0:
            condition = "🔴 DANGER ZONE - TOP RISK"
            action = "WAIT - Overleveraged longs, flush coming"
            trade_signal = "DO NOT BUY"
        else:
            condition = "🟢 OPPORTUNITY - BOTTOM SIGNAL"
            action = "DEPLOY - Overleveraged shorts, squeeze coming"
            trade_signal = "ACCUMULATE"
    elif oi_volatility == 'LOW':
        condition = "⚪ BORING MARKET"
        action = "WAIT - Low leverage, low volatility expected"
        trade_signal = "NO TRADE"
    elif funding_risk == 'MODERATE':
        condition = "🟡 CAUTION"
        action = "MONITOR - Market getting one-sided"
        trade_signal = "SMALL POSITIONS ONLY"
    else:
        condition = "🟢 HEALTHY"
        action = "NORMAL - Balanced market conditions"
        trade_signal = "FOLLOW PLAN"

    return {
        'condition': condition,
        'action': action,
        'trade_signal': trade_signal,
        'explanation': f"Funding {funding_data['signal']} + OI {oi_data['signal']}"
    }
