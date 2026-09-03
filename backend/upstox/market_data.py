import os
import requests
from dotenv import load_dotenv

load_dotenv("../.env")

UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")

BASE_URL = "https://api.upstox.com"


class UpstoxMarketData:

    def __init__(self):

        if not UPSTOX_ACCESS_TOKEN:
            raise RuntimeError(
                "UPSTOX_ACCESS_TOKEN not found"
            )

        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {UPSTOX_ACCESS_TOKEN}",
        }

    def get_ltp(self, instrument_key):

        url = f"{BASE_URL}/v3/market-quote/ltp"

        params = {
            "instrument_key": instrument_key
        }

        response = requests.get(
            url,
            headers=self.headers,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        return response.json()

    def get_indices(self):

        instruments = (
            "NSE_INDEX|Nifty 50,"
            "NSE_INDEX|Nifty Bank,"
            "NSE_INDEX|India VIX"
        )

        url = f"{BASE_URL}/v3/market-quote/ltp"

        params = {
            "instrument_key": instruments
        }

        response = requests.get(
            url,
            headers=self.headers,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        return response.json()