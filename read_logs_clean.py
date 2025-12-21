def tail(f_path, n):
    try:
        with open(f_path, 'r') as f:
            lines = f.readlines()
            for line in lines[-n:]:
                print(line.strip())
    except Exception as e:
        print(f"Error reading {f_path}: {e}")

print("--- SCAN LOG ---")
tail("scan.log", 5)
print("\n--- HIGHSCORE LOG ---")
tail("highscore.log", 5)
