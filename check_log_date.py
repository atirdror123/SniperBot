import os

def check_date(filename, date_str):
    if not os.path.exists(filename):
        print("File not found.")
        return
    
    found = False
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if date_str in line:
                    print(f"FOUND: {line.strip()}")
                    found = True
    except Exception as e:
        print(f"Error: {e}")

    if not found:
        print(f"Date {date_str} NOT FOUND in {filename}.")

check_date("scan.log", "2025-12-16")
