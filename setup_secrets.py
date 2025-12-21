import os
from dotenv import load_dotenv

def setup():
    # Load .env
    load_dotenv()
    
    # Get Keys
    fmp = os.getenv("FMP_API_KEY", "")
    sub_url = os.getenv("SUPABASE_URL", "")
    sub_key = os.getenv("SUPABASE_KEY", "")
    p = os.getenv("DASHBOARD_PASSWORD", "Atirdror2")
    google_key = os.getenv("GOOGLE_API_KEY", "")
    
    # Format TOML
    toml_content = f"""
# Streamlit Secrets
DASHBOARD_PASSWORD = "{p}"
GOOGLE_API_KEY = "{google_key}"
FMP_API_KEY = "{fmp}"
SUPABASE_URL = "{sub_url}"
SUPABASE_KEY = "{sub_key}"
"""
    
    # Write
    os.makedirs(".streamlit", exist_ok=True)
    with open(".streamlit/secrets.toml", "w") as f:
        f.write(toml_content)
        
    print(f"Secrets written to .streamlit/secrets.toml")
    print(f"- FMP Key Length: {len(fmp)}")
    print(f"- Supabase URL Length: {len(sub_url)}")

if __name__ == "__main__":
    setup()
