import os
import sys

def read_tail(filename, n=20):
    if not os.path.exists(filename):
        print(f"{filename} not found.")
        return

    print(f"--- TAIL OF {filename} ---")
    encodings = ['utf-8', 'utf-16', 'utf-16le', 'cp1252', 'latin1']
    for enc in encodings:
        try:
            with open(filename, 'rb') as f:
                # Read binary to seek end? efficient for huge files but let's just ready all for 22kb
                content = f.read()
                decoded = content.decode(enc)
                lines = decoded.splitlines()[-n:]
                for line in lines:
                    print(line)
                return
        except Exception:
            continue
    print("Failed to decode.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        read_tail(sys.argv[1])
    else:
        read_tail("highscore.log")
