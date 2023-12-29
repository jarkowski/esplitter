import json
import sys

# Read the JSON file
with open('data.json', mode='r') as file:
    # Load the data from the JSON file
    data = json.load(file)
    
    # Extract the MeterData and UserData from the JSON
    meter_data = data['MeterData']
    user_data = {user['Name']: user['Share'] for user in data['UserData']}
    start_meter = data['GeneralData']['StartMeterThisYear']
    end_meter = data['GeneralData']['EndMeterThisYear']
    year = data['GeneralData']['Year']

import json

def is_overlapping(meter_data):
    # Sorting by CheckInMeter to compare adjacent entries
    sorted_data = sorted(meter_data, key=lambda x: x['CheckInMeter'])
    
    # Iterate through sorted_data and check for overlapping ranges
    for i in range(len(sorted_data) - 1):
        # Adjusting condition to allow for consecutive readings to be the same
        if sorted_data[i]['CheckOutMeter'] > sorted_data[i + 1]['CheckInMeter']:
            return True  # Overlap found
    return False  # No overlaps or consecutive readings match exactly


def perform_consistency_checks(data):
    # Extracting relevant sections from the JSON data
    general_data = data.get('GeneralData', {})
    meter_data = data.get('MeterData', [])
    user_data = data.get('UserData', [])

    # Extracting specific general data points
    start_meter_year = general_data.get('StartMeterThisYear', 0)
    end_meter_year = general_data.get('EndMeterThisYear', 0)
    user_names = {user['Name'] for user in user_data}  # Set of all names in UserData

    # Consistency checks
    checks = {
        "meter_range_check": all(start_meter_year <= entry['CheckInMeter'] <= end_meter_year and
                                 start_meter_year <= entry['CheckOutMeter'] <= end_meter_year
                                 for entry in meter_data),
        "meter_overlap_check": not is_overlapping(meter_data),
        "user_names_check": all(entry['Name'] in user_names for entry in meter_data)
    }

    return checks

# Function to display the checks in a user-friendly manner and terminate script if any check fails
def perform_and_display_checks(data):
    checks_result = perform_consistency_checks(data)
    check_messages = [
        "All MeterData datasets are between StartMeterThisYear and EndMeterThisYear",
        "No overlappings in MeterData",
        "MeterData contains only known users"
    ]
    for i, (check, result) in enumerate(checks_result.items(), start=1):
        status = "OK" if result else "FAIL"
        print(f"Check {i} of {len(checks_result)}: {check_messages[i-1]} - {status}")
        if not result:
            sys.exit(f"Terminating script due to failed check: {check_messages[i-1]}")

print("================================================================================")
perform_and_display_checks(data)


# Calculate total units and unit price
total_units_this_year = end_meter - start_meter
TotalEnergyCostThisYearInEUR = data['GeneralData']['TotalEnergyCostThisYearInEUR']  # This should be the actual total cost for the year
unit_price = TotalEnergyCostThisYearInEUR / total_units_this_year if total_units_this_year else 0

# Initialize variables for meter units and general electric consumption
meter_units = {}
general_electric_units = 0
previous_meter = start_meter  # Start from the initial meter reading

# Calculate units used by each user and find gaps for General Electric
for entry in meter_data:
    # Calculate units used by the current entry
    units_used = entry['CheckOutMeter'] - entry['CheckInMeter']
    meter_units[entry['Name']] = meter_units.get(entry['Name'], 0) + units_used
    
    # Calculate any gap units before the current entry and add to General Electric
    gap_units = entry['CheckInMeter'] - previous_meter
    if gap_units > 0:
        general_electric_units += gap_units

    # Update the previous meter to the current checkout value for the next iteration
    previous_meter = entry['CheckOutMeter']

# Account for any remaining units after the last meter data entry
final_gap_units = end_meter - previous_meter
if final_gap_units > 0:
    general_electric_units += final_gap_units

# Assign the total General Electric units
meter_units['General Electric'] = general_electric_units

# Output the results for MeterData and calculate costs
print("--------------------------------------------------------------------------------")
print(f"Start of year meter: {start_meter} units")
print(f"End of year meter:  {end_meter} units")
print(f"Total for year {year}:  {end_meter - start_meter} units")
print(f"Price per unit: {round(unit_price,3)} EUR")
print("--------------------------------------------------------------------------------")

total_cost = 0
for name, units in meter_units.items():
    cost = units * unit_price
    total_cost += cost
    print(f"{name} used {units} units.")

print("--------------------------------------------------------------------------------")


# Extract the UserData from the JSON as a list of dictionaries
user_data = data.get('UserData', [])

# Assign the total General Electric units
meter_units['General Electric'] = general_electric_units

# Calculate and display each user's share of the General Electric cost

total_general_electric_units = meter_units['General Electric']
combined_cost = {}  # Initialize an empty dictionary to store the combined costs

for user in user_data:
    name = user['Name']
    share_percentage = user['Share']  # Share is assumed to be a whole number like 50 for 50%
    user_share_units = round((share_percentage / 100) * total_general_electric_units)  # Rounded to nearest whole number
    combined_cost[name] = user_share_units  # Add to the combined cost dictionary
    print(f"{name} is responsible for {user_share_units} units of General Electric.")

print("================================================================================")


# Initialize an empty dictionary for the summed costs
sum_units = {}
sum_cost_euro_should_be = {}

# Loop through each user in UserData to ensure all are included
for user in data['UserData']:
    name = user['Name']
    # Use .get() to retrieve and default to 0 if the user has no individual usage
    individual_units = meter_units.get(name, 0)
    # Retrieve and add the shared cost for each user
    shared_units = combined_cost.get(name, 0)
    # Sum the individual usage units and the share of General Electric units
    sum_units[name] = individual_units + shared_units

# Outputting the final cost for each user
for name, units in sum_units.items():
    sum_cost_euro_should_be[name] = round(units * unit_price,2)
    print(f"{name} total for year {year} is {units} units which is {sum_cost_euro_should_be[name]} EUR.")
    
print("--------------------------------------------------------------------------------")

sum_cost_euro_already_paid = {}

for user in data['UserData']:
    name = user['Name']
    share_percentage = user['Share']
    user_paid_already = TotalEnergyCostThisYearInEUR / 100 * share_percentage
    sum_cost_euro_already_paid[name] = user_paid_already
    print(f"SettleUp: {name} allready paid a share of {share_percentage} percent of {TotalEnergyCostThisYearInEUR} EUR, which is {user_paid_already} EUR.")

print("--------------------------------------------------------------------------------")

# Summing up the dictionaries
total_already_paid = sum(sum_cost_euro_already_paid.values())
total_should_be = sum(sum_cost_euro_should_be.values())

# Printing the totals
print(f"Total Already Paid: {total_already_paid} EUR")
print(f"Total Should Be:    {total_should_be} EUR")

print("--------------------------------------------------------------------------------")

# Calculate the difference for each person
payment_diff = {person: sum_cost_euro_should_be[person] - sum_cost_euro_already_paid[person]
                for person in sum_cost_euro_already_paid}

# Function to determine who needs to pay whom
def calculate_payments(payment_diff):
    # Split into payers (owe money) and receivers (owed money)
    payers = {k: v for k, v in payment_diff.items() if v < 0}
    receivers = {k: v for k, v in payment_diff.items() if v > 0}

    transactions = []

    # Until all debts are settled
    while payers and receivers:
        # Find the min debt and credit
        payer, pay_amt = min(payers.items(), key=lambda x: x[1])
        receiver, recv_amt = max(receivers.items(), key=lambda x: x[1])

        # Calculate the payment amount (the smaller of debt or credit)
        payment = min(-pay_amt, recv_amt)

        # Record the transaction
        transactions.append((payer, receiver, round(payment, 2)))

        # Update the amounts
        payers[payer] += payment
        receivers[receiver] -= payment

        # If the payer has settled all debts, remove them
        if payers[payer] == 0:
            del payers[payer]

        # If the receiver has been fully paid, remove them
        if receivers[receiver] == 0:
            del receivers[receiver]

    return transactions

# Calculate the difference for each person (Already paid amount - Should be amount)
payment_diff = {person: sum_cost_euro_already_paid[person] - sum_cost_euro_should_be[person]
                for person in sum_cost_euro_already_paid}

# Calculate and print transactions
transactions = calculate_payments(payment_diff)
for payer, receiver, amount in transactions:
    print(f"{payer} needs to pay {receiver} €{amount}")