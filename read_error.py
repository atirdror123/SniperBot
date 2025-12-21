try:
    with open("fmp_error.log", "r", encoding="utf-16") as f:
        content = f.read()
        print("--- START ERROR LOG ---")
        print(content)
        print("--- END ERROR LOG ---")
except Exception as e:
    print(f"Failed to read utf-16: {e}")
    try:
        with open("fmp_error.log", "r", encoding="utf-8") as f:
            content = f.read()
            print("--- START ERROR LOG ---")
            print(content)
            print("--- END ERROR LOG ---")
    except Exception as e:
        print(f"Failed to read utf-8: {e}")
