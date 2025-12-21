try:
    with open("alternatives.log", "r", encoding="utf-16") as f:
        print(f.read())
except:
    with open("alternatives.log", "r", encoding="utf-8") as f:
        print(f.read())
