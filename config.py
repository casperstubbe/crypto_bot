import os

# TEMPORARY: Hardcode for testing
TELEGRAM_BOT_TOKEN = "8329894048:AAHRHWvz2NAZAZwCkYpA4znkyXFmEJ0p9G8"  # Paste your real token
TELEGRAM_CHAT_ID = "8311591798"      # Paste your real chat ID

# Fallback to environment if hardcoded values aren't set
if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_ACTUAL_BOT_TOKEN_HERE":
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_CHAT_ID or TELEGRAM_CHAT_ID == "YOUR_ACTUAL_CHAT_ID_HERE":
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

TIMEZONE = 'America/Montevideo'
BITCOIN_ID = 'bitcoin'

ALTCOINS = {
    'ethereum': 'ETH',
    'solana': 'SOL',
    'cardano': 'ADA',
    'polkadot': 'DOT',
    'avalanche-2': 'AVAX',
    'internet-computer': 'ICP',
    'litecoin': 'LTC',
    'ripple': 'XRP',
    'injective-protocol': 'INJ',
    'sui': 'SUI',
    'celestia': 'TIA',
    'sei-network': 'SEI',
    'kaspa': 'KAS',
    'binancecoin': 'BNB',
    'zcash': 'ZEC',
    'bittensor': 'TAO',
    'pax-gold': 'PAXG'
}
