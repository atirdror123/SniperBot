import os

def search_log(filename, query):
    if not os.path.exists(filename):
        print(f"File not found: {filename}")
        return

    print(f"--- Searching {filename} for '{query}' ---")
    encodings = ['utf-8', 'utf-16', 'utf-16le', 'cp1252']
    
    for enc in encodings:
        try:
            with open(filename, 'r', encoding=enc) as f:
                lines = f.readlines()
                found = [l.strip() for l in lines if query in l]
                if found:
                     print(f"Found {len(found)} matches in {enc}:")
                     # Print last 10 matches
                     for line in found[-10:]:
                         print(line)
                     return
        except:
            continue
    print("No matches found in any standard encoding.")

if __name__ == "__main__":
    search_log("highscore.log", "2025-12-15")
    search_log("scan.log", "2025-12-15")
