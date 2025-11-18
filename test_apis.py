#!/usr/bin/env python3
"""
Test if crypto exchange APIs are accessible
"""
import requests
import time

def test_bybit():
    print("Testing Bybit API...")
    try:
        url = "https://api.bybit.com/v5/market/tickers"
        params = {'category': 'linear', 'symbol': 'BTCUSDT'}
        
        response = requests.get(url, params=params, timeout=10)
        print(f"  Bybit status: {response.status_code}")
        
        if response.status_code == 200:
            print("  ✅ Bybit API accessible!")
            return True
        else:
            print(f"  ❌ Bybit blocked: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Bybit error: {e}")
        return False

def test_binance():
    print("Testing Binance API...")
    try:
        url = "https://fapi.binance.com/fapi/v1/premiumIndex"
        params = {'symbol': 'BTCUSDT'}
        
        time.sleep(1)
        response = requests.get(url, params=params, timeout=10)
        print(f"  Binance status: {response.status_code}")
        
        if response.status_code == 200:
            print("  ✅ Binance API accessible!")
            return True
        else:
            print(f"  ❌ Binance blocked: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Binance error: {e}")
        return False

def test_coingecko():
    print("Testing CoinGecko API...")
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {'ids': 'bitcoin', 'vs_currencies': 'usd'}
        
        time.sleep(1)
        response = requests.get(url, params=params, timeout=10)
        print(f"  CoinGecko status: {response.status_code}")
        
        if response.status_code == 200:
            print("  ✅ CoinGecko API accessible!")
            return True
        else:
            print(f"  ❌ CoinGecko blocked: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ CoinGecko error: {e}")
        return False

if __name__ == "__main__":
    print("="*50)
    print("CRYPTO API ACCESSIBILITY TEST")
    print("="*50)
    
    bybit_ok = test_bybit()
    binance_ok = test_binance()
    coingecko_ok = test_coingecko()
    
    print("\n" + "="*50)
    print("RESULTS:")
    print("="*50)
    print(f"Bybit:     {'✅ PASS' if bybit_ok else '❌ FAIL'}")
    print(f"Binance:   {'✅ PASS' if binance_ok else '❌ FAIL'}")
    print(f"CoinGecko: {'✅ PASS' if coingecko_ok else '❌ FAIL'}")
    
    if bybit_ok or binance_ok:
        print("\n✅ Platform is suitable for crypto bot!")
    else:
        print("\n❌ Platform blocks crypto APIs - try another!")
    
    # Keep container alive for 60 seconds so we can see logs
    print("\nWaiting 60 seconds before exit...")
    time.sleep(60)
