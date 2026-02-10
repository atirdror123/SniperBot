"""
Connection Diagnostic Script
Tests connectivity to Google (Internet) and Supabase (Database) with strict timeouts.
"""
import os
import time
import requests
import socket
from dotenv import load_dotenv

load_dotenv()

def measure_ping(host, port=443):
    try:
        start = time.time()
        socket.create_connection((host, port), timeout=3)
        return (time.time() - start) * 1000
    except Exception as e:
        return None

print("=== DIAGNOSTIC START ===")

# 1. Check Internet
print("\n1. Checking Internet (www.google.com)...")
ping = measure_ping("www.google.com")
if ping:
    print(f"   ✅ Connected ({ping:.1f}ms)")
else:
    print(f"   ❌ FAILED to connect to google.com")

# 2. Check Supabase
supabase_url = os.getenv("SUPABASE_URL")
if supabase_url:
    subdomain = supabase_url.split("//")[1].split(".")[0]
    host = f"{subdomain}.supabase.co"
    print(f"\n2. Checking Supabase ({host})...")
    ping = measure_ping(host)
    if ping:
        print(f"   ✅ Connected ({ping:.1f}ms)")
        
        # REST API Check
        print("   Testing REST API Handshake...")
        try:
            start = time.time()
            resp = requests.get(f"{supabase_url}/rest/v1/", timeout=5)
            # 404 is fine, means we reached the server
            print(f"   ✅ REST API Responded ({resp.status_code}) in {(time.time() - start)*1000:.1f}ms")
        except Exception as e:
            print(f"   ❌ REST API Request Failed: {e}")
    else:
        print(f"   ❌ FAILED to connect to Supabase host")
else:
    print("   ⚠️ SQL_URL not set")

print("\n=== DIAGNOSTIC END ===")
