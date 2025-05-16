import csv
import json
from collections import OrderedDict
from datetime import datetime


# Helper function to parse timestamps from the CSV
def parse_timestamp(ts_str):
    """
    Parses a timestamp string in the format 'YYYY/MM/DD AM/PM HH:MM:SS'
    into a datetime object.
    Example: "2025/5/14 下午 5:51:07" (Note: AM/PM indicator is in Chinese in the example, will be handled)
    """
    try:
        date_part, time_with_ampm = ts_str.split(" ", 1)

        parts = time_with_ampm.split(" ", 1)
        if len(parts) == 2:
            ampm_indicator, time_part = parts
        else:
            # This case should ideally not happen based on consistent CSV data
            raise ValueError(
                f"Timestamp format unexpected after date: {time_with_ampm}"
            )

        dt_obj = datetime.strptime(f"{date_part} {time_part}", "%Y/%m/%d %I:%M:%S")

        if ampm_indicator == "下午" and dt_obj.hour < 12:
            dt_obj = dt_obj.replace(hour=dt_obj.hour + 12)
        elif (
            ampm_indicator == "上午" and dt_obj.hour == 12
        ):  # Midnight case: 12 AM is 00 hours
            dt_obj = dt_obj.replace(hour=0)
        return dt_obj
    except ValueError as e:
        print(f"Error: Failed to parse allocation time '{ts_str}': {e}")
        # Return a far future date to sort problematic entries last, or handle as error
        return datetime.max


def load_available_seats(filepath="available-seats.json"):  # Changed default filename
    """Loads available seats from a JSON file."""  # Updated docstring
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)  # Use json.load

        # Sort block names by the number in their name (e.g., "block-1", "block-2")
        sorted_block_names = sorted(data.keys(), key=lambda k: int(k.split("-")[1]))

        available_seats_ordered = OrderedDict()
        for block_name in sorted_block_names:
            available_seats_ordered[block_name] = list(
                data[block_name]
            )  # Ensure it's a list
        return available_seats_ordered
    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found.")
        return OrderedDict()
    except Exception as e:
        print(f"Error: An error occurred while loading or parsing '{filepath}': {e}")
        return OrderedDict()


def load_audience_requests(filepath="audiences.csv"):
    """Loads and sorts audience requests from a CSV file."""
    requests = []
    try:
        with open(
            filepath, "r", encoding="utf-8-sig"
        ) as f:  # Use utf-8-sig to handle potential BOM
            reader = csv.reader(f)
            next(reader)  # Skip header, header is not used

            # Column indices (based on the provided CSV structure)
            # Allocation Time: 0, Your Identity: 1, Member Name: 2, Ticket Holder Name: 3, Copiable: 4, Instrument: 5, Number of Tickets: 6, Pickup Method: 7
            idx_timestamp = 0
            idx_member_name = 2
            idx_ticket_holder = 3
            idx_num_tickets = 6
            idx_pickup_method = 7

            for i, row in enumerate(reader):
                if not row or len(row) <= max(
                    idx_timestamp,
                    idx_member_name,
                    idx_ticket_holder,
                    idx_num_tickets,
                    idx_pickup_method,
                ):
                    print(
                        f"Warning: Skipping improperly formatted row {i + 2} (file {filepath}): {row}"
                    )
                    continue
                try:
                    timestamp_str = row[idx_timestamp].strip()
                    member_name = row[idx_member_name].strip()
                    ticket_holder_name = row[idx_ticket_holder].strip()
                    if not ticket_holder_name:
                        ticket_holder_name = member_name

                    num_tickets_str = row[idx_num_tickets].strip()
                    if not num_tickets_str:
                        # print(f"Warning: Number of tickets is empty for row {i+2}, treating as 0 tickets.")
                        num_tickets = 0
                    else:
                        num_tickets = int(num_tickets_str)

                    if (
                        num_tickets <= 0
                    ):  # Skip requests for 0 or invalid number of tickets
                        continue

                    pickup_method = row[idx_pickup_method].strip()

                    requests.append(
                        {
                            "timestamp": parse_timestamp(timestamp_str),
                            "member_name": member_name,
                            "ticket_holder_name": ticket_holder_name,
                            "num_tickets": num_tickets,
                            "pickup_method": pickup_method,
                            "original_row_num": i + 2,  # For debugging
                        }
                    )
                except ValueError as e:
                    print(
                        f"Warning: Skipping row {i + 2} due to data conversion error (file {filepath}): {e} (original data: {row})"
                    )
                except IndexError:
                    print(
                        f"Warning: Skipping row {i + 2} due to insufficient columns (file {filepath}): {row}"
                    )

        requests.sort(key=lambda r: r["timestamp"])
        return requests
    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found.")
        return []
    except Exception as e:
        print(f"Error: An error occurred while loading or parsing '{filepath}': {e}")
        return []


def assign_seats(audience_requests, available_seats_ordered):
    """Assigns seats to audience requests."""
    assigned_seats_by_block = OrderedDict()
    for block_name in available_seats_ordered.keys():
        assigned_seats_by_block[block_name] = []

    unassigned_requests = []

    for request in audience_requests:
        num_tickets_needed = request["num_tickets"]
        assigned_for_this_request = False

        for block_name, seats_in_block in available_seats_ordered.items():
            if len(seats_in_block) >= num_tickets_needed:
                temp_assigned_seats_info = []
                for _ in range(num_tickets_needed):
                    seat = seats_in_block.pop(
                        0
                    )  # Take a seat from the front of this block
                    seat_info = {
                        "seat_number": seat,
                        "member_name": request["member_name"],
                        "ticket_holder_name": request["ticket_holder_name"],
                        "pickup_method": request["pickup_method"],
                        "timestamp": request["timestamp"],  # Add timestamp
                    }
                    temp_assigned_seats_info.append(seat_info)

                assigned_seats_by_block[block_name].extend(temp_assigned_seats_info)
                assigned_for_this_request = True
                break  # Finished assigning for this request, process next request

        if not assigned_for_this_request:
            unassigned_requests.append(request)
            # print(f"Info: Could not find enough seats in the same block for '{request['ticket_holder_name']}' (Time: {request['timestamp']}) for {num_tickets_needed} tickets.")

    return assigned_seats_by_block, unassigned_requests


def format_and_print_results(assigned_seats_by_block, unassigned_requests):
    """Formats and prints the seating assignment results."""
    print("--- Seating Assignment Results ---")
    any_seat_assigned = False
    for block_name, assignments in assigned_seats_by_block.items():
        if not assignments:
            continue
        any_seat_assigned = True
        block_display_name = block_name.replace("block-", "Block ")
        print(f"\n{block_display_name} ======")
        for assignment in assignments:
            output_str = f"{assignment['seat_number']}: "

            if assignment["member_name"]:
                output_str += f"Member: {assignment['member_name']} "

            output_str += f"Ticket Holder: {assignment['ticket_holder_name']}"

            if assignment["pickup_method"]:
                output_str += f" Pickup Method: {assignment['pickup_method']}"

            if "timestamp" in assignment and assignment["timestamp"]:
                ts_str = assignment["timestamp"].strftime("%Y/%m/%d %H:%M:%S")
                output_str += f" Allocation Time: {ts_str}"

            print(output_str)

    if not any_seat_assigned and not unassigned_requests:
        print(
            "No seats were assigned, and no unassigned requests (possibly all requests were for 0 tickets or no valid requests/seats)."
        )
    elif not any_seat_assigned and unassigned_requests:
        print("No seats were successfully assigned.")

    if unassigned_requests:
        print("\n--- Requests That Could Not Be Seated ---")
        for req in unassigned_requests:
            print(
                f"- Ticket Holder: {req['ticket_holder_name']}, Tickets: {req['num_tickets']}, Time: {req['timestamp'].strftime('%Y/%m/%d %H:%M:%S')} (Original CSV Row: {req.get('original_row_num', 'N/A')})"
            )


def main():
    """Main function to execute the seating script."""
    print("Starting seating script execution...\n")

    available_seats_file = "available-seats.json"  # Changed filename
    audience_file = "audiences.csv"

    # 1. Load available seats
    print(f"Reading available seats from '{available_seats_file}'...")
    available_seats = load_available_seats(available_seats_file)
    if not available_seats:
        print("Could not read any available seats. Script terminated.")
        return

    # 2. Load audience requests
    print(f"\nReading audience requests from '{audience_file}'...")
    audience_requests = load_audience_requests(audience_file)
    if not audience_requests:
        print(
            "Could not read any valid audience requests (or all requests were for 0 tickets). Script terminated."
        )
        return

    # 3. Assign seats
    print("\nAssigning seats...")
    assigned_seats, unassigned_requests = assign_seats(
        audience_requests, available_seats
    )
    print("Seat assignment complete.\n")

    # 4. Format and print results
    format_and_print_results(assigned_seats, unassigned_requests)

    # 5. Ask for and export results to CSV
    output_csv_filename = input(
        "\nPlease enter the filename for the CSV export (e.g., output.csv): "
    ).strip()
    if not output_csv_filename:
        print("No valid filename provided. CSV export will be skipped.")
    else:
        if not output_csv_filename.lower().endswith(".csv"):
            output_csv_filename += ".csv"
        print(f"\nExporting results to '{output_csv_filename}'...")
        export_results_to_csv(assigned_seats, unassigned_requests, output_csv_filename)
        print(f"Results successfully exported to '{output_csv_filename}'.")

    print("\nScript execution finished.")


def export_results_to_csv(assigned_seats_by_block, unassigned_requests, filename):
    """Exports the seating results to a CSV file."""
    try:
        with open(filename, "w", newline="", encoding="utf-8-sig") as csvfile:
            fieldnames = [
                "Block",
                "Seat Number",
                "Member Name",
                "Ticket Holder Name",
                "Number of Tickets",  # Added for unassigned requests
                "Pickup Method",
                "Allocation Time",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            # Write assigned seats
            for block_name, assignments in assigned_seats_by_block.items():
                block_display_name = block_name.replace("block-", "Block ")
                for assignment in assignments:
                    writer.writerow(
                        {
                            "Block": block_display_name,
                            "Seat Number": assignment["seat_number"],
                            "Member Name": assignment.get("member_name", ""),
                            "Ticket Holder Name": assignment["ticket_holder_name"],
                            "Number of Tickets": 1,  # Each assigned seat counts as one
                            "Pickup Method": assignment.get("pickup_method", ""),
                            "Allocation Time": assignment["timestamp"].strftime(
                                "%Y/%m/%d %H:%M:%S"
                            )
                            if assignment.get("timestamp")
                            else "",
                        }
                    )

            # Write unassigned requests
            if unassigned_requests:
                for req in unassigned_requests:
                    writer.writerow(
                        {
                            "Block": "N/A (Unassigned)",
                            "Seat Number": "N/A",
                            "Member Name": req.get("member_name", ""),
                            "Ticket Holder Name": req["ticket_holder_name"],
                            "Number of Tickets": req["num_tickets"],
                            "Pickup Method": req.get("pickup_method", ""),
                            "Allocation Time": req["timestamp"].strftime(
                                "%Y/%m/%d %H:%M:%S"
                            )
                            if req.get("timestamp")
                            else "",
                        }
                    )
    except IOError:
        print(
            f"Error: Could not write to file '{filename}'. Please check permissions or path."
        )
    except Exception as e:
        print(
            f"Error: An unknown error occurred while exporting CSV to '{filename}': {e}"
        )


if __name__ == "__main__":
    main()
