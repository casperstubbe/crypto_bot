import os

# Get from Railway environment variables
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
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
