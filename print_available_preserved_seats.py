import csv
import json

# Read available-seats.json
with open("available-seats.json", encoding="utf-8") as f:
    available = json.load(f)

# Check for duplicate seat numbers in available-seats.json
seen = set()
duplicates = set()
for seats in available.values():
    for seat in seats:
        if seat in seen:
            duplicates.add(seat)
        else:
            seen.add(seat)
if duplicates:
    raise ValueError(
        f"Duplicate seat numbers found in available-seats.json: {', '.join(sorted(duplicates))}"
    )

# Flatten all available seat numbers into a set
available_seats = seen

# Read preserved-seats.csv and collect all preserved seat numbers
preserved_seats = set()
with open("preserved-seats.csv", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        preserved_seats.add(row["Seat Number"])

# Print all available seats that are not preserved
for seat in sorted(available_seats):
    if seat not in preserved_seats:
        print(f"Available (not preserved) seat: {seat}")
