#!/usr/bin/env python3
"""
TVL INFRASTRUCTURE MONITOR
Complete infrastructure monitoring: L1 ratios, gas fees, staking, TVL, DEX volume
Validates multi-chain thesis

Run daily at 10 AM (after morning report)

UPDATED: November 11, 2025 - Complete infrastructure report
"""

import requests
import time
from datetime import datetime, timedelta
import json
import os
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# ========== CONFIGURATION ==========

# Chains to track with regional classification
CHAINS_TO_TRACK = {
    # Western DeFi
    'Ethereum': {'symbol': 'ETH', 'region': 'Western DeFi', 'coingecko_id': 'ethereum'},
    'Arbitrum': {'symbol': 'ARB', 'region': 'Western DeFi', 'coingecko_id': 'arbitrum-one'},
    'Base': {'symbol': 'BASE', 'region': 'Western DeFi', 'coingecko_id': 'base'},
    'Optimism': {'symbol': 'OP', 'region': 'Western DeFi', 'coingecko_id': 'optimism'},
    'Polygon': {'symbol': 'POL', 'region': 'Western DeFi', 'coingecko_id': 'polygon-pos'},

    # Asian Speed/Cost
    'Solana': {'symbol': 'SOL', 'region': 'Asian Speed', 'coingecko_id': 'solana'},
    'BSC': {'symbol': 'BNB', 'region': 'Asian Speed', 'coingecko_id': 'binance-smart-chain'},
    'Avalanche': {'symbol': 'AVAX', 'region': 'Multi-Region', 'coingecko_id': 'avalanche'},

    # Emerging/Other
    'Cardano': {'symbol': 'ADA', 'region': 'Emerging', 'coingecko_id': 'cardano'},
    'Polkadot': {'symbol': 'DOT', 'region': 'Emerging', 'coingecko_id': 'polkadot'},
    'Sui': {'symbol': 'SUI', 'region': 'Asian Speed', 'coingecko_id': 'sui'},
}

# L1s to track vs BTC
L1_VS_BTC = ['ethereum', 'solana', 'avalanche']

# Historical data storage file
HISTORY_FILE = 'tvl_history.json'

# ========== HELPER FUNCTIONS ==========

def send_telegram_message(message):
    """Send message to Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("✅ TVL report sent to Telegram")
            return True
        else:
            print(f"❌ Telegram error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        return False


def get_l1_ratios():
    """Get L1/BTC price ratios with 7d trend using CryptoCompare"""

    ratios = {}

    # Coins to track vs BTC
    coins = ['ETH', 'SOL', 'AVAX', 'BNB', 'ADA', 'DOT', 'MATIC', 'OP', 'ARB', 'SUI']

    for symbol in coins:
        try:
            url = "https://min-api.cryptocompare.com/data/v2/histohour"
            params = {'fsym': symbol, 'tsym': 'BTC', 'limit': 168}  # 7 days of hourly data

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if 'Data' in data and 'Data' in data['Data']:
                    candles = data['Data']['Data']

                    if len(candles) > 0:
                        current_ratio = candles[-1]['close']
                        ratio_7d_ago = candles[-168]['close'] if len(candles) >= 168 else candles[0]['close']

                        # Calculate 7d trend
                        trend_7d = ((current_ratio - ratio_7d_ago) / ratio_7d_ago) * 100 if ratio_7d_ago else 0

                        ratios[symbol] = {
                            'ratio': current_ratio,
                            'trend_7d': trend_7d
                        }

                        print(f"✅ {symbol}/BTC: {current_ratio:.6f} ({trend_7d:+.1f}% 7d)")

            time.sleep(1.5)  # Rate limit between calls

        except Exception as e:
            print(f"Error fetching {symbol}/BTC: {e}")

    return ratios if ratios else None


def get_eth_gas_fees():
    """Get Ethereum gas fees"""
    try:
        # Try Etherscan
        url = "https://api.etherscan.io/api"
        params = {
            'module': 'gastracker',
            'action': 'gasoracle'
        }

        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == '1':
                result = data.get('result', {})
                standard_gwei = float(result.get('ProposeGasPrice', 0))

                if standard_gwei > 0:
                    return {'standard': standard_gwei}

        # Fallback: estimate
        print("Using ETH gas estimate")
        return {'standard': 15.0}  # Typical current gas

    except Exception as e:
        print(f"Error fetching ETH gas: {e}")
        return {'standard': 15.0}


def get_solana_fees():
    """Estimate Solana transaction fees"""
    try:
        # Get current SOL price
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': 'solana',
            'vs_currencies': 'usd'
        }

        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            sol_price = data.get('solana', {}).get('usd', 0)

            # Typical Solana fee: 0.000005 SOL
            fee_sol = 0.000005
            fee_usd = fee_sol * sol_price if sol_price else 0.001

            return {
                'fee_sol': fee_sol,
                'fee_usd': fee_usd
            }

        return {'fee_sol': 0.000005, 'fee_usd': 0.001}
    except Exception as e:
        print(f"Error estimating SOL fees: {e}")
        return {'fee_sol': 0.000005, 'fee_usd': 0.001}


def get_bnb_gas_fees():
    """Estimate BNB Chain gas fees"""
    try:
        # Get current BNB price
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': 'binancecoin',
            'vs_currencies': 'usd'
        }

        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            bnb_price = data.get('binancecoin', {}).get('usd', 0)

            # Typical BSC fee: 5 gwei with 21000 gas = 0.000105 BNB
            fee_bnb = 0.000105
            fee_usd = fee_bnb * bnb_price if bnb_price else 0.05

            return {
                'gwei': 5,
                'fee_bnb': fee_bnb,
                'fee_usd': fee_usd
            }

        return {'gwei': 5, 'fee_bnb': 0.000105, 'fee_usd': 0.05}
    except Exception as e:
        print(f"Error estimating BNB fees: {e}")
        return {'gwei': 5, 'fee_bnb': 0.000105, 'fee_usd': 0.05}


def get_staking_data():
    """Get staking ratios for major chains"""
    staking_info = {}

    # ETH staking
    try:
        print("Fetching ETH staking...")
        url = "https://beaconcha.in/api/v1/epoch/latest"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                validator_count = data['data'].get('validatorscount', 0)

                if validator_count > 0:
                    total_staked = validator_count * 32
                    total_supply = 120_000_000
                    ratio = (total_staked / total_supply) * 100
                    staking_info['ETH'] = {'ratio': round(ratio, 1)}
                    print(f"  ✅ ETH staking: {ratio:.1f}%")
                else:
                    raise Exception("No validator count")
        else:
            raise Exception(f"API returned {response.status_code}")

    except Exception as e:
        print(f"  ⚠️ ETH staking API failed: {e}")
        staking_info['ETH'] = {'ratio': 28.5, 'note': 'Estimate'}

    # SOL staking - use Solana RPC
    try:
        print("Fetching SOL staking...")
        url = "https://api.mainnet-beta.solana.com"

        # Get total supply
        payload_supply = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSupply"
        }

        response = requests.post(url, json=payload_supply, timeout=10)

        if response.status_code == 200:
            data = response.json()
            total_supply = data.get('result', {}).get('value', {}).get('total', 0) / 1e9  # Convert lamports to SOL

            time.sleep(1)

            # Get vote accounts to calculate staked amount
            payload_votes = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getVoteAccounts"
            }

            response = requests.post(url, json=payload_votes, timeout=10)

            if response.status_code == 200:
                data = response.json()
                vote_accounts = data.get('result', {})

                # Sum staked SOL from all validators
                total_staked = 0
                for account in vote_accounts.get('current', []):
                    total_staked += account.get('activatedStake', 0) / 1e9
                for account in vote_accounts.get('delinquent', []):
                    total_staked += account.get('activatedStake', 0) / 1e9

                if total_supply > 0:
                    ratio = (total_staked / total_supply) * 100
                    staking_info['SOL'] = {'ratio': round(ratio, 1)}
                    print(f"  ✅ SOL staking: {ratio:.1f}%")
                else:
                    raise Exception("No supply data")
        else:
            raise Exception(f"API returned {response.status_code}")

    except Exception as e:
        print(f"  ⚠️ SOL staking API failed: {e}")
        staking_info['SOL'] = {'ratio': 67, 'note': 'Estimate'}

    # BNB staking - use BSCScan API
    try:
        print("Fetching BNB staking...")
        # Get BNB total supply
        url_supply = "https://api.bscscan.com/api"
        params_supply = {
            'module': 'stats',
            'action': 'bnbsupply'
        }

        response = requests.get(url_supply, params=params_supply, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('status') == '1':
                total_supply = float(data.get('result', 0)) / 1e18  # Convert from wei

                # BNB staking is ~18% typically, but we can estimate from validators
                # For now, use BSC's known staking ratio since there's no direct API
                # BSC has 21 validators with delegated staking
                estimated_ratio = 18  # Typical range 15-20%

                staking_info['BNB'] = {'ratio': estimated_ratio, 'note': 'Network estimate'}
                print(f"  ✅ BNB staking: {estimated_ratio}% (estimated)")
            else:
                raise Exception("API error")
        else:
            raise Exception(f"API returned {response.status_code}")

    except Exception as e:
        print(f"  ⚠️ BNB staking API failed: {e}")
        staking_info['BNB'] = {'ratio': 18, 'note': 'Estimate'}

    return staking_info


def get_tvl_from_defillama(chain_name):
    """Get current TVL for a chain from DeFiLlama API"""
    url = f"https://api.llama.fi/v2/chains"

    try:
        response = requests.get(url, timeout=15)

        if response.status_code == 200:
            data = response.json()

            for chain in data:
                if chain.get('name', '').lower() == chain_name.lower():
                    tvl = chain.get('tvl')
                    return float(tvl) if tvl else None

        return None

    except Exception as e:
        print(f"Error fetching TVL for {chain_name}: {e}")
        return None


def get_market_cap(coingecko_id):
    """Get market cap from CoinGecko"""
    url = f"https://api.coingecko.com/api/v3/simple/price"

    params = {
        'ids': coingecko_id,
        'vs_currencies': 'usd',
        'include_market_cap': 'true'
    }

    try:
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            market_cap = data.get(coingecko_id, {}).get('usd_market_cap')
            return float(market_cap) if market_cap else None

        return None

    except Exception as e:
        print(f"Error fetching market cap for {coingecko_id}: {e}")
        return None


def load_history():
    """Load historical TVL data from file"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading history: {e}")
            return {}
    return {}


def save_history(history):
    """Save historical TVL data to file"""
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
        print(f"✅ History saved to {HISTORY_FILE}")
    except Exception as e:
        print(f"Error saving history: {e}")


def calculate_tvl_change(current_tvl, historical_tvl):
    """Calculate percentage change in TVL"""
    if not historical_tvl or historical_tvl == 0:
        return None

    return ((current_tvl - historical_tvl) / historical_tvl) * 100


def get_signal_emoji(change):
    """Get emoji based on TVL change"""
    if change is None:
        return "⚪"
    elif change > 15:
        return "🔥"
    elif change > 5:
        return "🟢"
    elif change > -5:
        return "🟡"
    elif change > -15:
        return "🟠"
    else:
        return "🔴"


# ========== MAIN REPORT GENERATION ==========

def generate_tvl_report():
    """Generate and send TVL infrastructure monitoring report"""

    print("=" * 70)
    print("TVL INFRASTRUCTURE MONITOR - Generating Report")
    print("=" * 70)

    # Load historical data
    history = load_history()

    # Get current date
    today = datetime.now().strftime('%Y-%m-%d')

    # Initialize today's data
    if today not in history:
        history[today] = {}

    # Collect current TVL data
    chain_data = []

    for chain_name, chain_info in CHAINS_TO_TRACK.items():
        print(f"Fetching data for {chain_name}...")

        # Get current TVL
        current_tvl = get_tvl_from_defillama(chain_name)

        if current_tvl:
            # Store in history
            history[today][chain_name] = {
                'tvl': current_tvl,
                'timestamp': datetime.now().isoformat()
            }

            # Get market cap
            time.sleep(1.5)  # Rate limit
            market_cap = get_market_cap(chain_info['coingecko_id'])

            # Calculate TVL/MC ratio
            tvl_mc_ratio = (current_tvl / market_cap) if market_cap else None

            # Get historical TVL for comparison
            tvl_7d = None
            tvl_30d = None

            # Look back 7 days
            for i in range(6, 9):
                date_7d = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                if date_7d in history and chain_name in history[date_7d]:
                    tvl_7d = history[date_7d][chain_name]['tvl']
                    break

            # Look back 30 days
            for i in range(28, 32):
                date_30d = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                if date_30d in history and chain_name in history[date_30d]:
                    tvl_30d = history[date_30d][chain_name]['tvl']
                    break

            # Calculate changes
            change_7d = calculate_tvl_change(current_tvl, tvl_7d)
            change_30d = calculate_tvl_change(current_tvl, tvl_30d)

            chain_data.append({
                'name': chain_name,
                'symbol': chain_info['symbol'],
                'region': chain_info['region'],
                'tvl': current_tvl,
                'market_cap': market_cap,
                'tvl_mc_ratio': tvl_mc_ratio,
                'change_7d': change_7d,
                'change_30d': change_30d
            })

        time.sleep(2)  # Rate limit

    # Save updated history
    save_history(history)

    # Get infrastructure metrics
    print("Fetching infrastructure metrics...")
    l1_ratios = get_l1_ratios()
    eth_gas = get_eth_gas_fees()
    sol_fees = get_solana_fees()
    bnb_gas = get_bnb_gas_fees()
    staking_data = get_staking_data()

    # ========== BUILD MESSAGE ==========

    message = "🏗️ <b>TVL INFRASTRUCTURE MONITOR</b>\n"
    message += f"📅 {datetime.now().strftime('%A, %B %d, %Y')}\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"

    # ========== SECTION 1: LAYER 1 RACE (VS BTC) ==========
    message += "🏁 <b>LAYER 1 RACE (vs BTC)</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"

    if l1_ratios:
        # Sort by trend
        sorted_l1s = sorted(l1_ratios.items(), key=lambda x: x[1]['trend_7d'], reverse=True)

        for symbol, data in sorted_l1s:
            ratio = data['ratio']
            trend = data['trend_7d']

            if trend > 5:
                emoji = "🔥"
            elif trend > 2:
                emoji = "🟢"
            elif trend > -2:
                emoji = "⚪"
            elif trend > -5:
                emoji = "🟡"
            else:
                emoji = "🔴"

            # ETH threshold notes
            if symbol == 'ETH':
                if ratio > 0.038:
                    note = " 🟢"
                elif ratio < 0.034:
                    note = " 🔴"
                else:
                    note = ""
            else:
                note = ""

            message += f"{emoji} {symbol}: {ratio:.6f} ({trend:+.1f}%% est){note}\n"

        message += "\n"
    else:
        message += "⚠️ L1 ratio data unavailable\n\n"

# ========== SECTION 2: NETWORK ACTIVITY ==========
    message += "━━━━━━━━━━━━━━━━━━━━\n"
    message += "⛽ <b>NETWORK ACTIVITY</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"

    message += "<b>Gas Fees (Top 3):</b>\n"

    if eth_gas:
        standard = eth_gas['standard']
        if standard < 10:
            gas_status = "🟢 Very low"
        elif standard < 20:
            gas_status = "🟢 Low"
        elif standard < 50:
            gas_status = "🟡 Moderate"
        else:
            gas_status = "🔴 High"
        # Check if it's estimated
        gas_note = " (est)" if standard == 15.0 else ""
        message += f"• ETH: {standard:.1f} gwei ({gas_status}){gas_note}\n"

    if sol_fees:
        fee_usd = sol_fees['fee_usd']
        message += f"• SOL: ${fee_usd:.4f} per tx 🟢 Ultra-low (est)\n"

    if bnb_gas:
        fee_usd = bnb_gas['fee_usd']
        message += f"• BNB: ${fee_usd:.3f} per tx 🟢 Very low (est)\n"

    message += "\n<b>Staking Ratios (Top 3):</b>\n"

    if staking_data:
        for symbol in ['ETH', 'SOL', 'BNB']:
            if symbol in staking_data:
                data = staking_data[symbol]
                ratio = data['ratio']

                if symbol == 'ETH':
                    if ratio >= 28:
                        status = "🟢 Healthy"
                    elif ratio >= 25:
                        status = "🟡 Moderate"
                    else:
                        status = "🔴 Weak"
                elif symbol == 'SOL':
                    if ratio >= 65:
                        status = "🟢 Healthy"
                    else:
                        status = "🟡 Moderate"
                elif symbol == 'BNB':
                    if ratio >= 15:
                        status = "🟢 Healthy"
                    else:
                        status = "🟡 Moderate"
                else:
                    status = ""

                # Add note if present
                note_text = f" ({data['note']})" if 'note' in data else ""

                message += f"• {symbol}: {ratio}%% ({status}){note_text}\n"

    message += "\n"

    # ========== SECTION 3: TVL BY REGION ==========
    message += "━━━━━━━━━━━━━━━━━━━━\n"
    message += "📊 <b>TVL BY REGION</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"

    # Group by region
    regions = {}
    for chain in chain_data:
        region = chain['region']
        if region not in regions:
            regions[region] = []
        regions[region].append(chain)

    # Sort chains within each region by TVL
    for region in regions:
        regions[region].sort(key=lambda x: x['tvl'], reverse=True)

    # Display by region
    for region_name, chains in sorted(regions.items()):
        message += f"🌍 <b>{region_name.upper()}</b>\n\n"

        region_total_tvl = sum(c['tvl'] for c in chains)

        for chain in chains:
            tvl_billions = chain['tvl'] / 1e9

            # Get emoji based on 30d change (or 7d if 30d not available)
            change_for_emoji = chain['change_30d'] if chain['change_30d'] is not None else chain['change_7d']
            emoji = get_signal_emoji(change_for_emoji)

            message += f"{emoji} <b>{chain['symbol']}</b>: ${tvl_billions:.2f}B\n"

            # 7d and 30d changes
            if chain['change_7d'] is not None:
                message += f"   7d: {chain['change_7d']:+.1f}%%"
            else:
                message += f"   7d: N/A"

            if chain['change_30d'] is not None:
                message += f" | 30d: {chain['change_30d']:+.1f}%%\n"
            else:
                message += f" | 30d: N/A\n"

            # TVL/MC ratio
            if chain['tvl_mc_ratio']:
                ratio = chain['tvl_mc_ratio']

                if ratio > 0.15:
                    ratio_signal = "🟢 Undervalued"
                elif ratio > 0.08:
                    ratio_signal = "🟡 Fair"
                else:
                    ratio_signal = "🔴 Overvalued"

                message += f"   TVL/MC: {ratio:.3f} ({ratio_signal})\n"

            message += "\n"

        # Region total
        region_total_billions = region_total_tvl / 1e9
        message += f"<b>{region_name} Total:</b> ${region_total_billions:.2f}B\n\n"

    # ========== SECTION 4: REGIONAL INFRASTRUCTURE ANALYSIS ==========
    message += "━━━━━━━━━━━━━━━━━━━━\n"
    message += "🌐 <b>REGIONAL INFRASTRUCTURE ANALYSIS</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"

    # Calculate regional changes (use 7d if 30d not available)
    regional_changes = {}
    for region_name, chains in regions.items():
        chains_with_change = []
        for c in chains:
            change = c['change_30d'] if c['change_30d'] is not None else c['change_7d']
            if change is not None:
                chains_with_change.append(change)

        if chains_with_change:
            avg_change = sum(chains_with_change) / len(chains_with_change)
            regional_changes[region_name] = avg_change

    if regional_changes:
        message += "<b>Growth by Region:</b>\n"
        for region_name, avg_change in sorted(regional_changes.items(), key=lambda x: x[1], reverse=True):
            emoji = get_signal_emoji(avg_change)
            period = "30d" if any(c['change_30d'] is not None for c in regions.get(region_name, [])) else "7d est"
            message += f"{emoji} {region_name}: {avg_change:+.1f}%% ({period})\n"

        message += "\n"

        # Multi-chain thesis validation
        western_change = regional_changes.get('Western DeFi', 0)
        asian_change = regional_changes.get('Asian Speed', 0)

        message += "<b>Multi-Chain Thesis Check:</b>\n"
        if asian_change > western_change + 5:
            message += "✅ Asian infrastructure gaining vs West\n"
            message += "   <i>Multi-polar fragmentation confirmed</i>\n"
        elif western_change > asian_change + 5:
            message += "⚠️ Western DeFi still dominant\n"
            message += "   <i>Multi-chain thesis not yet confirmed</i>\n"
        else:
            message += "🟡 Balanced growth across regions\n"
            message += "   <i>Infrastructure diversifying but not decisive</i>\n"

        message += "\n"
    else:
        message += "<i>Insufficient historical data for regional analysis</i>\n"
        message += "<i>Check back tomorrow for trends</i>\n\n"

    # ========== SECTION 5: KEY INSIGHTS ==========
    message += "━━━━━━━━━━━━━━━━━━━━\n"
    message += "💡 <b>KEY INSIGHTS</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"

    insights_found = False

    # Find fastest growing chain (use 30d or 7d)
    chains_with_growth = []
    for c in chain_data:
        change = c['change_30d'] if c['change_30d'] is not None else c['change_7d']
        if change and change > 5:
            chains_with_growth.append((c, change))

    if chains_with_growth:
        fastest = max(chains_with_growth, key=lambda x: x[1])
        chain, change = fastest
        period = "30d" if chain['change_30d'] is not None else "7d"
        message += f"🔥 <b>Fastest Growth:</b> {chain['symbol']} ({change:+.1f}%% {period})\n"
        message += f"   <i>Real usage increasing - capital flowing in</i>\n\n"
        insights_found = True

    # Find declining chains
    chains_with_decline = []
    for c in chain_data:
        change = c['change_30d'] if c['change_30d'] is not None else c['change_7d']
        if change and change < -5:
            chains_with_decline.append((c, change))

    if chains_with_decline:
        fastest_decline = min(chains_with_decline, key=lambda x: x[1])
        chain, change = fastest_decline
        period = "30d" if chain['change_30d'] is not None else "7d"
        message += f"📉 <b>Biggest Decline:</b> {chain['symbol']} ({change:+.1f}%% {period})\n"
        message += f"   <i>Capital leaving - users migrating elsewhere</i>\n\n"
        insights_found = True

    # Find most undervalued (high TVL/MC ratio + positive momentum)
    undervalued_chains = []
    for c in chain_data:
        change = c['change_30d'] if c['change_30d'] is not None else c['change_7d']
        if c['tvl_mc_ratio'] and c['tvl_mc_ratio'] > 0.12 and change and change > 0:
            undervalued_chains.append(c)

    if undervalued_chains:
        best_value = max(undervalued_chains, key=lambda x: x['tvl_mc_ratio'])
        change = best_value['change_30d'] if best_value['change_30d'] is not None else best_value['change_7d']
        period = "30d" if best_value['change_30d'] is not None else "7d"
        message += f"💎 <b>Best Value:</b> {best_value['symbol']} (TVL/MC: {best_value['tvl_mc_ratio']:.3f}, +{change:.1f}%% {period})\n"
        message += f"   <i>High usage relative to valuation + growing</i>\n\n"
        insights_found = True

    # Infrastructure dominance shift (SOL vs ETH)
    eth_chain = next((c for c in chain_data if c['symbol'] == 'ETH'), None)
    sol_chain = next((c for c in chain_data if c['symbol'] == 'SOL'), None)

    if eth_chain and sol_chain:
        eth_change = eth_chain['change_30d'] if eth_chain['change_30d'] is not None else eth_chain['change_7d']
        sol_change = sol_chain['change_30d'] if sol_chain['change_30d'] is not None else sol_chain['change_7d']

        if eth_change is not None and sol_change is not None:
            if sol_change > eth_change + 5:
                period = "30d" if eth_chain['change_30d'] is not None else "7d"
                message += f"🔄 <b>Infrastructure Shift:</b> SOL gaining on ETH\n"
                message += f"   ETH: {eth_change:+.1f}%% | SOL: {sol_change:+.1f}%% ({period})\n"
                message += f"   <i>Alternative L1s challenging Ethereum dominance</i>\n\n"
                insights_found = True

    if not insights_found:
        message += "<i>First run - building historical baseline</i>\n"
        message += "<i>Key insights will appear as trends develop</i>\n\n"

    message += "━━━━━━━━━━━━━━━━━━━━"

    # Send to Telegram
    print("\nSending TVL report to Telegram...")
    send_telegram_message(message)
    print(f"✅ TVL infrastructure monitor complete")


if __name__ == "__main__":
    generate_tvl_report()