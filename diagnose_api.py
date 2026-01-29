"""
COMPREHENSIVE API DIAGNOSTIC
=============================
Checks all possible causes for API failure.
"""
import os
from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("GEMINI API DIAGNOSTIC")
print("=" * 60)

# 1. Check API Key
print("\n1. CHECKING API KEY...")
api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    print("   ❌ GOOGLE_API_KEY not found in .env!")
else:
    print(f"   ✓ API Key present (starts with: {api_key[:10]}...)")
    print(f"   ✓ Length: {len(api_key)} chars")

# 2. Import and Configure
print("\n2. TESTING IMPORT...")
try:
    import google.generativeai as genai
    print("   ✓ google.generativeai imported")
except ImportError as e:
    print(f"   ❌ Import failed: {e}")
    exit(1)

# 3. Configure
print("\n3. CONFIGURING...")
try:
    genai.configure(api_key=api_key)
    print("   ✓ genai.configure() succeeded")
except Exception as e:
    print(f"   ❌ Configure failed: {e}")

# 4. List Available Models
print("\n4. LISTING AVAILABLE MODELS...")
try:
    models = list(genai.list_models())
    flash_models = [m.name for m in models if 'flash' in m.name.lower()]
    pro_models = [m.name for m in models if 'pro' in m.name.lower()]
    print(f"   ✓ Found {len(models)} models total")
    print(f"   Flash models: {flash_models[:5]}")
    print(f"   Pro models: {pro_models[:3]}")
except Exception as e:
    print(f"   ❌ List models failed: {e}")
    models = []

# 5. Try Different Models
print("\n5. TESTING MODEL AVAILABILITY...")
test_models = [
    'gemini-2.0-flash',
    'gemini-1.5-flash',
    'gemini-1.5-pro',
    'gemini-pro'
]

for model_name in test_models:
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Say OK")
        print(f"   ✓ {model_name}: {response.text[:20]}...")
        print(f"   >>> WORKING MODEL FOUND: {model_name}")
        break
    except Exception as e:
        error_str = str(e)
        if '429' in error_str:
            print(f"   ⚠ {model_name}: Rate Limited (429)")
        elif 'not found' in error_str.lower() or '404' in error_str:
            print(f"   ✗ {model_name}: Model not available")
        else:
            print(f"   ✗ {model_name}: {error_str[:60]}...")

# 6. Check environment
print("\n6. ENVIRONMENT CHECK...")
print(f"   SUPABASE_URL set: {bool(os.getenv('SUPABASE_URL'))}")
print(f"   SUPABASE_KEY set: {bool(os.getenv('SUPABASE_KEY'))}")

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
