import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def get_retry_session(retries=5, backoff_factor=1.0):
    """
    Creates a requests Session with:
    1. Browser-like User-Agent (to avoid blocking).
    2. Automatic Retries (5 times) for 500/502/503/504/429 errors.
    3. Exponential Backoff.
    """
    session = requests.Session()
    
    # Chrome 120 User Agent
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    session.headers.update(headers)
    
    # Retry Logic
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[403, 429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"] # Allow POST retries for FMP if needed
    )
    
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session
