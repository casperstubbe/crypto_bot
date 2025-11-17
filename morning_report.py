#!/usr/bin/env python3
"""
COMPREHENSIVE MORNING REPORT
Combines macro assessment, infrastructure monitoring, long-term entries, and trade signals
Run daily at 9 AM

UPDATED: November 9, 2025 - Added 90-day structural divergence section
"""

from crypto_monitor import *
from config import *
from catalyst_tracker import get_catalyst_marker, CATALYSTS
import time
import requests

# Import functions from other modules
from divergence_reporter import (
    get_macro_regime,
    calculate_quality_score,
    get_fear_greed_index,
    calculate_rsi,
    get_rsi_for_coin,
    get_volume_comparison,
    get_market_context,
    get_long_term_price_change,
    calculate_structural_divergence
)

from infrastructure_monitor import (
    get_l1_ratios,
    get_eth_gas_fees,
    get_eth_staking_ratio,
    get_dex_volume_by_chain,
    get_tvl_by_chain,
    get_dxy,
    get_dollar_regime,
    get_real_yields,
    get_fed_funds_rate,
    get_fed_balance_sheet,
    get_reverse_repo,
    get_treasury_general_account,
    assess_liquidity_regime,
    detect_scenario,
    INFRASTRUCTURE_COINS
)

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

def generate_morning_report():
    """Generate comprehensive morning report"""

    current_time = get_montevideo_time()

    print(f"=" * 70)
    print(f"MORNING REPORT - {current_time.strftime('%A, %B %d, %Y')}")
    print(f"=" * 70)

    # Get market context
    print("Fetching market context...")
    market_context = get_market_context()

    # Get Fear & Greed Index
    print("Fetching Fear & Greed Index...")
    fg_value, fg_classification = get_fear_greed_index()

    # Get BTC RSI
    print("Calculating BTC RSI...")
    btc_rsi = get_rsi_for_coin('BTC')

    # Get BTC Volume comparison
    print("Calculating BTC volume...")
    btc_volume_vs_avg = get_volume_comparison('BTC')

    # Get current prices
    print("Fetching current prices...")
    current_data = get_current_prices()
    if not current_data:
        send_telegram_message("❌ Error fetching current prices")
        return

    # Bitcoin data
    btc_data = current_data.get(BITCOIN_ID, {})
    btc_price = btc_data.get('usd', 0)
    btc_24h_change = btc_data.get('usd_24h_change', 0)

    # Get BTC historical data
    print("Fetching BTC historical prices...")
    time.sleep(6)
    btc_week_ago = get_historical_price_with_retry(BITCOIN_ID, 7)
    time.sleep(6)
    btc_14d_ago = get_historical_price_with_retry(BITCOIN_ID, 14)

    btc_7d_change = 0
    btc_14d_change = 0

    if btc_week_ago:
        btc_7d_change = ((btc_price - btc_week_ago) / btc_week_ago) * 100

    if btc_14d_ago:
        btc_14d_change = ((btc_price - btc_14d_ago) / btc_14d_ago) * 100

    # Get Gold data early
    print("Fetching Gold data...")
    gold_data = current_data.get('pax-gold', {})
    gold_price = gold_data.get('usd', 0)
    gold_24h_change = gold_data.get('usd_24h_change', 0)

    # Calculate gold/BTC divergence
    gold_btc_divergence = None
    if btc_24h_change and gold_24h_change:
        gold_btc_divergence = calculate_divergence(btc_24h_change, gold_24h_change)

    # Calculate macro regime
    macro_regime, macro_reason = get_macro_regime(
        btc_price=btc_price,
        gold_divergence=gold_btc_divergence,
        btc_dominance=market_context.get('btc_dominance'),
        eth_btc_signal=market_context.get('eth_btc_signal'),
        btc_rsi=btc_rsi
    )

    print(f"🎯 MACRO REGIME: {macro_regime} - {macro_reason}\n")

    # ========== BUILD MESSAGE ==========
    message = f"🌅 <b>MORNING REPORT</b>\n"
    message += f"📅 {current_time.strftime('%A, %B %d, %Y')}\n"
    message += f"🕐 {current_time.strftime('%H:%M %Z')}\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"

    # ========== SECTION 1: BITCOIN & MACRO ==========
    message += "📊 <b>MARKET OVERVIEW</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"

    message += f"₿ <b>Bitcoin:</b> ${btc_price:,.0f}\n"
    message += f"   24h: {btc_24h_change:+.2f}%% | 7d: {btc_7d_change:+.2f}%% | 14d: {btc_14d_change:+.2f}%%\n"

    # BTC indicators
    indicators = []
    if btc_rsi is not None:
        if btc_rsi < 30:
            indicators.append(f"📈 RSI:{btc_rsi:.0f} 🟢")
        elif btc_rsi > 70:
            indicators.append(f"📈 RSI:{btc_rsi:.0f} 🔴")
        else:
            indicators.append(f"📈 RSI:{btc_rsi:.0f}")

    if fg_value is not None:
        if fg_value < 25:
            fg_emoji = "😱"
        elif fg_value < 45:
            fg_emoji = "😰"
        elif fg_value < 55:
            fg_emoji = "😐"
        elif fg_value < 75:
            fg_emoji = "😊"
        else:
            fg_emoji = "🤑"
        indicators.append(f"{fg_emoji} F&G:{fg_value}")

    if btc_volume_vs_avg is not None:
        indicators.append(f"💰 Vol:{btc_volume_vs_avg:+.0f}%% vs 30d")

    message += f"   {' | '.join(indicators)}\n\n"

    # Market Context
    if market_context['btc_dominance']:
        btc_dom = market_context['btc_dominance']
        dom_signal = market_context['btc_dom_signal']
        dom_emoji = "🟢" if dom_signal == 'BUY' else "🔴" if dom_signal == 'SELL' else "🟡"
        message += f"{dom_emoji} BTC.D: {btc_dom:.1f}%% "

    if market_context['eth_btc_ratio']:
        ratio = market_context['eth_btc_ratio']
        trend = market_context['eth_btc_trend']
        signal = market_context['eth_btc_signal']
        ratio_emoji = "🟢" if signal == 'BUY' else "🔴" if signal == 'SELL' else "🟡"
        message += f"| {ratio_emoji} ETH/BTC: {ratio:.5f} ({trend:+.1f}%% 7d) "

    if market_context['alt_volume_share']:
        vol_share = market_context['alt_volume_share']
        vol_signal = market_context['alt_vol_signal']
        vol_emoji = "🟢" if vol_signal == 'BUY' else "🔴" if vol_signal == 'CAUTION' else "🟡"
        message += f"| {vol_emoji} AltVol: {vol_share:.0f}%%"

    message += "\n\n"

    # ========== SECTION 3: INFRASTRUCTURE STATUS ==========
    message += "━━━━━━━━━━━━━━━━━━━━\n"
    message += "🏗️ <b>INFRASTRUCTURE STATUS</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"

    # Get L1 ratios
    print("Fetching L1 ratios...")
    ratios = get_l1_ratios()

    if ratios:
        message += "<b>Layer 1 Race (vs BTC):</b>\n"

        # Sort by trend
        sorted_l1s = sorted(ratios.items(), key=lambda x: x[1]['trend_7d'], reverse=True)

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

            message += f"{emoji} {symbol}: {ratio:.6f} ({trend:+.1f}%% 7d){note}\n"

        message += "\n"

        # Scenario detection
        scenario, description, recommendation = detect_scenario(ratios)

        if scenario == "A":
            scenario_emoji = "⚠️"
        elif scenario == "B":
            scenario_emoji = "🚀"
        elif scenario == "C":
            scenario_emoji = "❌"
        else:
            scenario_emoji = "🤔"

        message += f"🎯 <b>Scenario {scenario_emoji} {scenario}:</b> {description}\n"
        message += f"   💡 {recommendation}\n\n"

    # Network Activity
    print("Fetching network activity...")
    gas_fees = get_eth_gas_fees()
    staking_data = get_eth_staking_ratio()

    if gas_fees or staking_data:
        message += "<b>Network Activity:</b>\n"

        if gas_fees:
            standard = gas_fees['standard']

            if standard < 1:
                gas_status = "🟢 Ultra-low"
            elif standard < 10:
                gas_status = "🟢 Very low"
            elif standard < 20:
                gas_status = "🟢 Low"
            elif standard < 50:
                gas_status = "🟡 Moderate"
            else:
                gas_status = "🔴 High"

            message += f"• ETH Gas: {standard} gwei ({gas_status})\n"

        if staking_data:
            ratio = staking_data['ratio']

            if ratio >= 28:
                staking_status = "🟢 Healthy"
            elif ratio >= 25:
                staking_status = "🟡 Moderate"
            else:
                staking_status = "🔴 Weak"

            message += f"• ETH Staking: {ratio}%% ({staking_status})\n"

        message += "\n"

    # DeFi Activity
    print("Fetching DeFi metrics...")
    dex_volume = get_dex_volume_by_chain()
    tvl_data = get_tvl_by_chain()

    if dex_volume:
        message += "<b>DEX Volume (24h):</b>\n"

        sorted_chains = sorted(dex_volume.items(), key=lambda x: x[1]['volume'], reverse=True)

        for symbol, data in sorted_chains[:3]:  # Top 3 only
            volume = data['volume']
            percentage = data['percentage']

            if volume >= 1e9:
                volume_str = f"${volume/1e9:.1f}B"
            else:
                volume_str = f"${volume/1e6:.0f}M"

            emoji = "🔥" if percentage > 50 else "🟢" if percentage > 20 else "🟡"
            message += f"{emoji} {symbol}: {volume_str} ({percentage}%%)\n"

        message += "\n"

     # ========== ETF FLOWS SECTION ==========
    message += "━━━━━━━━━━━━━━━━━━━━\n"
    message += "💼 <b>ETF FLOW TRACKER</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"

    print("Fetching ETF flows...")
    etf_data = get_btc_etf_flows()

    if etf_data:
        interpretation = interpret_etf_flows(etf_data)

        if interpretation:
            # Show fallback warning if using estimated data
            if interpretation.get('is_fallback'):
                message += "⚠️ <i>Using estimated data (API unavailable)</i>\n\n"

            message += f"<b>Latest:</b> {interpretation['flow_signal']}\n"
            message += f"   {interpretation['flow_desc']}\n\n"

            message += f"<b>7-Day Avg:</b> {interpretation['trend_signal']} ({interpretation['avg_7d']:+,.0f} BTC/day)\n\n"

            message += f"<b>Holdings:</b> {interpretation['holdings_signal']}\n"
            message += f"   {interpretation['holdings_desc']}\n"

            # Thesis validation
            if interpretation['holdings_pct'] >= 12:
                message += f"\n✅ <b>12%% THESIS TRIGGERED!</b> Scarcity phase active\n"

            message += "\n"
    else:
        message += "⚠️ ETF data unavailable\n\n"

# ========== DERIVATIVES & LEVERAGE SECTION ==========
    message += "━━━━━━━━━━━━━━━━━━━━\n"
    message += "⚡ <b>DERIVATIVES MARKET</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"

    print("Fetching funding rate and open interest...")
    funding_data = get_funding_rate()
    oi_data = get_open_interest()

    if funding_data and oi_data:
        # Display funding rate
        message += f"<b>Funding Rate:</b> {funding_data['signal']}\n"
        message += f"   Current: {funding_data['rate_pct']:.4f}%% per 8hrs\n"
        message += f"   Annualized: {funding_data['annualized_pct']:.1f}%%\n"
        message += f"   {funding_data['explanation']}\n\n"

        # Display open interest
        message += f"<b>Open Interest:</b> {oi_data['signal']}\n"
        message += f"   Total: ${oi_data['oi_billions']:.2f}B\n"
        message += f"   {oi_data['explanation']}\n\n"

        # Combined interpretation
        leverage_analysis = interpret_leverage_conditions(funding_data, oi_data)

        if leverage_analysis:
            message += f"<b>Market Condition:</b> {leverage_analysis['condition']}\n"
            message += f"   💡 {leverage_analysis['action']}\n"
            message += f"   🎯 {leverage_analysis['trade_signal']}\n\n"

        # Educational context
        message += "<i>📚 Context:</i>\n"
        message += "<i>• High funding + high OI = overleveraged, flush risk</i>\n"
        message += "<i>• Negative funding + high OI = shorts squeezed, bounce potential</i>\n"
        message += "<i>• Low OI = stable but boring, wait for setup</i>\n\n"

    else:
        message += "⚠️ Derivatives data unavailable\n\n"

    # ========== 90-DAY STRUCTURAL DIVERGENCE ==========
    message += "━━━━━━━━━━━━━━━━━━━━\n"
    message += "📊 <b>90-DAY STRUCTURAL DIVERGENCE</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"

    print("Analyzing 90-day structural positions...")

    # Get BTC baseline
    btc_90d_change = get_long_term_price_change('BTC', days=90)

    if btc_90d_change:
        message += f"<b>BTC 90d baseline:</b> {btc_90d_change:+.2f}%%\n\n"

        # Analyze all alts
        structural_results = []
        for coin_id, symbol in ALTCOINS.items():
            if coin_id == 'pax-gold':  # Skip gold
                continue

            alt_90d_change = get_long_term_price_change(symbol, days=90)

            if alt_90d_change:
                analysis = calculate_structural_divergence(alt_90d_change, btc_90d_change)
                if analysis:
                    structural_results.append({
                        'symbol': symbol,
                        'change': alt_90d_change,
                        'category': analysis['category'],
                        'divergence': analysis['divergence']
                    })

        # Group by category
        leaders = [r for r in structural_results if r['category'] in ['LEADER', 'STRONG']]
        trackers = [r for r in structural_results if r['category'] == 'TRACKER']
        laggards = [r for r in structural_results if r['category'] in ['WEAK', 'LAGGARD']]

        # Sort each group by divergence
        leaders.sort(key=lambda x: x['divergence'], reverse=True)
        laggards.sort(key=lambda x: x['divergence'])

        # Display compact summary
        if leaders:
            message += "🏆 <b>LEADERS</b> (Outperformed BTC):\n"
            leader_list = [f"{r['symbol']} ({r['divergence']:+.0f}%%)" for r in leaders[:5]]  # Top 5
            message += "   " + ", ".join(leader_list)
            if len(leaders) > 5:
                message += f" +{len(leaders)-5} more"
            message += "\n\n"

        if trackers:
            message += "➡️ <b>TRACKERS</b> (Neutral):\n"
            tracker_list = [r['symbol'] for r in trackers[:8]]  # Top 8
            message += "   " + ", ".join(tracker_list)
            if len(trackers) > 8:
                message += f" +{len(trackers)-8} more"
            message += "\n\n"

        if laggards:
            message += "🚨 <b>LAGGARDS</b> (Underperformed BTC):\n"
            laggard_list = [f"{r['symbol']} ({r['divergence']:+.0f}%%)" for r in laggards[:5]]  # Bottom 5
            message += "   " + ", ".join(laggard_list)
            if len(laggards) > 5:
                message += f" +{len(laggards)-5} more"
            message += "\n\n"

        message += "💡 <i>Context: Shows which assets are winning/losing infrastructure race</i>\n\n"
    else:
        message += "⚠️ Unable to fetch 90-day data\n\n"

    # ========== SECTION 2: DOLLAR STRENGTH ASSESSMENT ==========
    message += "━━━━━━━━━━━━━━━━━━━━\n"
    message += "💵 <b>DOLLAR STRENGTH</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"

    # Get dollar indicators
    print("Analyzing dollar strength...")

    # Get DXY with 90-day history
    print("Fetching DXY with 90-day trend...")
    api_key = "7fd7e4bd0c4be5b5d382faaa64e8d9ee"
    dxy_url = "https://api.stlouisfed.org/fred/series/observations"
    dxy_params = {
        'series_id': 'DTWEXBGS',
        'api_key': api_key,
        'file_type': 'json',
        'sort_order': 'desc',
        'limit': 100
    }

    dxy_today = None
    dxy_90d_ago = None
    dxy_values = []

    try:
        time.sleep(2)
        response = requests.get(dxy_url, params=dxy_params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if 'observations' in data and len(data['observations']) > 0:
                for obs in data['observations']:
                    value = obs.get('value', '.')
                    if value != '.':
                        dxy_values.append(float(value))

                if len(dxy_values) >= 2:
                    dxy_today = dxy_values[0]
                    if len(dxy_values) >= 65:
                        dxy_90d_ago = dxy_values[64]
    except:
        pass

    dxy_90d_change = 0
    dxy_90d_trend = "NEUTRAL"
    if dxy_today and dxy_90d_ago:
        dxy_90d_change = ((dxy_today - dxy_90d_ago) / dxy_90d_ago) * 100

        if dxy_90d_change > 3:
            dxy_90d_trend = "STRENGTHENING"
        elif dxy_90d_change < -3:
            dxy_90d_trend = "WEAKENING"

    dxy_data = get_dxy()
    real_yields = get_real_yields()

    eur_usd_value = dxy_data.get('eur_usd') if dxy_data else None
    real_yield_value = real_yields.get('value') if real_yields else None

    # Get dollar regime
    dollar_regime, dollar_emoji, dollar_interpretation, dollar_signals = get_dollar_regime(
        eur_usd_value,
        real_yield_value
    )

    message += f"{dollar_emoji} <b>{dollar_regime}</b>\n"
    message += f"   {dollar_interpretation}\n\n"

    # Display indicators
    message += "<b>Indicators:</b>\n"

    # EUR/USD
    if eur_usd_value:
        if eur_usd_value < 1.05:
            eur_status = "🔴 Strong dollar"
        elif eur_usd_value > 1.10:
            eur_status = "🟢 Weak dollar"
        else:
            eur_status = "🟡 Neutral"
        message += f"• EUR/USD: {eur_usd_value:.4f} ({eur_status})\n"

    # DXY with 90-day trend
    if dxy_today:
        if dxy_90d_trend == "STRENGTHENING":
            dxy_emoji_local = "🔴"
            dxy_interpretation = "rising (pressure on crypto)"
        elif dxy_90d_trend == "WEAKENING":
            dxy_emoji_local = "🟢"
            dxy_interpretation = "falling (bullish)"
        else:
            dxy_emoji_local = "🟡"
            dxy_interpretation = "stable"

        message += f"• DXY: {dxy_today:.2f} ({dxy_emoji_local} {dxy_interpretation})\n"
        if dxy_90d_ago:
            message += f"   90d change: {dxy_90d_change:+.2f}%% ({dxy_90d_trend})\n"

    # Real Yields
    if real_yield_value:
        # Get 10Y treasury rate dynamically
        treasury_url = "https://api.stlouisfed.org/fred/series/observations"
        treasury_params = {
            'series_id': 'DGS10',
            'api_key': api_key,
            'file_type': 'json',
            'sort_order': 'desc',
            'limit': 5
        }

        treasury_10y = None
        try:
            time.sleep(2)
            response = requests.get(treasury_url, params=treasury_params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if 'observations' in data and len(data['observations']) > 0:
                    for obs in data['observations']:
                        value = obs.get('value', '.')
                        if value != '.':
                            treasury_10y = float(value)
                            break
        except:
            pass

        # Get latest CPI dynamically
        cpi_url = "https://api.stlouisfed.org/fred/series/observations"
        cpi_params = {
            'series_id': 'CPIAUCSL',
            'api_key': api_key,
            'file_type': 'json',
            'sort_order': 'desc',
            'limit': 15
        }

        actual_inflation = None
        try:
            time.sleep(2)
            response = requests.get(cpi_url, params=cpi_params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if 'observations' in data and len(data['observations']) >= 13:
                    # Calculate YoY inflation from 12 months ago
                    cpi_now = None
                    cpi_12m_ago = None
                    for i, obs in enumerate(data['observations']):
                        value = obs.get('value', '.')
                        if value != '.' and cpi_now is None:
                            cpi_now = float(value)
                        if value != '.' and i >= 12 and cpi_12m_ago is None:
                            cpi_12m_ago = float(value)
                            break

                    if cpi_now and cpi_12m_ago:
                        actual_inflation = ((cpi_now - cpi_12m_ago) / cpi_12m_ago) * 100
        except:
            pass

        # Calculate backward-looking real yield
        backward_real_yield = None
        if treasury_10y and actual_inflation:
            backward_real_yield = treasury_10y - actual_inflation
            yield_spread = real_yield_value - backward_real_yield

        if real_yield_value > 2.5:
            yield_status = "🔴 High (BTC headwind)"
        elif real_yield_value < 1.5:
            yield_status = "🟢 Low (BTC tailwind)"
        else:
            yield_status = "🟡 Moderate"

        message += f"• Real Yields: {real_yield_value:.2f}%% ({yield_status})\n"

        # Show the forward premium if we have all data
        if backward_real_yield:
            if yield_spread > 0.5:
                message += f"   ⚠️ Market pricing tighter conditions (+{yield_spread:.2f}%% vs actual)\n"
            elif yield_spread < -0.5:
                message += f"   ✅ Market pricing easier conditions ({yield_spread:.2f}%% vs actual)\n"


# ========== SECTION 3: FED & LIQUIDITY ==========
    message += "━━━━━━━━━━━━━━━━━━━━\n"
    message += "🏦 <b>FED & LIQUIDITY</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"

    print("Fetching Fed indicators...")
    fed_funds = get_fed_funds_rate()
    balance_sheet = get_fed_balance_sheet()
    tga = get_treasury_general_account()

    # Display individual indicators
    if fed_funds:
        rate = fed_funds['rate']
        change = fed_funds['change']

        if change < 0:
            rate_signal = "🟢 CUTTING"
        elif change > 0:
            rate_signal = "🔴 HIKING"
        else:
            rate_signal = "🟡 PAUSED"

        message += f"<b>Fed Funds Rate:</b> {rate}%% | {rate_signal}\n"
        if change != 0:
            message += f"   Last change: {change:+.2f}%%\n"
        message += "\n"

    if balance_sheet:
        balance = balance_sheet['balance']
        change = balance_sheet['change_1m']

        if change > 0.01:
            bs_signal = "🟢 Expanding"
        elif change < -0.01:
            bs_signal = "🔴 QT active"
        else:
            bs_signal = "🟡 Stable"

        message += f"<b>Fed Balance Sheet:</b> ${balance:.3f}T | {bs_signal}\n"
        message += f"   1M change: {change:+.2f}T\n\n"

    if tga:
        balance = tga['balance']
        change = tga['change_1m']

        if change < -50:
            tga_signal = "🟢 Falling (injection)"
        elif change > 50:
            tga_signal = "🔴 Rising (drain)"
        else:
            tga_signal = "🟡 Stable"

        message += f"<b>Treasury Account:</b> ${balance:.0f}B | {tga_signal}\n"
        message += f"   1M change: {change:+.0f}B\n\n"

    # Overall liquidity assessment
    liquidity_regime, liq_emoji, liq_interpretation, liq_signals = assess_liquidity_regime(
        fed_funds, balance_sheet, None, tga
    )

    message += f"{liq_emoji} <b>LIQUIDITY REGIME: {liquidity_regime}</b>\n"
    message += f"   {liq_interpretation}\n\n"

    # Thesis alignment
    if "EASING" in liquidity_regime:
        message += "✅ <b>Thesis:</b> Fed pivot confirmed - structural support for alternatives\n\n"
    elif "TIGHTENING" in liquidity_regime:
        message += "⚠️ <b>Thesis:</b> QT still active - patience required for liquidity turn\n\n"
    else:
        message += "🟡 <b>Thesis:</b> Transitional - watch for clear easing signals\n\n"


    # ========== SECTION 6: CATALYSTS & ETF WAVES ==========
    has_catalysts = any(get_catalyst_marker(coin_id, days_ahead=30) for coin_id in CATALYSTS.keys())

    # Import ETF wave functions
    from catalyst_tracker import get_all_etf_waves, get_upcoming_catalysts

    etf_waves = get_all_etf_waves(days_ahead=30)

    if has_catalysts or etf_waves:
        message += "━━━━━━━━━━━━━━━━━━━━\n"
        message += "📅 <b>UPCOMING CATALYSTS (30 days)</b>\n"
        message += "━━━━━━━━━━━━━━━━━━━━\n\n"

        # Show ETF waves first (sector rotation opportunity)
        if etf_waves:
            message += "💎 <b>ETF WAVES (Sector Rotation):</b>\n"

            status_emoji_map = {
                "approved": "✅",
                "filed": "📋",
                "pending": "⏳",
                "speculation": "🔮"
            }

            for wave in etf_waves:
                status_emoji = status_emoji_map.get(wave['status'], "❓")
                coin_symbols = [ALTCOINS.get(c, c.upper()) for c in wave['coins']]

                # Highlight if approaching (within 3 days)
                urgency = "🔥 " if wave['days_until'] <= 3 else ""

                message += f"{urgency}• Day {wave['days_until']}: {wave['description']} {status_emoji}\n"
                message += f"   Coins: {', '.join(coin_symbols)} ({len(wave['coins'])} total)\n"

                # Add context for status
                if wave['status'] == 'approved' and wave['days_until'] <= 5:
                    message += f"   ⚡ Launch imminent - watch for sector pump\n"
                elif wave['status'] == 'pending':
                    message += f"   ⏰ Decision deadline - high volatility expected\n"

            message += "\n"

        # Then individual catalysts (excluding ETF wave duplicates)
        all_catalysts = []
        for coin_id in CATALYSTS.keys():
            catalysts = get_upcoming_catalysts(coin_id, days_ahead=30)
            if catalysts:
                symbol = ALTCOINS.get(coin_id, coin_id.upper())
                for c in catalysts:
                    # Skip if already shown in ETF wave
                    if not c.get('is_etf_wave'):
                        all_catalysts.append({
                            'symbol': symbol,
                            'days': c['days_until'],
                            'event': c['event'],
                            'impact': c['impact']
                        })

        if all_catalysts:
            message += "<b>Individual Catalysts:</b>\n"
            all_catalysts.sort(key=lambda x: x['days'])

            for cat in all_catalysts:
                # Emoji based on impact
                if cat['impact'].startswith('high'):
                    impact_emoji = "🔥"
                elif cat['impact'].startswith('medium'):
                    impact_emoji = "📅"
                else:
                    impact_emoji = "📌"

                message += f"{impact_emoji} <b>{cat['symbol']}</b> (Day {cat['days']}): {cat['event']}\n"

        message += "\n"

    message += "\n━━━━━━━━━━━━━━━━━━━━"

    # Send to Telegram
    print("\nSending morning report...")
    print(f"Message length: {len(message)} characters")
    
    # If message is too long, split it
    if len(message) > 4000:  # Leave margin below 4096 limit
        print("Message too long, splitting into parts...")
        parts = []
        current_part = ""
        
        for line in message.split('\n'):
            if len(current_part) + len(line) + 1 > 4000:
                parts.append(current_part)
                current_part = line + '\n'
            else:
                current_part += line + '\n'
        
        if current_part:
            parts.append(current_part)
        
        print(f"Sending {len(parts)} parts...")
        for i, part in enumerate(parts):
            send_telegram_message(part)
            print(f"✅ Part {i+1}/{len(parts)} sent")
            time.sleep(1)  # Delay between messages
    else:
        send_telegram_message(message)
        print(f"✅ Morning report sent at {current_time.strftime('%H:%M:%S')}")
        
if __name__ == "__main__":
    generate_morning_report()
