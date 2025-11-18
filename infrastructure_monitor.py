#!/usr/bin/env python3
"""
Infrastructure Monitor
Tracks L1 competition and macro environment for strategic allocation
Runs weekly to validate investment thesis
"""

from crypto_monitor import *
from config import *
import time
import requests

# Infrastructure coins for monitoring
INFRASTRUCTURE_COINS = {
    'ethereum': 'ETH',
    'solana': 'SOL',
    'cardano': 'ADA',
    'polkadot': 'DOT',
    'avalanche-2': 'AVAX',
    'internet-computer': 'ICP'
}

def get_l1_ratios():
    """Get all L1/BTC ratios with 7-day trends"""
    print("Fetching L1/BTC ratios...")

    ratios = {}

    # Get BTC price
    url_btc = "https://api.coingecko.com/api/v3/simple/price"
    params_btc = {'ids': 'bitcoin', 'vs_currencies': 'usd'}

    try:
        time.sleep(2)
        response_btc = requests.get(url_btc, params=params_btc, timeout=10)
        if response_btc.status_code != 200:
            print("Error fetching BTC price")
            return None

        btc_price = response_btc.json().get('bitcoin', {}).get('usd', 0)

        if btc_price == 0:
            return None

        # Get 7-day data for each L1
        for coin_id, symbol in INFRASTRUCTURE_COINS.items():
            print(f"  Processing {symbol}...")

            url_hist = "https://min-api.cryptocompare.com/data/v2/histohour"
            params_hist = {'fsym': symbol, 'tsym': 'BTC', 'limit': 168}  # 7 days

            time.sleep(3)
            response = requests.get(url_hist, params=params_hist, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if 'Data' in data and 'Data' in data['Data']:
                    candles = data['Data']['Data']

                    current_ratio = candles[-1]['close']
                    ratio_7d_ago = candles[0]['close']
                    trend_7d = ((current_ratio - ratio_7d_ago) / ratio_7d_ago) * 100

                    ratios[symbol] = {
                        'ratio': round(current_ratio, 8),
                        'trend_7d': round(trend_7d, 2)
                    }

        return ratios

    except Exception as e:
        print(f"Error fetching L1 ratios: {e}")
        return None

def get_dxy():
    """Get EUR/USD as proxy for dollar strength"""
    print("Fetching EUR/USD (Dollar proxy)...")

    api_key = "7fd7e4bd0c4be5b5d382faaa64e8d9ee"

    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        'series_id': 'DEXUSEU',  # USD per EUR
        'api_key': api_key,
        'file_type': 'json',
        'sort_order': 'desc',
        'limit': 10
    }

    try:
        time.sleep(2)
        response = requests.get(url, params=params, timeout=15)

        if response.status_code == 200:
            data = response.json()

            if 'observations' in data and len(data['observations']) > 0:
                for obs in data['observations']:
                    value = obs.get('value', '.')
                    if value != '.':
                        eur_usd = float(value)

                        # Invert to show dollar strength (lower EUR/USD = stronger dollar)
                        dollar_strength = 100 / eur_usd  # Normalized

                        return {
                            'value': round(dollar_strength, 2),
                            'proxy': True,
                            'eur_usd': eur_usd
                        }

        return None

    except Exception as e:
        print(f"  ❌ Dollar proxy error: {e}")
        return None

def get_eth_gas_fees():
    """Get current ETH gas fees from alternative source (no API key needed)"""
    print("Fetching ETH gas fees...")

    # Use Blocknative Gas Platform (free, no key)
    url = "https://api.blocknative.com/gasprices/blockprices"

    try:
        time.sleep(2)
        response = requests.get(url, timeout=15)

        print(f"  Blocknative status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            if 'blockPrices' in data and len(data['blockPrices']) > 0:
                prices = data['blockPrices'][0]['estimatedPrices']

                # Find different confidence levels (keep as float, gas is < 1 gwei now!)
                safe = None
                standard = None
                fast = None

                for price in prices:
                    confidence = price.get('confidence', 0)
                    max_fee = round(price.get('maxFeePerGas', 0), 2)  # Round to 2 decimals

                    if confidence >= 99:
                        safe = max_fee
                    elif confidence >= 95:
                        standard = max_fee
                    elif confidence >= 90:
                        fast = max_fee

                # Use available data (allow values < 1)
                if standard is not None or fast is not None or safe is not None:
                    result = {
                        'safe': safe or standard or fast,
                        'standard': standard or fast or safe,
                        'fast': fast or standard or safe
                    }
                    print(f"  ✅ Gas fees retrieved: {result['standard']} gwei")
                    return result

        # Fallback: Try OwlRacle (another free source)
        print("  Trying alternative source (OwlRacle)...")
        time.sleep(2)

        url_owl = "https://api.owlracle.info/v4/eth/gas"
        response_owl = requests.get(url_owl, timeout=15)

        print(f"  OwlRacle status: {response_owl.status_code}")

        if response_owl.status_code == 200:
            data_owl = response_owl.json()

            if 'speeds' in data_owl:
                speeds = data_owl['speeds']

                # OwlRacle returns array with different speeds (keep as float)
                safe = round(speeds[0].get('maxFeePerGas', 0), 2) if len(speeds) > 0 else 0
                standard = round(speeds[1].get('maxFeePerGas', 0), 2) if len(speeds) > 1 else 0
                fast = round(speeds[3].get('maxFeePerGas', 0), 2) if len(speeds) > 3 else 0

                if standard > 0 or safe > 0 or fast > 0:
                    result = {
                        'safe': safe or standard or fast,
                        'standard': standard or safe or fast,
                        'fast': fast or standard or safe
                    }
                    print(f"  ✅ Gas fees retrieved: {result['standard']} gwei")
                    return result

        print("  ❌ All gas sources failed")
        return None

    except Exception as e:
        print(f"  ❌ Gas API error: {e}")
        return None

def get_eth_staking_ratio():
    """Get ETH staking ratio from Beaconcha.in API"""
    print("Fetching ETH staking ratio...")

    url = "https://beaconcha.in/api/v1/epoch/latest"

    try:
        time.sleep(2)
        response = requests.get(url, timeout=15)

        print(f"  Beaconcha.in status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            if 'data' in data:
                # Get validator count
                validators = data['data'].get('validatorscount', 0)

                # Each validator stakes 32 ETH
                staked_eth = validators * 32

                # Total ETH supply (approximate, updates slowly)
                total_eth_supply = 120500000  # ~120.5M as of late 2024

                staking_ratio = (staked_eth / total_eth_supply) * 100

                print(f"  ✅ Staking ratio: {staking_ratio:.2f}%")

                return {
                    'ratio': round(staking_ratio, 2),
                    'validators': validators,
                    'staked_eth': round(staked_eth / 1000000, 2)  # In millions
                }

        # Fallback: Try alternative endpoint
        print("  Trying alternative endpoint...")
        time.sleep(2)

        url_alt = "https://beaconcha.in/api/v1/validators/queue"
        response_alt = requests.get(url_alt, timeout=15)

        if response_alt.status_code == 200:
            # This endpoint has less data but might work
            # Return approximate based on known values
            return {
                'ratio': 28.0,  # Approximate as of Q4 2024
                'validators': None,
                'staked_eth': None
            }

        print("  ❌ Failed to fetch staking data")
        return None

    except Exception as e:
        print(f"  ❌ Staking API error: {e}")
        return None

def get_dex_volume_by_chain():
    """Get DEX trading volume by chain from DefiLlama"""
    print("Fetching DEX volume by chain...")

    url = "https://api.llama.fi/overview/dexs?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true&dataType=dailyVolume"

    try:
        time.sleep(2)
        response = requests.get(url, timeout=15)

        print(f"  DefiLlama DEX status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            # Get chains we care about
            chains_data = {}
            total_volume = 0

            # The API returns protocols, we need to aggregate by chain
            if 'protocols' in data:
                chain_volumes = {}

                for protocol in data['protocols']:
                    chains = protocol.get('chains', [])
                    volume_24h = protocol.get('total24h', 0)

                    # Aggregate by chain
                    for chain in chains:
                        if chain not in chain_volumes:
                            chain_volumes[chain] = 0
                        chain_volumes[chain] += volume_24h

                # Extract our L1s
                chains_data['ETH'] = chain_volumes.get('Ethereum', 0)
                chains_data['SOL'] = chain_volumes.get('Solana', 0)
                chains_data['ADA'] = chain_volumes.get('Cardano', 0)
                chains_data['DOT'] = chain_volumes.get('Polkadot', 0)
                chains_data['AVAX'] = chain_volumes.get('Avalanche', 0)

                # Calculate total
                total_volume = sum(chains_data.values())

                # Add percentages
                for chain in chains_data:
                    volume = chains_data[chain]
                    percentage = (volume / total_volume * 100) if total_volume > 0 else 0
                    chains_data[chain] = {
                        'volume': volume,
                        'percentage': round(percentage, 1)
                    }

                print(f"  ✅ DEX volume retrieved for {len(chains_data)} chains")
                return chains_data

        print("  ❌ Failed to fetch DEX volume")
        return None

    except Exception as e:
        print(f"  ❌ DEX volume API error: {e}")
        return None

def get_tvl_by_chain():
    """Get Total Value Locked by chain from DefiLlama"""
    print("Fetching TVL by chain...")

    url = "https://api.llama.fi/v2/chains"

    try:
        time.sleep(2)
        response = requests.get(url, timeout=15)

        print(f"  DefiLlama TVL status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            chains_data = {}

            # Map our symbols to DefiLlama chain names
            chain_mapping = {
                'ETH': 'Ethereum',
                'SOL': 'Solana',
                'ADA': 'Cardano',
                'DOT': 'Polkadot',
                'AVAX': 'Avalanche',
                'BNB': 'BSC',
                'BASE': 'Base',
                'ARB': 'Arbitrum'
            }

            for item in data:
                chain_name = item.get('name', '')

                # Find our chains
                for symbol, llama_name in chain_mapping.items():
                    if chain_name == llama_name:
                        tvl = item.get('tvl', 0)
                        tvl_prev_day = item.get('tvlPrevDay', 0)

                        # Calculate 24h change
                        change_24h = ((tvl - tvl_prev_day) / tvl_prev_day * 100) if tvl_prev_day > 0 else 0

                        chains_data[symbol] = {
                            'tvl': tvl,
                            'change_24h': round(change_24h, 2),
                            'chain_name': llama_name
                        }

            print(f"  ✅ TVL retrieved for {len(chains_data)} chains")
            return chains_data

        print("  ❌ Failed to fetch TVL")
        return None

    except Exception as e:
        print(f"  ❌ TVL API error: {e}")
        return None

# ============================================
# NEW TVL TRACKING FUNCTIONS
# ============================================

def get_historical_tvl(chain_name, days_ago):
    """
    Fetch TVL from X days ago to calculate growth rate
    Uses DefiLlama historical chain TVL endpoint
    """
    print(f"  Fetching TVL history for {chain_name}...")

    url = f"https://api.llama.fi/v2/historicalChainTvl/{chain_name}"

    try:
        time.sleep(2)
        response = requests.get(url, timeout=15)

        if response.status_code == 200:
            data = response.json()

            # Data is array of {date: timestamp, tvl: value}
            if len(data) >= days_ago:
                # Get TVL from days_ago
                target_data = data[-days_ago] if days_ago <= len(data) else data[0]
                historical_tvl = target_data.get('tvl', 0)

                print(f"    ✅ Historical TVL for {chain_name}: ${historical_tvl/1e9:.1f}B")
                return historical_tvl

        return None

    except Exception as e:
        print(f"    ❌ Error fetching historical TVL: {e}")
        return None

def calculate_tvl_growth_rate(symbol, days=30):
    """
    Calculate TVL growth rate over specified period
    Returns percentage change or None
    """
    # Get current TVL
    tvl_data = get_tvl_by_chain()
    if not tvl_data or symbol not in tvl_data:
        return None

    current_tvl = tvl_data[symbol]['tvl']
    chain_name = tvl_data[symbol]['chain_name']

    # Get historical TVL
    historical_tvl = get_historical_tvl(chain_name, days)

    if not historical_tvl or historical_tvl == 0:
        return None

    # Calculate growth rate
    growth_rate = ((current_tvl - historical_tvl) / historical_tvl) * 100

    return round(growth_rate, 1)

def calculate_tvl_ratio(coin_symbol):
    """
    Calculate TVL/Market Cap ratio

    Returns:
        tuple: (ratio, signal)
        - ratio: float (TVL divided by market cap)
        - signal: 'UNDERVALUED' | 'FAIR' | 'OVERVALUED'
    """
    print(f"  Calculating TVL/MC ratio for {coin_symbol}...")

    # Map symbols to CoinGecko IDs
    coin_mapping = {
        'ETH': 'ethereum',
        'SOL': 'solana',
        'AVAX': 'avalanche-2',
        'BNB': 'binancecoin',
        'ADA': 'cardano',
        'DOT': 'polkadot'
    }

    if coin_symbol not in coin_mapping:
        return None, None

    coin_id = coin_mapping[coin_symbol]

    try:
        # Get market cap
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': coin_id,
            'vs_currencies': 'usd',
            'include_market_cap': 'true'
        }

        time.sleep(2)
        response = requests.get(url, params=params, timeout=15)

        if response.status_code != 200:
            return None, None

        data = response.json()
        market_cap = data[coin_id].get('usd_market_cap', 0)

        if market_cap == 0:
            return None, None

        # Get current TVL
        tvl_data = get_tvl_by_chain()
        if not tvl_data or coin_symbol not in tvl_data:
            return None, None

        current_tvl = tvl_data[coin_symbol]['tvl']

        # Calculate ratio
        ratio = current_tvl / market_cap

        # Determine signal
        if ratio > 0.15:
            signal = 'UNDERVALUED'
        elif ratio > 0.08:
            signal = 'FAIR'
        else:
            signal = 'OVERVALUED'

        print(f"    ✅ {coin_symbol} TVL/MC ratio: {ratio:.3f} ({signal})")

        return round(ratio, 3), signal

    except Exception as e:
        print(f"    ❌ Error calculating TVL ratio: {e}")
        return None, None

def get_tvl_regional_summary():
    """
    Get TVL summary by region (Western DeFi vs Asian Speed)
    Returns dict with regional aggregates and growth rates
    """
    print("Calculating TVL regional summary...")

    tvl_data = get_tvl_by_chain()
    if not tvl_data:
        return None

    # Define regions
    western_chains = ['ETH', 'BASE', 'ARB']
    asian_chains = ['SOL', 'BNB']

    # Calculate regional totals
    western_tvl = sum(tvl_data.get(chain, {}).get('tvl', 0) for chain in western_chains if chain in tvl_data)
    asian_tvl = sum(tvl_data.get(chain, {}).get('tvl', 0) for chain in asian_chains if chain in tvl_data)

    # Calculate regional growth rates (30d)
    western_growth_rates = []
    for chain in western_chains:
        if chain in tvl_data:
            growth = calculate_tvl_growth_rate(chain, days=30)
            if growth is not None:
                western_growth_rates.append(growth)

    asian_growth_rates = []
    for chain in asian_chains:
        if chain in tvl_data:
            growth = calculate_tvl_growth_rate(chain, days=30)
            if growth is not None:
                asian_growth_rates.append(growth)

    # Average growth rates
    western_avg_growth = sum(western_growth_rates) / len(western_growth_rates) if western_growth_rates else 0
    asian_avg_growth = sum(asian_growth_rates) / len(asian_growth_rates) if asian_growth_rates else 0

    # Determine capital flow signal
    growth_diff = asian_avg_growth - western_avg_growth

    if growth_diff > 5:
        flow_signal = f"💡 SIGNAL: Capital rotating to Asia (+{growth_diff:.1f}pp)"
    elif growth_diff < -5:
        flow_signal = f"💡 SIGNAL: Capital rotating to West (+{abs(growth_diff):.1f}pp)"
    else:
        flow_signal = "💡 SIGNAL: Balanced capital flows"

    return {
        'western_tvl': western_tvl,
        'western_growth': western_avg_growth,
        'asian_tvl': asian_tvl,
        'asian_growth': asian_avg_growth,
        'flow_signal': flow_signal,
        'growth_diff': growth_diff
    }

def get_alt_quality_score_with_tvl(coin_symbol):
    """
    Enhanced quality score including TVL analysis

    Scoring:
    - TVL/MC ratio: +3 points if >0.15, +1 if >0.10
    - TVL growth 30d: +2 points if >15%, +1 if >5%
    - Price + TVL + Volume aligned: +2 points
    - TVL declining: -3 points (red flag)

    Returns dict with score and metrics
    """
    print(f"Calculating quality score for {coin_symbol}...")

    score = 0
    metrics = {}

    # Get TVL metrics
    tvl_ratio, ratio_signal = calculate_tvl_ratio(coin_symbol)
    tvl_growth_30d = calculate_tvl_growth_rate(coin_symbol, days=30)

    if tvl_ratio is not None:
        metrics['tvl_ratio'] = tvl_ratio
        metrics['ratio_signal'] = ratio_signal

        # TVL/MC Ratio scoring
        if tvl_ratio > 0.15:
            score += 3
        elif tvl_ratio > 0.10:
            score += 1

    if tvl_growth_30d is not None:
        metrics['tvl_growth_30d'] = tvl_growth_30d

        # TVL Growth scoring
        if tvl_growth_30d > 15:
            score += 2
        elif tvl_growth_30d > 5:
            score += 1
        elif tvl_growth_30d < -5:
            score -= 3  # Capital leaving = red flag

    # Get current price/volume data (from your existing functions)
    try:
        from divergence_reporter import get_volume_comparison
        volume_vs_avg = get_volume_comparison(coin_symbol)

        # Get 7d price change
        ratios = get_l1_ratios()
        price_change_7d = ratios.get(coin_symbol, {}).get('trend_7d', 0) if ratios else 0

        metrics['price_change_7d'] = price_change_7d
        metrics['volume_vs_avg'] = volume_vs_avg

        # Three-signal confirmation (all positive = strong)
        if price_change_7d > 3 and tvl_growth_30d and tvl_growth_30d > 3 and volume_vs_avg and volume_vs_avg > 10:
            score += 2
            metrics['three_signal_aligned'] = True
        else:
            metrics['three_signal_aligned'] = False

        # Divergence penalty (price up but TVL flat/down = speculation)
        if price_change_7d > 5 and tvl_growth_30d and tvl_growth_30d < 2:
            score -= 2
            metrics['divergence_warning'] = True
        else:
            metrics['divergence_warning'] = False

    except:
        metrics['three_signal_aligned'] = False
        metrics['divergence_warning'] = False

    metrics['score'] = score

    print(f"  ✅ Quality score for {coin_symbol}: {score} points")

    return metrics

# ============================================
# EXISTING FUNCTIONS CONTINUE BELOW
# ============================================

def get_real_yields():
    """Get 10-Year Real Treasury Yields from FRED API"""
    print("Fetching Real Yields (10Y TIPS)...")

    api_key = "7fd7e4bd0c4be5b5d382faaa64e8d9ee"

    # 10-Year TIPS (Treasury Inflation-Protected Securities) yield
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        'series_id': 'DFII10',
        'api_key': api_key,
        'file_type': 'json',
        'sort_order': 'desc',
        'limit': 10
    }

    try:
        time.sleep(2)
        response = requests.get(url, params=params, timeout=15)

        print(f"  FRED Real Yields status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            if 'observations' in data and len(data['observations']) > 0:
                # Find most recent non-null value
                for obs in data['observations']:
                    value = obs.get('value', '.')
                    if value != '.':
                        real_yield = float(value)
                        date = obs.get('date', '')

                        print(f"  ✅ Real Yields retrieved: {real_yield}% (as of {date})")

                        return {
                            'value': round(real_yield, 2),
                            'date': date
                        }

        print("  ❌ Failed to fetch Real Yields")
        return None

    except Exception as e:
        print(f"  ❌ Real Yields API error: {e}")
        return None

def get_btc_etf_flows():
    """Get Bitcoin ETF flow data from Glassnode"""
    print("Fetching BTC ETF flows...")

    try:
        # Glassnode free endpoint (no key needed for some data)
        url = "https://api.glassnode.com/v1/metrics/distribution/balance_exchanges"
        params = {
            'a': 'BTC',
            'i': '24h'
        }

        time.sleep(2)
        response = requests.get(url, params=params, timeout=15)

        if response.status_code == 200:
            data = response.json()
            if len(data) > 0:
                # Calculate rough flows
                latest = data[-1]
                week_ago = data[-7] if len(data) >= 7 else data[0]
                
                latest_flow = (latest['v'] - week_ago['v']) / 7
                
                print(f"  ✅ ETF flows estimated: {latest_flow:.0f} BTC/day")
                
                return {
                    'latest_flow': round(latest_flow, 2),
                    'avg_7d': round(latest_flow, 2),
                    'total_holdings': 1_375_000,
                    'flows_7d': []
                }
    except Exception as e:
        print(f"  ❌ Glassnode error: {e}")

    # Fallback
    print("  ⚠️ Using estimated ETF data (API unavailable)")
    return {
        'latest_flow': -186.5,
        'avg_7d': -50,
        'total_holdings': 1_375_000,
        'flows_7d': [],
        'is_fallback': True
    }

def interpret_etf_flows(etf_data):
    """Interpret ETF flow signals"""

    if not etf_data:
        return None

    latest_flow = etf_data['latest_flow']
    avg_7d = etf_data['avg_7d']
    total_holdings = etf_data['total_holdings']

    # Calculate % of circulating supply (19.8M BTC)
    circulating_supply = 19_800_000
    holdings_pct = (total_holdings / circulating_supply) * 100 if total_holdings else None

    # Flow interpretation
    if latest_flow > 5000:
        flow_signal = "🟢 MASSIVE INFLOW"
        flow_desc = f"+{latest_flow:,.0f} BTC (institutional FOMO)"
    elif latest_flow > 2000:
        flow_signal = "🟢 STRONG INFLOW"
        flow_desc = f"+{latest_flow:,.0f} BTC (healthy demand)"
    elif latest_flow > 0:
        flow_signal = "🟢 INFLOW"
        flow_desc = f"+{latest_flow:,.0f} BTC (positive)"
    elif latest_flow > -2000:
        flow_signal = "🔴 OUTFLOW"
        flow_desc = f"{latest_flow:,.0f} BTC (weak hands)"
    elif latest_flow > -5000:
        flow_signal = "🔴 STRONG OUTFLOW"
        flow_desc = f"{latest_flow:,.0f} BTC (distribution)"
    else:
        flow_signal = "🔴 MASSIVE OUTFLOW"
        flow_desc = f"{latest_flow:,.0f} BTC (capitulation)"

    # 7-day trend
    if avg_7d > 1000:
        trend_signal = "🟢 Sustained buying"
    elif avg_7d > 0:
        trend_signal = "🟢 Positive trend"
    elif avg_7d > -1000:
        trend_signal = "🔴 Negative trend"
    else:
        trend_signal = "🔴 Sustained selling"

    # Holdings interpretation
    if holdings_pct:
        if holdings_pct > 12:
            holdings_signal = "🔥 HIGH SCARCITY"
            holdings_desc = f"ETFs hold {holdings_pct:.1f}%% of supply (thesis playing out)"
        elif holdings_pct > 10:
            holdings_signal = "⚠️ RISING SCARCITY"
            holdings_desc = f"ETFs hold {holdings_pct:.1f}%% of supply (watch closely)"
        else:
            holdings_signal = "📊 BUILDING"
            holdings_desc = f"ETFs hold {holdings_pct:.1f}%% of supply"
    else:
        holdings_signal = "📊 DATA UNAVAILABLE"
        holdings_desc = "Total holdings not available"

    return {
        'flow_signal': flow_signal,
        'flow_desc': flow_desc,
        'trend_signal': trend_signal,
        'avg_7d': avg_7d,
        'holdings_signal': holdings_signal,
        'holdings_desc': holdings_desc,
        'holdings_pct': holdings_pct
    }

def get_fed_funds_rate():
    """Get current Fed Funds Rate from FRED"""
    print("Fetching Fed Funds Rate...")

    api_key = "7fd7e4bd0c4be5b5d382faaa64e8d9ee"

    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        'series_id': 'FEDFUNDS',  # Effective Federal Funds Rate
        'api_key': api_key,
        'file_type': 'json',
        'sort_order': 'desc',
        'limit': 3  # Get last 3 months to calculate change
    }

    try:
        time.sleep(2)
        response = requests.get(url, params=params, timeout=15)

        if response.status_code == 200:
            data = response.json()

            if 'observations' in data and len(data['observations']) > 0:
                # Get current and previous
                current_obs = None
                prev_obs = None

                for obs in data['observations']:
                    if obs.get('value', '.') != '.':
                        if not current_obs:
                            current_obs = obs
                        elif not prev_obs:
                            prev_obs = obs
                            break

                if current_obs:
                    current_rate = float(current_obs['value'])
                    current_date = current_obs['date']

                    # Calculate change
                    change = 0
                    if prev_obs:
                        prev_rate = float(prev_obs['value'])
                        change = current_rate - prev_rate

                    print(f"  ✅ Fed Funds Rate: {current_rate}%")

                    return {
                        'rate': round(current_rate, 2),
                        'change': round(change, 2),
                        'date': current_date
                    }

        return None

    except Exception as e:
        print(f"  ❌ Fed Funds error: {e}")
        return None

def get_fed_balance_sheet():
    """Get Fed Balance Sheet total assets"""
    print("Fetching Fed Balance Sheet...")

    api_key = "7fd7e4bd0c4be5b5d382faaa64e8d9ee"

    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        'series_id': 'WALCL',  # Assets: Total Assets: Total Assets (Less Eliminations from Consolidation): Wednesday Level
        'api_key': api_key,
        'file_type': 'json',
        'sort_order': 'desc',
        'limit': 10
    }

    try:
        time.sleep(2)
        response = requests.get(url, params=params, timeout=15)

        if response.status_code == 200:
            data = response.json()

            if 'observations' in data and len(data['observations']) > 0:
                # Find current and ~1 month ago (4 weeks back)
                current = None
                month_ago = None

                for i, obs in enumerate(data['observations']):
                    if obs.get('value', '.') != '.':
                        if not current:
                            current = obs
                        elif i >= 4 and not month_ago:  # ~4 weeks back
                            month_ago = obs
                            break

                if current:
                    current_balance = float(current['value'])  # In millions
                    current_date = current['date']

                    # Calculate 1-month change
                    change_1m = 0
                    if month_ago:
                        month_ago_balance = float(month_ago['value'])
                        change_1m = current_balance - month_ago_balance

                    print(f"  ✅ Fed Balance Sheet: ${current_balance/1000:.1f}T")

                    return {
                        'balance': round(current_balance / 1_000_000, 2),  # Convert millions to trillions
                        'change_1m': round(change_1m / 1_000_000, 2),
                        'date': current_date
                    }

        return None

    except Exception as e:
        print(f"  ❌ Fed Balance Sheet error: {e}")
        return None

def get_reverse_repo():
    """Get Reverse Repo balance"""
    print("Fetching Reverse Repo...")

    api_key = "7fd7e4bd0c4be5b5d382faaa64e8d9ee"

    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        'series_id': 'RRPONTSYD',
        'api_key': api_key,
        'file_type': 'json',
        'sort_order': 'desc',
        'limit': 100
    }

    try:
        time.sleep(2)
        response = requests.get(url, params=params, timeout=15)

        if response.status_code == 200:
            data = response.json()

            if 'observations' in data and len(data['observations']) > 0:
                valid_obs = []
                for obs in data['observations']:
                    if obs.get('value', '.') != '.':
                        valid_obs.append(obs)

                if len(valid_obs) >= 2:
                    current = valid_obs[0]
                    current_rrp = float(current['value'])  # Already in billions!
                    current_date = current['date']

                    month_ago = valid_obs[min(20, len(valid_obs)-1)]
                    month_ago_rrp = float(month_ago['value'])

                    change_1m = current_rrp - month_ago_rrp

                    print(f"  ✅ Reverse Repo: ${current_rrp:.0f}B")

                    return {
                        'balance': round(current_rrp, 0),  # NO division!
                        'change_1m': round(change_1m, 0),
                        'date': current_date
                    }

        return None

    except Exception as e:
        print(f"  ❌ Reverse Repo error: {e}")
        return None

def get_treasury_general_account():
    """Get Treasury General Account balance"""
    print("Fetching Treasury General Account...")

    api_key = "7fd7e4bd0c4be5b5d382faaa64e8d9ee"

    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        'series_id': 'WTREGEN',
        'api_key': api_key,
        'file_type': 'json',
        'sort_order': 'desc',
        'limit': 50
    }

    try:
        time.sleep(2)
        response = requests.get(url, params=params, timeout=15)

        if response.status_code == 200:
            data = response.json()

            if 'observations' in data and len(data['observations']) > 0:
                valid_obs = []
                for obs in data['observations']:
                    if obs.get('value', '.') != '.':
                        valid_obs.append(obs)

                if len(valid_obs) >= 2:
                    current = valid_obs[0]
                    current_tga = float(current['value']) / 1000
                    current_date = current['date']

                    month_ago = valid_obs[min(4, len(valid_obs)-1)]
                    month_ago_tga = float(month_ago['value']) / 1000

                    change_1m = current_tga - month_ago_tga

                    print(f"  ✅ TGA: ${current_tga:.0f}B")

                    return {
                        'balance': round(current_tga, 0),  # NO division!
                        'change_1m': round(change_1m, 0),
                        'date': current_date
                    }

        return None

    except Exception as e:
        print(f"  ❌ TGA error: {e}")
        return None

def assess_liquidity_regime(fed_funds, balance_sheet, rrp, tga):
    """
    Assess overall liquidity regime based on Fed indicators
    Returns: (regime, emoji, interpretation)
    """

    score = 0
    signals = []

    # Fed Funds Rate - Cutting = good
    if fed_funds and fed_funds.get('change'):
        change = fed_funds['change']
        if change < -0.2:
            score += 2
            signals.append("🟢 Cutting aggressively")
        elif change < 0:
            score += 1
            signals.append("🟢 Cutting cycle")
        elif change > 0.2:
            score -= 2
            signals.append("🔴 Hiking cycle")
        elif change > 0:
            score -= 1
            signals.append("🔴 Tightening")
        else:
            signals.append("🟡 Paused")

    # Balance Sheet - Expanding = good
    if balance_sheet and balance_sheet.get('change_1m'):
        change = balance_sheet['change_1m']
        if change > 0.1:  # +$100B+
            score += 2
            signals.append("🟢 QE active")
        elif change > 0:
            score += 1
            signals.append("🟢 Expanding slowly")
        elif change < -0.1:  # -$100B+
            score -= 2
            signals.append("🔴 QT active")
        elif change < 0:
            score -= 1
            signals.append("🔴 Contracting")

    # Reverse Repo - Draining = good (liquidity entering markets)
    if rrp and rrp.get('change_1m'):
        change = rrp['change_1m']
        if change < -100:  # -$100B+
            score += 2
            signals.append("🟢 RRP draining fast")
        elif change < -50:
            score += 1
            signals.append("🟢 RRP draining")
        elif change > 100:
            score -= 1
            signals.append("🔴 RRP building")

    # TGA - Falling = good (gov't injecting money)
    if tga and tga.get('change_1m'):
        change = tga['change_1m']
        if change < -100:  # -$100B+
            score += 2
            signals.append("🟢 TGA draining (injection)")
        elif change < -50:
            score += 1
            signals.append("🟢 TGA falling")
        elif change > 100:
            score -= 1
            signals.append("🔴 TGA building (drain)")

    # Determine regime
    if score >= 4:
        regime = "EASING STRONGLY"
        emoji = "🟢"
        interpretation = "Major liquidity injection - strong tailwind for BTC/Gold"
    elif score >= 2:
        regime = "EASING"
        emoji = "🟢"
        interpretation = "Net liquidity improving - favorable for risk assets"
    elif score >= -1:
        regime = "NEUTRAL"
        emoji = "🟡"
        interpretation = "Mixed liquidity signals - price action matters more"
    elif score >= -3:
        regime = "TIGHTENING"
        emoji = "🟠"
        interpretation = "Net liquidity draining - headwind for crypto"
    else:
        regime = "TIGHTENING STRONGLY"
        emoji = "🔴"
        interpretation = "Aggressive liquidity drain - strong headwind"

    return regime, emoji, interpretation, signals

def get_dollar_regime(eur_usd, real_yields):
    """
    Assess dollar strength regime and crypto implications
    Returns: (regime, signal, interpretation)
    """

    if not eur_usd and not real_yields:
        return 'UNKNOWN', '❓', 'Insufficient data'

    # Score system (lower = stronger dollar = worse for crypto)
    score = 0
    signals = []

    # EUR/USD component (higher EUR/USD = weaker dollar = good for crypto)
    if eur_usd:
        if eur_usd > 1.10:
            score += 2
            signals.append(f"EUR/USD {eur_usd:.4f} (weak $)")
        elif eur_usd > 1.08:
            score += 1
            signals.append(f"EUR/USD {eur_usd:.4f} (neutral)")
        elif eur_usd > 1.05:
            score += 0
            signals.append(f"EUR/USD {eur_usd:.4f} (firm $)")
        else:  # < 1.05
            score -= 1
            signals.append(f"EUR/USD {eur_usd:.4f} (strong $)")

    # Real Yields component (lower = better for crypto)
    if real_yields:
        if real_yields < 1.5:
            score += 2
            signals.append(f"Real yields {real_yields}% (low)")
        elif real_yields < 2.0:
            score += 1
            signals.append(f"Real yields {real_yields}% (moderate)")
        elif real_yields < 2.5:
            score += 0
            signals.append(f"Real yields {real_yields}% (elevated)")
        else:  # > 2.5
            score -= 1
            signals.append(f"Real yields {real_yields}% (high)")

    # Determine regime
    if score >= 3:
        regime = 'WEAK DOLLAR'
        emoji = '🟢'
        interpretation = 'Strong tailwind for BTC/Gold - debasement trade active'
    elif score >= 1:
        regime = 'NEUTRAL'
        emoji = '🟡'
        interpretation = 'Mixed signals - fundamentals matter more than dollar'
    elif score >= -1:
        regime = 'FIRM DOLLAR'
        emoji = '🟠'
        interpretation = 'Headwind for crypto - dollar strength creating resistance'
    else:
        regime = 'STRONG DOLLAR'
        emoji = '🔴'
        interpretation = 'Major headwind - risk-off into USD, pressure on alternatives'

    return regime, emoji, interpretation, signals

def detect_scenario(ratios):
    """
    Detect which infrastructure scenario is playing out:
    - Scenario A: Winner takes all (ETH + SOL strong, others weak)
    - Scenario B: Rising together (all L1s strong)
    - Scenario C: All weak (all L1s weak)
    """

    # Initialize defaults
    scenario = "UNKNOWN"
    description = "Unable to determine scenario"
    recommendation = "Wait for more data"

    if not ratios:
        return scenario, description, recommendation

    # Count winners and losers
    strong = []  # >5% gain
    weak = []    # <-5% loss
    neutral = []

    for symbol, data in ratios.items():
        trend = data['trend_7d']
        if trend > 5.0:
            strong.append(symbol)
        elif trend < -5.0:
            weak.append(symbol)
        else:
            neutral.append(symbol)

    # Scenario detection
    eth_strong = 'ETH' in strong or ratios.get('ETH', {}).get('trend_7d', 0) > 2
    sol_strong = 'SOL' in strong or ratios.get('SOL', {}).get('trend_7d', 0) > 2
    old_guard_weak = ('ADA' in weak or ratios.get('ADA', {}).get('trend_7d', 0) < -5) and \
                     ('DOT' in weak or ratios.get('DOT', {}).get('trend_7d', 0) < -5)

    if eth_strong and sol_strong and old_guard_weak:
        scenario = "A"
        description = "WINNER TAKES ALL: ETH + SOL dominating, old guard dying"
        recommendation = "Exit ADA/DOT, focus on ETH/SOL"
    elif len(strong) >= 3:
        scenario = "B"
        description = "RISING TOGETHER: Broad L1 strength"
        recommendation = "Diversify across quality L1s"
    elif len(weak) >= 3:
        scenario = "C"
        description = "ALL WEAK: Broad L1 weakness"
        recommendation = "Rotate to BTC/Gold, reduce alt exposure"
    else:
        scenario = "MIXED"
        description = "MIXED SIGNALS: No clear trend"
        recommendation = "Wait for clearer picture"

    return scenario, description, recommendation

def get_funding_rate():
    """Get BTC perpetual futures funding rate from Bybit"""
    print("Fetching funding rate...")
    
    try:
        url = "https://api.bybit.com/v5/market/tickers"
        params = {
            'category': 'linear',
            'symbol': 'BTCUSDT'
        }
        
        time.sleep(2)
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('retCode') == 0 and 'result' in data:
                ticker = data['result']['list'][0]
                
                # Funding rate (8-hour rate)
                funding_rate = float(ticker.get('fundingRate', 0))
                funding_pct = funding_rate * 100
                
                # Annualized
                annualized_pct = funding_pct * 3 * 365
                
                # Determine signal
                if funding_pct >= 0.10:
                    signal = "🔴 EXTREME BULLISH"
                    explanation = "Danger zone - overleveraged longs"
                elif funding_pct >= 0.08:
                    signal = "🟠 VERY HIGH"
                    explanation = "High long leverage - correction risk"
                elif funding_pct >= 0.05:
                    signal = "🟡 HIGH"
                    explanation = "Moderate long bias"
                elif funding_pct >= 0.01:
                    signal = "🟢 HEALTHY BULLISH"
                    explanation = "Normal bullish funding"
                elif funding_pct >= -0.01:
                    signal = "⚪ NEUTRAL"
                    explanation = "Balanced market"
                elif funding_pct >= -0.05:
                    signal = "🟢 HEALTHY BEARISH"
                    explanation = "Normal bearish funding"
                elif funding_pct >= -0.08:
                    signal = "🟡 NEGATIVE"
                    explanation = "Moderate short bias"
                elif funding_pct >= -0.10:
                    signal = "🟠 VERY NEGATIVE"
                    explanation = "High short leverage - squeeze risk"
                else:
                    signal = "🔴 EXTREME BEARISH"
                    explanation = "Danger zone - overleveraged shorts"
                
                print(f"  ✅ Funding rate: {funding_pct:.4f}% per 8hrs")
                
                return {
                    'rate_pct': funding_pct,
                    'annualized_pct': annualized_pct,
                    'signal': signal,
                    'explanation': explanation
                }
        
        print(f"  ❌ Bybit funding API error: {response.status_code}")
        return None
            
    except Exception as e:
        print(f"  ❌ Error fetching funding rate: {e}")
        return None

def get_open_interest():
    """Get BTC perpetual futures open interest from Bybit"""
    print("Fetching open interest...")
    
    try:
        url = "https://api.bybit.com/v5/market/open-interest"
        params = {
            'category': 'linear',
            'symbol': 'BTCUSDT',
            'intervalTime': '5min'
        }
        
        time.sleep(2)
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('retCode') == 0 and 'result' in data:
                oi_data = data['result']['list'][0]
                
                # OI in USD
                oi_usd = float(oi_data.get('openInterest', 0))
                oi_billions = oi_usd / 1_000_000_000
                
                # Determine signal
                if oi_billions >= 40:
                    signal = "🔴 EXTREME"
                    explanation = "Massive leverage - high volatility risk"
                elif oi_billions >= 35:
                    signal = "🟠 VERY HIGH"
                    explanation = "Elevated leverage - watch for cascade"
                elif oi_billions >= 30:
                    signal = "🟡 HIGH"
                    explanation = "Above average positioning"
                elif oi_billions >= 20:
                    signal = "🟢 MODERATE"
                    explanation = "Healthy leverage levels"
                else:
                    signal = "⚪ LOW"
                    explanation = "Low leverage - stable but boring"
                
                print(f"  ✅ Open interest: ${oi_billions:.2f}B")
                
                return {
                    'oi_billions': oi_billions,
                    'signal': signal,
                    'explanation': explanation
                }
        
        print(f"  ❌ Bybit OI API error: {response.status_code}")
        return None
            
    except Exception as e:
        print(f"  ❌ Error fetching open interest: {e}")
        return None

def interpret_leverage_conditions(funding_data, oi_data):
    """
    Combine funding rate + OI to interpret market leverage conditions
    Based on Day 12 framework
    """
    if not funding_data or not oi_data:
        return None
    
    funding_pct = funding_data['rate_pct']
    oi_billions = oi_data['oi_billions']
    
    # Critical thresholds from Day 12
    extreme_positive_funding = funding_pct >= 0.08
    extreme_negative_funding = funding_pct <= -0.08
    very_extreme_funding = abs(funding_pct) >= 0.10
    high_oi = oi_billions >= 30
    extreme_oi = oi_billions >= 35
    
    # Condition 1: Extreme positive funding + high OI = TOP RISK
    if extreme_positive_funding and high_oi:
        condition = "🔴 DANGER ZONE - TOP RISK"
        action = "DO NOT BUY - Liquidation cascade imminent"
        trade_signal = "Wait for flush to €85k-€90k BTC"
        
    # Condition 2: Extreme negative funding + high OI = BOTTOM OPPORTUNITY
    elif extreme_negative_funding and high_oi:
        condition = "🟢 OPPORTUNITY - BOTTOM SIGNAL"
        action = "ACCUMULATE - Short squeeze likely"
        trade_signal = "Deploy Finst ladder, watch for bounce"
        
    # Condition 3: Very extreme funding alone
    elif very_extreme_funding:
        if funding_pct > 0:
            condition = "🟠 EXTREME BULLISH FUNDING"
            action = "CAUTION - High correction risk"
            trade_signal = "Reduce exposure, wait for reset"
        else:
            condition = "🟢 EXTREME BEARISH FUNDING"
            action = "CONTRARIAN OPPORTUNITY"
            trade_signal = "Shorts likely to be squeezed"
            
    # Condition 4: High OI but normal funding
    elif high_oi and abs(funding_pct) < 0.05:
        condition = "🟡 HIGH LEVERAGE - NEUTRAL BIAS"
        action = "WATCH CLOSELY - Powder keg"
        trade_signal = "Wait for funding to spike either direction"
        
    # Condition 5: Normal conditions
    else:
        condition = "🟢 HEALTHY MARKET"
        action = "NORMAL CONDITIONS"
        trade_signal = "Trade as usual"
    
    return {
        'condition': condition,
        'action': action,
        'trade_signal': trade_signal
    }

def generate_infrastructure_report():
    """Generate and send infrastructure monitor report"""

    current_time = get_montevideo_time()

    print(f"=" * 70)
    print(f"INFRASTRUCTURE MONITOR")
    print(f"Started at {current_time.strftime('%H:%M:%S')}")
    print(f"=" * 70)

    # Get L1 ratios
    ratios = get_l1_ratios()

    # Get ETH gas fees
    gas_fees = get_eth_gas_fees()

    # Get ETH staking ratio
    staking_data = get_eth_staking_ratio()

    # Get DEX volume by chain
    dex_volume = get_dex_volume_by_chain()

    # Get TVL by chain
    tvl_data = get_tvl_by_chain()

    # Get macro indicators
    dxy_data = get_dxy()
    real_yields = get_real_yields()

    # Get DXY (placeholder for now)
    dxy = None  # We'll add this later with proper API

    # Build message
    message = f"🏗️ <b>INFRASTRUCTURE MONITOR</b>\n"
    message += f"🕐 {current_time.strftime('%Y-%m-%d %H:%M %Z')}\n"
    message += f"━━━━━━━━━━━━━━━━━━━━\n\n"

    # L1 Race Section
    if ratios:
        message += f"📊 <b>LAYER 1 RACE (vs BTC):</b>\n\n"

        # Sort by trend (strongest first)
        sorted_l1s = sorted(ratios.items(), key=lambda x: x[1]['trend_7d'], reverse=True)

        for symbol, data in sorted_l1s:
            ratio = data['ratio']
            trend = data['trend_7d']

            # Emoji based on trend
            if trend > 5:
                emoji = "🔥"
                status = "STRONG"
            elif trend > 2:
                emoji = "🟢"
                status = "Rising"
            elif trend > -2:
                emoji = "⚪"
                status = "Stable"
            elif trend > -5:
                emoji = "🟡"
                status = "Weak"
            else:
                emoji = "🔴"
                status = "DYING"

            # Specific thresholds for ETH
            if symbol == 'ETH':
                if ratio > 0.038:
                    threshold_note = " (🟢 Above 0.038 - Alt season signal)"
                elif ratio < 0.034:
                    threshold_note = " (🔴 Below 0.034 - BTC dominance)"
                else:
                    threshold_note = " (🟡 Neutral zone)"
            else:
                threshold_note = ""

            message += f"{emoji} <b>{symbol}/BTC:</b> {ratio:.6f} | 7d: {trend:+.1f}%% ({status}){threshold_note}\n"

        message += f"\n"

        # Scenario detection
        scenario, description, recommendation = detect_scenario(ratios)

        if scenario:
            if scenario == "A":
                scenario_emoji = "⚠️"
            elif scenario == "B":
                scenario_emoji = "🚀"
            elif scenario == "C":
                scenario_emoji = "❌"
            else:
                scenario_emoji = "🤔"

            message += f"🎯 <b>SCENARIO DETECTED: {scenario_emoji} {scenario}</b>\n"
            message += f"   {description}\n"
            message += f"   💡 <b>Action:</b> {recommendation}\n\n"
    else:
        message += f"⚠️ Error fetching L1 data\n\n"

    # Network Activity
    message += f"━━━━━━━━━━━━━━━━━━━━\n"
    message += f"⛽ <b>NETWORK ACTIVITY:</b>\n\n"

    if gas_fees:
        safe = gas_fees['safe']
        standard = gas_fees['standard']
        fast = gas_fees['fast']

        # Interpret gas fees (handle sub-1 gwei values)
        if standard < 1:
            gas_status = "🟢 ULTRA LOW - Post-Dencun equilibrium"
        elif standard < 10:
            gas_status = "🟢 VERY LOW - L2s effective"
        elif standard < 20:
            gas_status = "🟢 LOW - Good conditions"
        elif standard < 50:
            gas_status = "🟡 MODERATE - Normal activity"
        elif standard < 100:
            gas_status = "🟠 HIGH - Network congested"
        else:
            gas_status = "🔴 EXTREME - Avoid mainnet"

        message += f"<b>ETH Gas Fees:</b>\n"
        message += f"  Safe: {safe} gwei | Standard: {standard} gwei | Fast: {fast} gwei\n"
        message += f"  Status: {gas_status}\n\n"
    else:
        message += f"ETH Gas: Data unavailable\n\n"

    # DeFi Activity
    message += f"━━━━━━━━━━━━━━━━━━━━\n"
    message += f"💰 <b>DEFI ACTIVITY (24h):</b>\n\n"

    if dex_volume:
        message += f"<b>DEX Volume by Chain:</b>\n"

        # Sort by volume (highest first)
        sorted_chains = sorted(dex_volume.items(), key=lambda x: x[1]['volume'], reverse=True)

        for symbol, data in sorted_chains:
            volume = data['volume']
            percentage = data['percentage']

            # Format volume
            if volume >= 1e9:
                volume_str = f"${volume/1e9:.1f}B"
            elif volume >= 1e6:
                volume_str = f"${volume/1e6:.0f}M"
            else:
                volume_str = f"${volume/1e3:.0f}K"

            # Emoji based on market share
            if percentage > 50:
                emoji = "🔥"
            elif percentage > 20:
                emoji = "🟢"
            elif percentage > 5:
                emoji = "🟡"
            else:
                emoji = "🔴"

            message += f"  {emoji} {symbol}: {volume_str} ({percentage}%%)\n"

        message += f"\n"

    if tvl_data:
        message += f"<b>Total Value Locked (TVL):</b>\n"

        # Sort by TVL (highest first)
        sorted_tvl = sorted(tvl_data.items(), key=lambda x: x[1]['tvl'], reverse=True)

        for symbol, data in sorted_tvl:
            tvl = data['tvl']
            change = data['change_24h']

            # Format TVL
            if tvl >= 1e9:
                tvl_str = f"${tvl/1e9:.1f}B"
            elif tvl >= 1e6:
                tvl_str = f"${tvl/1e6:.0f}M"
            else:
                tvl_str = f"${tvl/1e3:.0f}K"

            # Emoji based on change
            if change > 5:
                change_emoji = "🚀"
            elif change > 2:
                change_emoji = "🟢"
            elif change > -2:
                change_emoji = "⚪"
            elif change > -5:
                change_emoji = "🟡"
            else:
                change_emoji = "🔴"

            message += f"  {change_emoji} {symbol}: {tvl_str} ({change:+.1f}%% 24h)\n"

        message += f"\n"

    if not dex_volume and not tvl_data:
        message += f"DeFi data unavailable\n\n"

    # ETH Staking
    if staking_data:
        ratio = staking_data['ratio']
        validators = staking_data['validators']
        staked_eth = staking_data['staked_eth']

        # Interpret staking ratio
        if ratio >= 33:
            staking_status = "🟢 Very Strong"
            staking_signal = "High confidence"
        elif ratio >= 28:
            staking_status = "🟢 Strong"
            staking_signal = "Healthy"
        elif ratio >= 25:
            staking_status = "🟡 Moderate"
            staking_signal = "Watch for changes"
        elif ratio >= 20:
            staking_status = "🟠 Weak"
            staking_signal = "Low confidence"
        else:
            staking_status = "🔴 Very Weak"
            staking_signal = "Concerning"

        message += f"<b>ETH Staking:</b>\n"
        message += f"  Ratio: {ratio}%% of supply locked | Status: {staking_status}\n"

        if validators:
            message += f"  Validators: {validators:,} | Staked: {staked_eth}M ETH\n"

        message += f"  Signal: {staking_signal}\n"
        message += f"  📊 Post-Fusaka (Dec 3): Watch for ratio increase\n\n"
    else:
        message += f"ETH Staking: Data unavailable\n\n"

    # ETF Flows Section
    message += f"━━━━━━━━━━━━━━━━━━━━\n"
    message += f"💼 <b>ETF FLOW TRACKER:</b>\n\n"

    etf_data = get_btc_etf_flows()

    if etf_data:
        interpretation = interpret_etf_flows(etf_data)

        if interpretation:
            message += f"<b>Latest Flow:</b> {interpretation['flow_signal']}\n"
            message += f"   {interpretation['flow_desc']}\n\n"

            message += f"<b>7-Day Trend:</b> {interpretation['trend_signal']}\n"
            message += f"   Avg: {interpretation['avg_7d']:+,.0f} BTC/day\n\n"

            message += f"<b>Total Holdings:</b> {interpretation['holdings_signal']}\n"
            message += f"   {interpretation['holdings_desc']}\n\n"

            # Thesis validation
            if interpretation['holdings_pct'] >= 12:
                message += f"✅ <b>THESIS VALIDATION:</b> 12%% supply threshold reached!\n"
                message += f"   Scarcity intensifying as predicted\n\n"
    else:
        message += f"⚠️ ETF flow data unavailable\n\n"

    # Macro context (existing section continues here)
    message += f"━━━━━━━━━━━━━━━━━━━━\n"
    message += f"🌍 <b>MACRO ENVIRONMENT:</b>\n\n"


    # Dollar Strength (EUR/USD proxy)
    if dxy_data:
        eur_usd = dxy_data['eur_usd']

        # EUR/USD interpretation (inverse of dollar strength)
        # Higher EUR/USD = weaker dollar = good for crypto
        # Lower EUR/USD = stronger dollar = bad for crypto

        if eur_usd < 1.05:
            dollar_status = "🔴 STRONG DOLLAR"
            dollar_signal = "Headwind for crypto, favor Gold"
        elif eur_usd < 1.08:
            dollar_status = "🟡 MODERATE"
            dollar_signal = "Neutral"
        elif eur_usd > 1.10:
            dollar_status = "🟢 WEAK DOLLAR"
            dollar_signal = "Tailwind for crypto"
        else:
            dollar_status = "🟢 BALANCED"
            dollar_signal = "Neutral-positive"

        message += f"<b>Dollar Strength (EUR/USD proxy):</b> €{eur_usd}\n"
        message += f"  Status: {dollar_status} | Signal: {dollar_signal}\n"
        message += f"  Note: EUR/USD below 1.05 = strong dollar | above 1.10 = weak dollar\n\n"

    # Real Yields
    if real_yields:
        yield_val = real_yields['value']

        if yield_val > 2.5:
            yield_status = "🔴 HIGH"
            yield_signal = "Pressure on BTC/Gold (opportunity cost high)"
        elif yield_val > 1.5:
            yield_status = "🟡 MODERATE"
            yield_signal = "Neutral for crypto"
        else:
            yield_status = "🟢 LOW"
            yield_signal = "Bullish for BTC/Gold (TINA)"

        message += f"<b>Real Yields (10Y TIPS):</b> {yield_val}%% | {yield_status}\n"
        message += f"  Signal: {yield_signal}\n\n"

    # References
    message += f"<b>Gold/BTC Ratio:</b> See divergence report\n"
    message += f"<b>BTC Dominance:</b> See divergence report\n\n"

    if not dxy_data and not real_yields:
        message += f"⚠️ Macro data unavailable\n\n"

    # Trading signals
    message += f"━━━━━━━━━━━━━━━━━━━━\n"
    message += f"📈 <b>TRADING SIGNALS:</b>\n\n"

    if ratios:
        eth_ratio = ratios.get('ETH', {}).get('ratio', 0)
        eth_trend = ratios.get('ETH', {}).get('trend_7d', 0)

        # €2k Divergence trading bucket
        message += f"<b>€2k Alt/BTC Divergence Bucket:</b>\n"
        if eth_ratio > 0.038:
            message += f"✅ ACTIVE - ETH/BTC above 0.038\n"
            message += f"   Trade alt divergences vs BTC\n"
        elif eth_ratio < 0.034:
            message += f"❌ AVOID - ETH/BTC below 0.034\n"
            message += f"   Exit alt positions, hold BTC\n"
        else:
            message += f"⚠️ NEUTRAL - ETH/BTC in 0.034-0.038 range\n"
            message += f"   Selective trades only\n"

        message += f"\n"

        # €3k BTC/ETH/Gold rotation bucket
        message += f"<b>€3k BTC/ETH/Gold Rotation:</b>\n"
        if eth_trend > 5:
            message += f"🟢 FAVOR ETH - Strong 7d momentum ({eth_trend:+.1f}%%)\n"
        elif eth_trend < -5:
            message += f"🔴 FAVOR BTC - Weak ETH momentum ({eth_trend:+.1f}%%)\n"
        else:
            message += f"🟡 BALANCED - Monitor for breakout\n"

        message += f"\n"

        # €5k Long-term hold decision
        message += f"<b>€5k Long-Term Allocation:</b>\n"
        if eth_ratio > 0.040 and eth_trend > 3:
            message += f"✅ ADD ETH - Strong technicals\n"
            message += f"   Consider 50%% BTC / 30%% ETH / 20%% Gold\n"
        elif eth_ratio < 0.035:
            message += f"⚠️ BTC/GOLD ONLY - ETH underperforming\n"
            message += f"   Maintain 60%% BTC / 40%% Gold\n"
        else:
            message += f"🟡 WATCH - Not conclusive yet\n"
            message += f"   Wait for Fusaka results (Dec 3)\n"

    message += f"\n━━━━━━━━━━━━━━━━━━━━"

    # Send to Telegram
    send_telegram_message(message)
    print(f"✅ Infrastructure report sent at {current_time.strftime('%H:%M:%S')}")

if __name__ == "__main__":
    generate_infrastructure_report()
