# generate_dataset.py
import pandas as pd
import random

products = ["Washing Machine", "Refrigerator", "Air Conditioner", "Microwave Oven"]
washing_issues = [
    "water not filling", "machine not spinning", "clothes remain wet",
    "leakage during wash", "door not locking", "drum not rotating", 
    "vibration while running", "stuck on rinse cycle", "error code E2"
]
refrigerator_issues = [
    "not cooling properly", "ice not forming", "water leakage", "compressor noisy",
    "light not working", "door not closing", "fridge too warm", "bad smell inside"
]
ac_issues = [
    "not cooling", "remote not working", "leaking water", "fan not rotating",
    "making loud noise", "not switching on", "airflow weak", "hot air coming out"
]
microwave_issues = [
    "not heating", "stops midway", "plate not rotating", "burning smell",
    "door not closing", "buttons not responding", "display not working"
]

data = []
cid = 1
for _ in range(500):
    product = random.choice(products)
    if product == "Washing Machine":
        text = random.choice(washing_issues)
    elif product == "Refrigerator":
        text = random.choice(refrigerator_issues)
    elif product == "Air Conditioner":
        text = random.choice(ac_issues)
    else:
        text = random.choice(microwave_issues)
    data.append([cid, product, text])
    cid += 1

df = pd.DataFrame(data, columns=["complaint_id", "product", "complaint_text"])
df.to_csv("data/complaints.csv", index=False)
print("✅ Generated 500 complaint records in data/complaints.csv")
