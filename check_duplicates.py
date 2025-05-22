import json
from collections import Counter

with open('available-seats.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

all_seats = []
for seats in data.values():
    all_seats.extend(seats)

seat_counts = Counter(all_seats)
duplicates = [seat for seat, count in seat_counts.items() if count > 1]

if duplicates:
    print('Duplicate seats found:')
    for seat in duplicates:
        print(f'{seat} (count: {seat_counts[seat]})')
else:
    print('No duplicate seats found.')
