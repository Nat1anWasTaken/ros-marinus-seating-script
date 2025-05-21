import csv  # Added
import json  # Added
from collections import OrderedDict
from datetime import datetime


# Helper function to parse timestamps from the CSV
def parse_timestamp(ts_str):
    """
    Parses a timestamp string in various possible formats
    into a datetime object.
    Handles:
    1. 'YYYY/MM/DD AM/PM HH:MM:SS' (e.g., "2025/5/14 下午 5:51:07")
    2. 'YYYY/MM/DD HH:MM:SS' (24-hour format, e.g., "2025/05/19 17:51:07")
    """
    if (
        not ts_str
        or ts_str.strip().lower() == "invalid timestamp in source"
        or ts_str.strip().lower() == "n/a (unassigned)"
    ):  # Added check for placeholder strings
        return None  # Return None for empty or placeholder strings

    try:
        # Attempt 1: Parse with Chinese AM/PM
        date_part, time_with_ampm = ts_str.split(" ", 1)
        parts = time_with_ampm.split(" ", 1)
        if len(parts) == 2:
            ampm_indicator, time_part = parts
            dt_obj = datetime.strptime(f"{date_part} {time_part}", "%Y/%m/%d %I:%M:%S")
            if ampm_indicator == "下午" and dt_obj.hour < 12:
                dt_obj = dt_obj.replace(hour=dt_obj.hour + 12)
            elif ampm_indicator == "上午" and dt_obj.hour == 12:  # Midnight case
                dt_obj = dt_obj.replace(hour=0)
            return dt_obj
        else:
            # If not two parts after splitting time_with_ampm, it might be 24-hour format
            # Fall through to the next try-except block
            pass
    except ValueError:
        # If first format fails, try the 24-hour format
        pass

    try:
        # Attempt 2: Parse 24-hour format
        return datetime.strptime(ts_str, "%Y/%m/%d %H:%M:%S")
    except ValueError as e:
        print(
            f"Error: Failed to parse allocation time '{ts_str}' with known formats: {e}"
        )
        return datetime.max  # Return datetime.max if all parsing attempts fail


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


def load_preserved_seats(filepath="preserved-seats.csv"):
    """Loads preserved seat assignments from a CSV file."""
    preserved = []
    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    # Allocation Time might be empty if it's from an older export or manually created
                    timestamp_str = row.get("Allocation Time", "").strip()
                    alloc_time = (
                        parse_timestamp(timestamp_str)
                        if timestamp_str
                        else None  # Handle empty timestamp
                    )

                    preserved.append(
                        {
                            "block": row["Block"]
                            .strip()
                            .replace("Block ", "block-"),  # Normalize block name
                            "seat_number": row["Seat Number"].strip(),
                            "member_name": row.get("Member Name", "").strip(),
                            "ticket_holder_name": row["Ticket Holder Name"].strip(),
                            "pickup_method": row.get("Pickup Method", "").strip(),
                            "allocation_time": alloc_time,  # Store as datetime or None
                        }
                    )
                except KeyError as e:
                    print(
                        f"Warning: Skipping row in '{filepath}' due to missing column: {e} (Row: {row})"
                    )
                except (
                    ValueError
                ) as e:  # Catch parsing errors for timestamp specifically
                    print(
                        f"Warning: Skipping row in '{filepath}' due to timestamp parse error: {e} (Row: {row})"
                    )
        return preserved
    except FileNotFoundError:
        print(
            f"Info: Preserved seats file '{filepath}' not found. Continuing without preserved seats."
        )
        return []
    except Exception as e:
        print(f"Error: An error occurred while loading '{filepath}': {e}")
        return []


def load_audience_requests(filepath="audiences.csv"):
    """Loads and sorts audience requests from a CSV file."""
    requests = []
    try:
        with open(
            filepath, "r", encoding="utf-8-sig"
        ) as f:  # Use utf-8-sig to handle potential BOM
            reader = csv.DictReader(f)  # Use DictReader
            # No need to skip header manually, DictReader handles it.

            # Define expected header names for clarity and validation (optional)
            # expected_headers = ["時間戳記", "您的身分是", "索票人姓名", "票券張數", "團員姓名", "取票人姓名", "索票方式"]
            # actual_headers = reader.fieldnames
            # if not all(header in actual_headers for header in expected_headers):
            #     print(f"Warning: CSV headers do not match expected. Found: {actual_headers}")
            #     # Decide if you want to proceed or raise an error

            for i, row in enumerate(reader):
                try:
                    # Access columns by name
                    timestamp_str = row["時間戳記"].strip()
                    member_name = row[
                        "團員姓名"
                    ].strip()  # Corrected column name based on audiences.csv
                    ticket_holder_name = row[
                        "取票人姓名"
                    ].strip()  # Corrected column name
                    if not ticket_holder_name:
                        ticket_holder_name = member_name

                    num_tickets_str = row["票券張數"].strip()  # Corrected column name
                    if not num_tickets_str:
                        num_tickets = 0
                    else:
                        num_tickets = int(num_tickets_str)

                    if num_tickets <= 0:
                        continue

                    pickup_method = row["索票方式"].strip()

                    requests.append(
                        {
                            "timestamp": parse_timestamp(timestamp_str),
                            "member_name": member_name,
                            "ticket_holder_name": ticket_holder_name,
                            "num_tickets": num_tickets,
                            "pickup_method": pickup_method,
                            "original_row_num": i
                            + 2,  # For debugging (i+1 for DictReader header, +1 for 1-based)
                        }
                    )
                except ValueError as e:
                    print(
                        f"Warning: Skipping row {i + 2} due to data conversion error (file {filepath}): {e} (original data: {row})"
                    )
                except KeyError as e:
                    print(
                        f"Warning: Skipping row {i + 2} due to missing column (file {filepath}): {e} (original data: {row})"
                    )
                except IndexError:  # Should be less likely with DictReader unless rows are truly malformed
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


def assign_seats(
    audience_requests, available_seats_ordered, preserved_seats=None
):  # Added preserved_seats
    """Assigns seats to audience requests, considering preserved seats."""
    assigned_seats_by_block = OrderedDict()
    for (
        block_name_key_init
    ) in available_seats_ordered.keys():  # Initialize for all available blocks
        assigned_seats_by_block[block_name_key_init] = []

    # Step 1: Account for preserved seats - remove from available and add to final assignments
    # Also, build a lookup for checking if audience requests are covered by these.
    # Key: (ticket_holder_name, allocation_time_datetime_object)
    # Value: count of tickets preserved for this key
    preserved_tickets_lookup = {}

    if preserved_seats:
        for ps in preserved_seats:
            block_name = ps["block"]
            seat_num = ps["seat_number"]

            # Add to assigned_seats_by_block to include in output
            # This ensures preserved seats are always in the "assigned" list.
            assigned_seats_by_block.setdefault(block_name, []).append(
                {
                    "seat_number": seat_num,
                    "member_name": ps["member_name"],
                    "ticket_holder_name": ps["ticket_holder_name"],
                    "pickup_method": ps["pickup_method"],
                    "timestamp": ps[
                        "allocation_time"
                    ],  # This is the original allocation time
                }
            )

            # Remove from available_seats_ordered
            if block_name in available_seats_ordered:
                if seat_num in available_seats_ordered[block_name]:
                    available_seats_ordered[block_name].remove(seat_num)
                else:  # Seat not in the specific list of available seats for that block
                    print(
                        f"Warning: Preserved seat {seat_num} in {block_name} not found in available seat list for that block. It might have been removed or changed, or block name mismatch."
                    )
            else:  # Block itself not in available_seats_ordered
                print(
                    f"Warning: Block {block_name} for preserved seat {seat_num} not found in available seat blocks."
                )

            # Populate the lookup for request matching
            # Only consider preserved seats with valid allocation times for this matching logic
            if ps["allocation_time"] and ps["allocation_time"] != datetime.max:
                key = (ps["ticket_holder_name"], ps["allocation_time"])
                preserved_tickets_lookup[key] = preserved_tickets_lookup.get(key, 0) + 1

    unassigned_requests = []

    # Step 2: Process audience requests
    for request in audience_requests:
        num_tickets_needed = request["num_tickets"]
        request_holder_name = request["ticket_holder_name"]
        request_timestamp = request["timestamp"]  # This is from audience_requests

        is_fulfilled_by_preserved = False
        # Only attempt to match if the audience request timestamp is valid
        if request_timestamp and request_timestamp != datetime.max:
            request_match_key = (request_holder_name, request_timestamp)

            if (
                request_match_key in preserved_tickets_lookup
                and preserved_tickets_lookup[request_match_key] >= num_tickets_needed
            ):
                # This request is considered fulfilled by preserved seats.
                preserved_tickets_lookup[request_match_key] -= (
                    num_tickets_needed  # "Use up" these preserved tickets
                )
                is_fulfilled_by_preserved = True
                print(
                    f"Info: Request for {request_holder_name} ({num_tickets_needed} tickets, Time: {request_timestamp.strftime('%Y/%m/%d %H:%M:%S') if request_timestamp else 'N/A'}) "
                    f"is covered by preserved seats. Skipping new assignment."
                )

        if is_fulfilled_by_preserved:
            continue  # Move to the next audience request

        # If not fulfilled by preserved, proceed with normal assignment logic
        assigned_for_this_request_newly = False
        for block_name, seats_in_block in available_seats_ordered.items():
            if len(seats_in_block) >= num_tickets_needed:
                temp_assigned_seats_info = []
                for _ in range(num_tickets_needed):
                    seat = seats_in_block.pop(0)
                    seat_info = {
                        "seat_number": seat,
                        "member_name": request["member_name"],
                        "ticket_holder_name": request_holder_name,
                        "pickup_method": request["pickup_method"],
                        "timestamp": request_timestamp,  # The audience request's timestamp
                    }
                    temp_assigned_seats_info.append(seat_info)

                # Ensure block_name exists in assigned_seats_by_block before extending
                assigned_seats_by_block.setdefault(block_name, []).extend(
                    temp_assigned_seats_info
                )
                assigned_for_this_request_newly = True
                break

        if not assigned_for_this_request_newly:
            unassigned_requests.append(request)
            # print(f"Info: Could not find enough seats in the same block for '{request_holder_name}' (Time: {request_timestamp.strftime('%Y/%m/%d %H:%M:%S') if request_timestamp and request_timestamp != datetime.max else 'Invalid/Max'}) for {num_tickets_needed} tickets.")

    return assigned_seats_by_block, unassigned_requests, available_seats_ordered


def format_and_print_results(assigned_seats_by_block, unassigned_requests, remaining_seats_by_block):
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

    print("\n--- Remaining Available Seats ---")
    total_remaining_seats = 0
    if remaining_seats_by_block:
        for block_name, seats in remaining_seats_by_block.items():
            count = len(seats)
            total_remaining_seats += count
            block_display_name = block_name.replace("block-", "Block ")
            print(f"{block_display_name}: {count} seat(s) remaining")
        print(f"\nTotal remaining seats: {total_remaining_seats}")
    else:
        print("No remaining seats information available (or all seats taken).")


def main():
    """Main function to execute the seating script."""
    print("Starting seating script execution...\n")

    available_seats_file = "available-seats.json"  # Changed filename
    audience_file = "audiences.csv"
    preserved_seats_file = "preserved-seats.csv"  # Added

    # 1. Load available seats
    print(f"Reading available seats from '{available_seats_file}'...")
    available_seats = load_available_seats(available_seats_file)
    if not available_seats:
        print("Could not read any available seats. Script terminated.")
        return

    # Load preserved seats (before audience requests, after available seats)
    print(f"\nReading preserved seats from '{preserved_seats_file}'...")
    preserved_seats = load_preserved_seats(preserved_seats_file)
    if preserved_seats:
        print(f"Successfully loaded {len(preserved_seats)} preserved seat assignments.")

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
    assigned_seats, unassigned_requests, remaining_seats = assign_seats(
        audience_requests,
        available_seats,
        preserved_seats,  # Pass preserved_seats
    )
    print("Seat assignment complete.\n")

    # 4. Format and print results
    format_and_print_results(assigned_seats, unassigned_requests, remaining_seats)

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
                "Number of Tickets",
                "Pickup Method",
                "Allocation Time",  # Ensure this is the correct header for your needs
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            # Write assigned seats (includes new and preserved)
            for block_name, assignments in assigned_seats_by_block.items():
                block_display_name = block_name.replace("block-", "Block ")
                for assignment in assignments:
                    alloc_time_str = ""
                    timestamp = assignment.get("timestamp")
                    # Check if timestamp is None or datetime.max (our error placeholder)
                    if timestamp and timestamp != datetime.max:
                        alloc_time_str = timestamp.strftime("%Y/%m/%d %H:%M:%S")
                    elif timestamp == datetime.max:
                        alloc_time_str = (
                            "Invalid Timestamp in Source"  # Or "" if you prefer
                        )

                    writer.writerow(
                        {
                            "Block": block_display_name,
                            "Seat Number": assignment["seat_number"],
                            "Member Name": assignment.get("member_name", ""),
                            "Ticket Holder Name": assignment["ticket_holder_name"],
                            "Number of Tickets": 1,  # Each assigned row is 1 ticket
                            "Pickup Method": assignment.get("pickup_method", ""),
                            "Allocation Time": alloc_time_str,
                        }
                    )

            # Write unassigned requests
            if unassigned_requests:
                for req in unassigned_requests:
                    writer.writerow(  # Added writerow for unassigned requests
                        {
                            "Block": "N/A (Unassigned)",
                            "Seat Number": "N/A",
                            "Member Name": req.get("member_name", ""),
                            "Ticket Holder Name": req["ticket_holder_name"],
                            "Number of Tickets": req["num_tickets"],
                            "Pickup Method": req.get("pickup_method", ""),
                            "Allocation Time": "N/A (Unassigned)",  # Or req['timestamp'] if you want request time
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
