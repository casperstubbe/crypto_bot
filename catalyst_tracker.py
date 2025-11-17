#!/usr/bin/env python3
"""
Catalyst tracking for crypto projects
Add upcoming events that could affect price
Includes semi-automated ETF filing wave tracking
NOW WITH: Seasonal pattern detection for historical timing patterns
Syncs with ALTCOINS list from config.py

UPDATED: November 9, 2025 - Added seasonal patterns for LTC, BTC, ETH, SOL, BNB and general altcoin patterns
"""

from datetime import datetime, timedelta
from config import ALTCOINS

# ========== INDIVIDUAL COIN CATALYSTS ==========
# Format: 'coin-id': [{'date': 'YYYY-MM-DD', 'event': 'Description', 'impact': 'high/medium/low'}]
# IMPORTANT: Keys must match ALTCOINS keys in config.py

CATALYSTS = {
    # Layer 1 Competitors (Infrastructure)
    'ethereum': [
        {'date': '2025-12-03', 'event': 'Fusaka Upgrade (PeerDAS 8x blob capacity, 60-150M gas limit, slot 13,164,544)', 'impact': 'high-technical'},
    ],
    'solana': [
        {'date': '2025-12-11', 'event': 'Breakpoint 2025 Conference (Abu Dhabi, Dec 11-13)', 'impact': 'high-narrative'},
    ],
    'cardano': [],
    'polkadot': [
        {'date': '2025-12-15', 'event': 'EVM/PVM compatibility launch (Solidity deployment on Polkadot)', 'impact': 'high-technical'},
        {'date': '2025-12-31', 'event': 'JAM Protocol upgrade (1M+ TPS, gasless txns, RISC-V VM)', 'impact': 'high-technical'},
    ],
    'avalanche-2': [],
    'internet-computer': [],

    # High Momentum L1s
    'injective-protocol': [
        {'date': '2025-12-31', 'event': 'Altria Mainnet Upgrade (Q4, scaling improvements)', 'impact': 'medium-technical'},
    ],
    'sui': [
        {'date': '2025-12-31', 'event': 'Mysticeti v2 consensus upgrade (Q4, faster parallel execution)', 'impact': 'high-technical'},
        {'date': '2025-12-31', 'event': 'Remora scaling (Q4, 100k+ TPS horizontal validator clusters)', 'impact': 'high-technical'},
        {'date': '2025-12-31', 'event': 'AI Agent integration (Q4, autonomous on-chain transactions)', 'impact': 'medium-narrative'},
    ],
    'sei-network': [
        {'date': '2025-12-31', 'event': 'Giga upgrade (Q4, scaling to 200k TPS target)', 'impact': 'high-technical'},
    ],
    'celestia': [],

    # Established Alts (high liquidity)
    'chainlink': [],
    'litecoin': [],
    'ripple': [
        {'date': '2025-11-20', 'event': 'Multiple XRP ETFs launch (21Shares, Bitwise, Franklin Templeton, WisdomTree)', 'impact': 'high-narrative'},
    ],
    'binancecoin': [],

    # Special Positions
    'cosmos': [],
    'bittensor': [
        {'date': '2025-12-10', 'event': 'TAO First Halving (emissions 7,200→3,600/day, supply shock)', 'impact': 'high-fundamental'},
    ],

    # Trending/Emerging
    'kaspa': [],
    'render-token': [],

    # PoW & Emerging
    'zcash': [],

    # Gold hedge
    'pax-gold': []
}


# ========== ETF FILING WAVE TRACKER ==========
# Semi-automated: Update monthly by asking Claude to search for new filing waves
# Tracks coordinated ETF filings that create sector rotations

KNOWN_ETF_WAVES = [
    {
        'date': '2025-10-03',
        'coins': ['cardano', 'avalanche-2', 'polkadot', 'sei-network', 'cosmos'],
        'description': 'REX-Osprey 21-ETF mega-filing (AAVE, ADA, AVAX, DOT, SEI, TRX, UNI+)',
        'impact': 'high',
        'status': 'filed',
        'source': 'SEC EDGAR',
        'verified_date': '2025-10-03'
    },
    {
        'date': '2025-11-13',
        'coins': ['ripple'],
        'description': 'XRP ETF launch (Canary Capital auto-effective)',
        'impact': 'high',
        'status': 'approved',
        'source': 'SEC',
        'verified_date': '2025-11-07'
    },
    {
        'date': '2025-11-20',
        'coins': ['ripple'],
        'description': 'XRP ETF launches (21Shares, Bitwise)',
        'impact': 'high',
        'status': 'approved',
        'source': 'SEC',
        'verified_date': '2025-11-07'
    },
    {
        'date': '2025-12-31',
        'coins': ['solana', 'cardano', 'avalanche-2', 'polkadot', 'litecoin', 'injective-protocol'],
        'description': 'Q4 2025 ETF decision window (post-shutdown batch)',
        'impact': 'high',
        'status': 'pending',
        'source': 'Estimated from filing dates',
        'verified_date': '2025-11-08'
    }
]


# ========== SEASONAL PATTERNS ==========
# Historical data showing which months/periods are traditionally strong/weak
# Confidence levels: 'high' (5+ years data), 'medium' (3-4 years), 'low' (1-2 years)

SEASONAL_PATTERNS = {
    # ========== ESTABLISHED COINS (High confidence patterns) ==========

    'litecoin': {
        'strong_months': [11, 12],
        'weak_months': [],
        'notes': 'November historically strongest month (17.8% avg return), December also strong (16.9%). Pattern holds 5+ years.',
        'confidence': 'high',
        'data_source': 'Cryptorank multi-year analysis',
        'verified_date': '2025-11-09',
        'additional_factors': ['Whale accumulation pattern in Q4', 'Breaking 4-year consolidation', 'DeFi activity picks up Q4']
    },

    'bitcoin': {
        'strong_months': [10, 11, 12],
        'weak_months': [6, 8, 9],
        'notes': 'Q4 historically bullish ("Uptober" through year-end). Summer months typically consolidation/correction.',
        'confidence': 'high',
        'data_source': 'Historical price analysis 2013-2024',
        'verified_date': '2025-11-09',
        'additional_factors': ['Halving cycle patterns', 'Institutional Q4 positioning', 'September worst month (-5% avg)']
    },

    'ethereum': {
        'strong_months': [4, 5, 10, 11, 12],
        'weak_months': [6, 9],
        'notes': 'April-May strongest (avg 92.75% gains in Q1), similar Q4 pattern to BTC. June and September averaging losses.',
        'confidence': 'high',
        'data_source': 'Historical price analysis 2017-2024, Coinglass data',
        'verified_date': '2025-11-09',
        'additional_factors': ['Conference cycles (Devcon typically Q4)', 'DeFi activity peaks Q1/Q4', 'Correlation to BTC ~0.85']
    },

    'solana': {
        'strong_months': [9],
        'weak_months': [6],
        'notes': 'September is historically SOL\'s best month (5/5 positive years). June consistently weak (4/5 negative years).',
        'confidence': 'medium',
        'data_source': 'CoinLore 5-year monthly analysis',
        'verified_date': '2025-11-09',
        'additional_factors': ['Breakpoint conference typically Q4', 'Summer selloff pattern', 'ATH in Nov 2021']
    },

    'binancecoin': {
        'strong_months': [1, 4, 7, 10],
        'weak_months': [],
        'notes': 'Quarterly BNB burns (Jan/April/July/Oct) create deflationary pressure. Burns typically positive for price.',
        'confidence': 'medium',
        'data_source': 'BNB burn history analysis, Binance quarterly reports',
        'verified_date': '2025-11-09',
        'additional_factors': ['Auto-burn mechanism', 'Supply reducing to 100M target', 'Burn size correlates with Binance volume']
    },

    # ========== GENERAL ALTCOIN PATTERNS ==========

    'cardano': {
        'strong_months': [10, 11, 12],
        'weak_months': [6, 9],
        'notes': 'Follows general altcoin seasonality - Q4 strength after BTC rallies, summer weakness. ETH correlation high.',
        'confidence': 'medium',
        'data_source': 'Altcoin Season Index historical patterns',
        'verified_date': '2025-11-09',
        'additional_factors': ['Upgrade timing (historically Q1/Q4)', 'ETF speculation waves', 'Summit conferences Q3/Q4']
    },

    'polkadot': {
        'strong_months': [10, 11, 12],
        'weak_months': [6, 9],
        'notes': 'Q4 strength tied to parachain auction cycles and altcoin season. Summer consolidation typical.',
        'confidence': 'medium',
        'data_source': 'Altcoin Season Index, parachain auction history',
        'verified_date': '2025-11-09',
        'additional_factors': ['Parachain auctions Q4 historically', 'DOT ATH in Nov 2021', 'Infrastructure narrative Q4']
    },

    'ripple': {
        'strong_months': [10, 11, 12],
        'weak_months': [6, 9],
        'notes': 'Follows altcoin season patterns - Q4 outperformance. Regulatory news can override seasonality.',
        'confidence': 'low',
        'data_source': 'Altcoin Season Index patterns',
        'verified_date': '2025-11-09',
        'additional_factors': ['ETF speculation November 2025', 'Regulatory news can override patterns', 'Banking adoption news']
    },

    'chainlink': {
        'strong_months': [10, 11, 12],
        'weak_months': [6, 9],
        'notes': 'Infrastructure token follows altcoin season patterns. Oracle demand cycles can create mid-year spikes.',
        'confidence': 'low',
        'data_source': 'Altcoin Season Index patterns',
        'verified_date': '2025-11-09',
        'additional_factors': ['Integration announcements (can happen any month)', 'DeFi activity peaks Q1/Q4', 'Infrastructure narrative']
    },

    'avalanche-2': {
        'strong_months': [10, 11, 12],
        'weak_months': [6, 9],
        'notes': 'Likely follows general altcoin seasonality but needs more data (launched 2020).',
        'confidence': 'low',
        'data_source': 'Limited historical data',
        'verified_date': '2025-11-09',
        'additional_factors': ['Subnet launches can happen anytime', 'DeFi activity follows market cycles']
    },
}


# ========== SEASONAL PATTERN FUNCTIONS ==========

def get_current_seasonal_signal(coin_id, current_month=None):
    """Check if we're currently in a historically strong or weak period"""
    if coin_id not in SEASONAL_PATTERNS:
        return None

    pattern = SEASONAL_PATTERNS[coin_id]
    month = current_month or datetime.now().month

    signal = None
    if month in pattern['strong_months']:
        signal = 'bullish'
    elif month in pattern['weak_months']:
        signal = 'bearish'
    else:
        signal = 'neutral'

    if signal in ['bullish', 'bearish']:
        return {
            'signal': signal,
            'month': month,
            'confidence': pattern['confidence'],
            'notes': pattern['notes'],
            'data_source': pattern['data_source'],
            'additional_factors': pattern.get('additional_factors', [])
        }

    return None


def get_seasonal_marker(coin_id):
    """Get a short marker string for seasonal signals in reports"""
    signal = get_current_seasonal_signal(coin_id)

    if not signal:
        return ""

    if signal['signal'] == 'bullish':
        if signal['confidence'] == 'high':
            return "📈🔥"
        else:
            return "📈"
    elif signal['signal'] == 'bearish':
        if signal['confidence'] == 'high':
            return "📉❄️"
        else:
            return "📉"

    return ""


def get_all_seasonal_signals(current_month=None):
    """Get seasonal signals for all coins that have patterns"""
    month = current_month or datetime.now().month
    month_name = datetime(2025, month, 1).strftime('%B')

    signals = []
    for coin_id in SEASONAL_PATTERNS.keys():
        signal = get_current_seasonal_signal(coin_id, month)
        if signal:
            symbol = ALTCOINS.get(coin_id, coin_id.upper())
            signals.append({
                'coin_id': coin_id,
                'symbol': symbol,
                **signal
            })

    confidence_order = {'high': 0, 'medium': 1, 'low': 2}
    signal_order = {'bullish': 0, 'neutral': 1, 'bearish': 2}

    signals.sort(key=lambda x: (confidence_order[x['confidence']], signal_order[x['signal']]))

    return {
        'month': month,
        'month_name': month_name,
        'signals': signals,
        'total_patterns': len(SEASONAL_PATTERNS)
    }


# ========== VALIDATION FUNCTIONS ==========

def validate_catalysts():
    """Ensure CATALYSTS dictionary matches ALTCOINS from config.py"""
    missing = set(ALTCOINS.keys()) - set(CATALYSTS.keys())
    extra = set(CATALYSTS.keys()) - set(ALTCOINS.keys())

    issues = []
    if missing:
        issues.append(f"⚠️  Missing from CATALYSTS: {', '.join(missing)}")
        issues.append(f"   Add these lines to CATALYSTS:")
        for coin in missing:
            issues.append(f"   '{coin}': [],  # TODO: Research {ALTCOINS[coin]} catalysts")

    if extra:
        issues.append(f"⚠️  In CATALYSTS but not in ALTCOINS: {', '.join(extra)}")
        issues.append(f"   Remove these from CATALYSTS or add to config.py")

    return len(issues) == 0, issues


# ========== ETF WAVE DETECTION ==========

def detect_potential_etf_wave(pumping_coins, threshold_days=7):
    """Alert system: If 3+ coins pump together and aren't in KNOWN_ETF_WAVES"""
    today = datetime.now().date()
    future_date = today + timedelta(days=threshold_days)

    for wave in KNOWN_ETF_WAVES:
        wave_date = datetime.strptime(wave['date'], '%Y-%m-%d').date()
        if today <= wave_date <= future_date:
            matching_coins = set(pumping_coins) & set(wave['coins'])
            if len(matching_coins) >= 2:
                return {
                    'type': 'known_wave',
                    'wave': wave,
                    'matching_coins': list(matching_coins),
                    'message': f"✅ Pump matches known wave: {wave['description']}"
                }

    if len(pumping_coins) >= 3:
        coin_symbols = [ALTCOINS.get(c, c.upper()) for c in pumping_coins]
        return {
            'type': 'unknown_wave',
            'coins': pumping_coins,
            'message': f"🚨 RESEARCH NEEDED: {len(pumping_coins)} coins pumping together",
            'action': f"Ask Claude: 'Search for ETF filing wave involving {', '.join(coin_symbols)} in November 2025'"
        }

    return None


# ========== CATALYST QUERY FUNCTIONS ==========

def get_etf_wave_exposure(coin_id, days_ahead=30):
    """Check if a coin is part of an upcoming ETF wave"""
    today = datetime.now().date()
    future_date = today + timedelta(days=days_ahead)

    for wave in KNOWN_ETF_WAVES:
        if coin_id in wave['coins']:
            wave_date = datetime.strptime(wave['date'], '%Y-%m-%d').date()
            if today <= wave_date <= future_date:
                days_until = (wave_date - today).days
                return {
                    'days_until': days_until,
                    'description': wave['description'],
                    'impact': wave['impact'],
                    'status': wave['status'],
                    'group_size': len(wave['coins']),
                    'verified_date': wave['verified_date'],
                    'source': wave['source']
                }
    return None


def get_upcoming_catalysts(coin_id, days_ahead=14):
    """Get catalysts for a coin in the next X days"""
    if coin_id not in CATALYSTS:
        return []

    if not CATALYSTS[coin_id]:
        return []

    today = datetime.now().date()
    future_date = today + timedelta(days=days_ahead)

    upcoming = []
    for catalyst in CATALYSTS[coin_id]:
        catalyst_date = datetime.strptime(catalyst['date'], '%Y-%m-%d').date()

        if today <= catalyst_date <= future_date:
            days_until = (catalyst_date - today).days
            wave_info = get_etf_wave_exposure(coin_id, days_ahead)
            is_wave = wave_info and abs(wave_info['days_until'] - days_until) <= 3

            upcoming.append({
                'date': catalyst['date'],
                'days_until': days_until,
                'event': catalyst['event'],
                'impact': catalyst['impact'],
                'is_etf_wave': is_wave,
                'wave_info': wave_info if is_wave else None
            })

    upcoming.sort(key=lambda x: x['days_until'])
    return upcoming


def get_catalyst_marker(coin_id, days_ahead=14):
    """Get marker string including both event catalysts AND seasonal patterns"""
    catalysts = get_upcoming_catalysts(coin_id, days_ahead)
    seasonal = get_seasonal_marker(coin_id)

    if not catalysts:
        wave_info = get_etf_wave_exposure(coin_id, days_ahead)
        if wave_info and wave_info['days_until'] <= days_ahead:
            return f"💎{wave_info['days_until']}d {seasonal}".strip()
        return seasonal

    catalyst = catalysts[0]

    if catalyst.get('is_etf_wave'):
        return f"💎{catalyst['days_until']}d {seasonal}".strip()

    if catalyst['impact'].startswith('high'):
        emoji = "🔥"
    elif catalyst['impact'].startswith('medium'):
        emoji = "📅"
    else:
        emoji = "📌"

    return f"{emoji}{catalyst['days_until']}d {seasonal}".strip()


def get_all_etf_waves(days_ahead=60):
    """Get all upcoming ETF waves for sector rotation tracking"""
    today = datetime.now().date()
    future_date = today + timedelta(days=days_ahead)

    upcoming_waves = []
    for wave in KNOWN_ETF_WAVES:
        wave_date = datetime.strptime(wave['date'], '%Y-%m-%d').date()
        if today <= wave_date <= future_date:
            days_until = (wave_date - today).days
            upcoming_waves.append({
                'days_until': days_until,
                'date': wave['date'],
                'coins': wave['coins'],
                'description': wave['description'],
                'impact': wave['impact'],
                'status': wave['status'],
                'source': wave['source'],
                'verified_date': wave['verified_date']
            })

    upcoming_waves.sort(key=lambda x: x['days_until'])
    return upcoming_waves


# ========== MAIN TEST ==========

if __name__ == "__main__":
    print("=" * 70)
    print("CATALYST TRACKER - Validation & Testing")
    print("=" * 70)

    # Validation
    print("\n📋 VALIDATION: Checking sync with config.py ALTCOINS")
    print("-" * 70)
    is_valid, issues = validate_catalysts()
    if is_valid:
        print("✅ CATALYSTS is in sync with config.ALTCOINS")
    else:
        print("❌ CATALYSTS needs updates:\n")
        for issue in issues:
            print(issue)

    print(f"\n📊 Tracking {len(ALTCOINS)} coins from config.py")
    coins_with_data = sum(1 for cats in CATALYSTS.values() if cats)
    print(f"   ✅ {coins_with_data} coins have catalyst data")

    # Seasonal Patterns
    print("\n" + "=" * 70)
    print("📈 SEASONAL PATTERNS (Historical Timing Indicators)")
    print("=" * 70)

    seasonal_report = get_all_seasonal_signals()
    print(f"\n📅 Current Month: {seasonal_report['month_name']}")
    print(f"📊 Tracking {seasonal_report['total_patterns']} coins with seasonal patterns\n")

    if seasonal_report['signals']:
        for s in seasonal_report['signals']:
            emoji = "📈" if s['signal'] == 'bullish' else "📉"
            conf_badge = f"[{s['confidence'].upper()}]"
            print(f"{emoji} {s['symbol']}: {s['signal'].upper()} {conf_badge}")
            print(f"   {s['notes']}\n")

    # ETF Waves
    print("\n" + "=" * 70)
    print("💎 ETF FILING WAVES")
    print("=" * 70)

    waves = get_all_etf_waves(days_ahead=60)
    print(f"\n{len(waves)} waves upcoming in next 60 days\n")

    if waves:
        status_emoji = {"filed": "📋", "pending": "⏳", "approved": "✅"}
        for wave in waves:
            emoji = status_emoji.get(wave['status'], "❓")
            coin_symbols = [ALTCOINS.get(c, c.upper()) for c in wave['coins']]
            print(f"{emoji} Day {wave['days_until']}: {wave['description']}")
            print(f"   {', '.join(coin_symbols)} ({len(wave['coins'])} total)\n")

    # Individual Catalysts
    print("\n" + "=" * 70)
    print("📅 CATALYSTS (next 30 days)")
    print("=" * 70 + "\n")

    for coin_id in sorted(CATALYSTS.keys()):
        catalysts = get_upcoming_catalysts(coin_id, days_ahead=30)
        seasonal_marker = get_seasonal_marker(coin_id)

        if catalysts or seasonal_marker:
            symbol = ALTCOINS.get(coin_id, coin_id.upper())
            print(f"{symbol}: {seasonal_marker}")
            for c in catalysts:
                wave_marker = " [ETF WAVE]" if c.get('is_etf_wave') else ""
                print(f"  Day {c['days_until']}: {c['event']} ({c['impact']}){wave_marker}")
            print()
