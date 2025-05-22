import json

with open("available-seats.json", "r") as file:
    data: dict = json.load(file)

total_seats = 0

for block, seats in data.items():
    print(f"Block: {block}")
    print(f"Number of seats: {len(seats)}")
    total_seats += len(seats)
    print("========")

print(f"Total number of seats: {total_seats}")
