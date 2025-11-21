#!/usr/bin/env python3
"""
Infrastructure Monitor
Tracks L1 competition and macro environment for strategic allocation

UPDATED: November 21, 2025 - Removed duplicates, imports from tvl_monitor
"""

from crypto_monitor import *
from config import *
import time
import requests

# Import shared functions from tvl_monitor instead of duplicating
from tvl_monitor import get_l1_ratios, get_eth_gas_fees

# Infrastructure coins for monitoring
INFRASTRUCTURE_COINS = {
    'ethereum': 'ETH',
    'solana': 'SOL',
    'cardano': 'ADA',
    'polkadot': 'DOT',
    'avalanche-2': 'AVAX',
    'internet-computer': 'ICP'
}

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


def get_dollar_regime(dxy_value):
    """Classify dollar strength regime"""
    if not dxy_value:
        return "UNKNOWN"
    
    # Based on normalized value (100/EUR_USD)
    if dxy_value > 95:
        return "VERY STRONG"
    elif dxy_value > 90:
        return "STRONG"
    elif dxy_value > 85:
        return "NEUTRAL"
    elif dxy_value > 80:
        return "WEAK"
    else:
        return "VERY WEAK"


def get_eth_staking_ratio():
    """Get ETH staking ratio"""
    print("Fetching ETH staking ratio...")

    try:
        # Use beaconcha.in API (no key needed)
        url = "https://beaconcha.in/api/v1/epoch/latest"
        
        time.sleep(2)
        response = requests.get(url, timeout=15)

        if response.status_code == 200:
            data = response.json()
            
            if 'data' in data:
                validator_count = data['data'].get('validatorscount', 0)
                
                if validator_count > 0:
                    total_staked = validator_count * 32
                    total_supply = 120_000_000
                    ratio = (total_staked / total_supply) * 100
                    
                    return {
                        'ratio': round(ratio, 1),
                        'validators': validator_count,
                        'staked': total_staked
                    }

        return None

    except Exception as e:
        print(f"  ❌ ETH staking error: {e}")
        return None


def get_dex_volume_by_chain():
    """Get DEX volume by chain from DeFiLlama"""
    print("Fetching DEX volumes...")

    try:
        url = "https://api.llama.fi/overview/dexs?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true&dataType=dailyVolume"
        
        time.sleep(2)
        response = requests.get(url, timeout=15)

        if response.status_code == 200:
            data = response.json()
            
            volumes = {}
            
            # Process top chains
            for chain_name, chain_data in data.get('totalDataChartBreakdown', {}).items():
                if len(chain_data) > 0:
                    latest_volume = chain_data[-1]
                    volumes[chain_name] = {
                        'volume': latest_volume,
                        'symbol': chain_name.upper()[:4]
                    }
            
            return volumes

        return None

    except Exception as e:
        print(f"  ❌ DEX volume error: {e}")
        return None


def get_tvl_by_chain():
    """Get TVL by chain from DeFiLlama"""
    print("Fetching TVL by chain...")

    try:
        url = "https://api.llama.fi/v2/chains"
        
        time.sleep(2)
        response = requests.get(url, timeout=15)

        if response.status_code == 200:
            data = response.json()
            
            tvls = {}
            
            for chain in data:
                name = chain.get('name')
                tvl = chain.get('tvl')
                
                if name and tvl:
                    tvls[name] = {
                        'tvl': tvl,
                        'change_1d': chain.get('change_1d'),
                        'change_7d': chain.get('change_7d')
                    }
            
            return tvls

        return None

    except Exception as e:
        print(f"  ❌ TVL error: {e}")
        return None


def get_real_yields():
    """Get real yields (10Y Treasury - CPI)"""
    print("Fetching real yields...")

    api_key = "7fd7e4bd0c4be5b5d382faaa64e8d9ee"

    try:
        # 10Y Treasury
        url = "https://api.stlouisfed.org/fred/series/observations"
        params = {
            'series_id': 'DGS10',
            'api_key': api_key,
            'file_type': 'json',
            'sort_order': 'desc',
            'limit': 5
        }
        
        time.sleep(2)
        response = requests.get(url, params=params, timeout=15)

        treasury_10y = None
        if response.status_code == 200:
            data = response.json()
            if 'observations' in data:
                for obs in data['observations']:
                    value = obs.get('value', '.')
                    if value != '.':
                        treasury_10y = float(value)
                        break

        # CPI YoY
        params['series_id'] = 'CPIAUCSL'
        params['limit'] = 13  # Need 13 months for YoY

        time.sleep(2)
        response = requests.get(url, params=params, timeout=15)

        cpi_yoy = None
        if response.status_code == 200:
            data = response.json()
            if 'observations' in data and len(data['observations']) >= 13:
                latest_cpi = float(data['observations'][0]['value'])
                year_ago_cpi = float(data['observations'][12]['value'])
                cpi_yoy = ((latest_cpi - year_ago_cpi) / year_ago_cpi) * 100

        # Calculate real yield
        if treasury_10y is not None and cpi_yoy is not None:
            real_yield = treasury_10y - cpi_yoy
            
            return {
                'real_yield': round(real_yield, 2),
                'treasury_10y': round(treasury_10y, 2),
                'cpi_yoy': round(cpi_yoy, 2)
            }

        return None

    except Exception as e:
        print(f"  ❌ Real yields error: {e}")
        return None


def get_fed_funds_rate():
    """Get Fed Funds Rate"""
    print("Fetching Fed Funds Rate...")

    api_key = "7fd7e4bd0c4be5b5d382faaa64e8d9ee"

    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        'series_id': 'FEDFUNDS',
        'api_key': api_key,
        'file_type': 'json',
        'sort_order': 'desc',
        'limit': 5
    }

    try:
        time.sleep(2)
        response = requests.get(url, params=params, timeout=15)

        if response.status_code == 200:
            data = response.json()
            
            if 'observations' in data:
                for obs in data['observations']:
                    value = obs.get('value', '.')
                    if value != '.':
                        return {'rate': round(float(value), 2)}

        return None

    except Exception as e:
        print(f"  ❌ Fed Funds error: {e}")
        return None


def get_fed_balance_sheet():
    """Get Fed Balance Sheet"""
    print("Fetching Fed Balance Sheet...")

    api_key = "7fd7e4bd0c4be5b5d382faaa64e8d9ee"

    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        'series_id': 'WALCL',  # Fed Total Assets
        'api_key': api_key,
        'file_type': 'json',
        'sort_order': 'desc',
        'limit': 5
    }

    try:
        time.sleep(2)
        response = requests.get(url, params=params, timeout=15)

        if response.status_code == 200:
            data = response.json()
            
            if 'observations' in data:
                for obs in data['observations']:
                    value = obs.get('value', '.')
                    if value != '.':
                        balance_sheet_millions = float(value)
                        balance_sheet_trillions = balance_sheet_millions / 1000
                        return {'balance_sheet': round(balance_sheet_trillions, 2)}

        return None

    except Exception as e:
        print(f"  ❌ Fed Balance Sheet error: {e}")
        return None


def get_reverse_repo():
    """Get Reverse Repo facility usage"""
    print("Fetching Reverse Repo...")

    api_key = "7fd7e4bd0c4be5b5d382faaa64e8d9ee"

    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        'series_id': 'RRPONTSYD',  # Reverse Repo
        'api_key': api_key,
        'file_type': 'json',
        'sort_order': 'desc',
        'limit': 5
    }

    try:
        time.sleep(2)
        response = requests.get(url, params=params, timeout=15)

        if response.status_code == 200:
            data = response.json()
            
            if 'observations' in data:
                for obs in data['observations']:
                    value = obs.get('value', '.')
                    if value != '.':
                        rrp_millions = float(value)
                        rrp_billions = rrp_millions / 1000
                        return {'rrp': round(rrp_billions, 0)}

        return None

    except Exception as e:
        print(f"  ❌ Reverse Repo error: {e}")
        return None


def get_treasury_general_account():
    """Get Treasury General Account balance"""
    print("Fetching TGA...")

    api_key = "7fd7e4bd0c4be5b5d382faaa64e8d9ee"

    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        'series_id': 'WTREGEN',  # Treasury General Account
        'api_key': api_key,
        'file_type': 'json',
        'sort_order': 'desc',
        'limit': 5
    }

    try:
        time.sleep(2)
        response = requests.get(url, params=params, timeout=15)

        if response.status_code == 200:
            data = response.json()
            
            if 'observations' in data:
                for obs in data['observations']:
                    value = obs.get('value', '.')
                    if value != '.':
                        tga_millions = float(value)
                        tga_billions = tga_millions / 1000
                        return {'tga': round(tga_billions, 0)}

        return None

    except Exception as e:
        print(f"  ❌ TGA error: {e}")
        return None


def assess_liquidity_regime(fed_balance, rrp, tga):
    """Assess overall liquidity conditions"""
    if not all([fed_balance, rrp, tga]):
        return "UNKNOWN"
    
    # Fed expanding + RRP low + TGA low = HIGH LIQUIDITY
    # Fed flat + RRP high + TGA high = LOW LIQUIDITY
    
    liquidity_score = 0
    
    # Fed Balance Sheet (higher = more liquidity)
    if fed_balance['balance_sheet'] > 7.5:
        liquidity_score += 2
    elif fed_balance['balance_sheet'] > 7.0:
        liquidity_score += 1
    else:
        liquidity_score -= 1
    
    # RRP (lower = more liquidity available)
    if rrp['rrp'] < 200:
        liquidity_score += 2
    elif rrp['rrp'] < 500:
        liquidity_score += 1
    else:
        liquidity_score -= 1
    
    # TGA (lower = more liquidity in system)
    if tga['tga'] < 400:
        liquidity_score += 1
    elif tga['tga'] > 800:
        liquidity_score -= 1
    
    # Classify
    if liquidity_score >= 4:
        return "🟢 HIGH LIQUIDITY"
    elif liquidity_score >= 2:
        return "🟡 MODERATE LIQUIDITY"
    elif liquidity_score >= 0:
        return "🟠 LOW LIQUIDITY"
    else:
        return "🔴 TIGHT LIQUIDITY"


def detect_scenario(ratios):
    """Detect market scenario based on L1 ratios"""
    if not ratios:
        return None, "Insufficient data", ""
    
    eth_ratio = ratios.get('ETH', {}).get('ratio', 0)
    
    # Scenario A: ETH/BTC > 0.038 (Altseason)
    if eth_ratio > 0.038:
        return "A", "Altseason - ETH/BTC strong", "Rotate to alts, BTC.D likely falling"
    
    # Scenario C: ETH/BTC < 0.034 (BTC dominance)
    elif eth_ratio < 0.034:
        return "C", "BTC Dominance - Flight to safety", "Stay in BTC, alts bleeding"
    
    # Scenario B: Neutral zone
    else:
        return "B", "Neutral - Consolidation phase", "Monitor for breakout direction"


if __name__ == "__main__":
    generate_infrastructure_report()
