import os

def create_toml_file():
    with open(".env", "r") as f:
        lines = f.readlines()
    
    with open("secrets.toml", "w") as out:
        out.write("# COPIED FROM .ENV - PASTE THIS INTO STREAMLIT SECRETS\n")
        out.write("# -----------------------------------------------------\n\n")
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"): continue
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'").strip('"')
                out.write(f'{k} = "{v}"\n')
    
    print("Created 'secrets.toml'. Please open it and copy the content.")

if __name__ == "__main__":
    create_toml_file()
