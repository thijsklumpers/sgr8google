import os
import csv
import time
import re
import json
import urllib.parse
from collections import defaultdict
from google.oauth2 import service_account
from googleapiclient.discovery import build

start_time = time.time()

# Load configuration from config.json
config_path = os.path.join(os.path.dirname(__file__), '../../service/config.json')
with open(config_path, 'r') as config_file:
    config = json.load(config_file)

SERVICE_ACCOUNT_FILE = config.get('SERVICE_ACCOUNT_FILE')
DELEGATED_ADMIN_EMAIL = config.get('DELEGATED_ADMIN_EMAIL')

# Construct the full path to the service account file
service_account_file_path = os.path.join(os.path.dirname(__file__), '../../service', SERVICE_ACCOUNT_FILE)

# Define base_dir for your CSV files
base_dir = os.path.dirname(__file__)

# Define the scope and credentials
SCOPES = [
    'https://www.googleapis.com/auth/admin.directory.user',
    'https://www.googleapis.com/auth/admin.directory.orgunit'
]

credentials = service_account.Credentials.from_service_account_file(
    service_account_file_path, scopes=SCOPES)
credentials = credentials.with_subject(DELEGATED_ADMIN_EMAIL)

service = build('admin', 'directory_v1', credentials=credentials)

# Path to your CSV file
csv_file_path = os.path.join(base_dir, '../../csv/user/split/split_leerling_google_users.csv')

# Initialize dictionaries to track users per domain (school)
moved_users_count_per_school = defaultdict(int)
ous_created_per_school = defaultdict(list)
all_domains = set()  # To store all domains found in the CSV

# Initialize a set to store all OUs that need to be checked or created
required_ous = defaultdict(set)

def sanitize_ou_name(ou_name, allow_period=False):
    """
    Sanitize the OU name to remove or replace any invalid characters.
    This function will keep periods (if allow_period is True), spaces, letters, and numbers.
    """
    if not ou_name:
        return None  # If the OU name is empty, return None to avoid creating an invalid OU

    # Remove invalid characters from OU names (keep periods if specified)
    if allow_period:
        sanitized_ou_name = re.sub(r'[^\w\s.-]', '', ou_name)  # Allow periods, spaces, letters, and numbers
    else:
        sanitized_ou_name = re.sub(r'[^\w\s]', '', ou_name)  # Allow only letters, numbers, and spaces

    sanitized_ou_name = sanitized_ou_name.strip()  # Strip leading and trailing spaces
    return sanitized_ou_name if sanitized_ou_name else None  # Return sanitized name or None if empty

def ensure_ou_path_exists(ou_path, domain):
    """
    Ensure that the entire OU path exists, creating any missing OUs.
    :param ou_path: The organizational unit path (e.g., '/@domain/1.Users/1.4Leerling/Department').
    :param domain: The domain name for tracking OU creation.
    """
    parts = ou_path.strip('/').split('/')
    current_path = ''
    for part in parts:
        current_path += f'/{part}'
        try:
            encoded_current_path = urllib.parse.quote(current_path, safe='')
            service.orgunits().get(customerId='my_customer', orgUnitPath=encoded_current_path).execute()
            # OU exists
        except Exception as e:
            if 'not found' in str(e).lower():
                # Parent OU exists, create this OU
                parent_path = '/' + '/'.join(current_path.strip('/').split('/')[:-1])
                ou_name = current_path.strip('/').split('/')[-1]
                create_ou(ou_name, parent_path, domain)
            else:
                print(f"Error checking OU '{current_path}': {e}")

def create_ou(ou_name, parent_ou, domain):
    """
    Create a new organizational unit under the specified parent OU.
    :param ou_name: The name of the OU to create.
    :param parent_ou: The parent OU path.
    :param domain: The domain name for tracking OU creation.
    :return: The newly created OU.
    """
    ou_name = sanitize_ou_name(ou_name, allow_period=True)

    if not ou_name:
        print(f"Invalid OU name for '{parent_ou}/{ou_name}', skipping OU creation.")
        return None

    body = {
        "name": ou_name,
        "parentOrgUnitPath": parent_ou
    }
    try:
        created_ou = service.orgunits().insert(customerId='my_customer', body=body).execute()
        print(f"Created OU '{ou_name}' under '{parent_ou}'")
        ous_created_per_school[domain].append(f"{parent_ou}/{ou_name}")
        return created_ou
    except Exception as e:
        if 'duplicate' in str(e).lower() or 'already exists' in str(e).lower():
            print(f"OU '{ou_name}' under '{parent_ou}' already exists.")
        else:
            print(f"Failed to create OU '{ou_name}' under '{parent_ou}': {e}")
        return None

# Step 1: Read the CSV file and gather user information
users_to_process = []

with open(csv_file_path, mode='r') as file:
    csv_reader = csv.DictReader(file)

    for row in csv_reader:
        email = row['userPrincipalName']
        domain = email.split('@')[1]  # This represents the school in your case
        department = row.get('department', '')  # Get the department (class) information

        sanitized_department = sanitize_ou_name(department)
        if sanitized_department:
            required_ous[domain].add(sanitized_department)
            users_to_process.append((email, domain, sanitized_department))
        else:
            print(f"Skipping user {email} due to invalid department.")

        all_domains.add(domain)

# Step 2: Check and create all required OUs before moving users
for domain, departments in required_ous.items():
    for department in departments:
        ou_path = f'/@{domain}/1.Users/1.4Leerling/{department}'
        ensure_ou_path_exists(ou_path, domain)

# Step 3: Move users to their respective OUs if they are not already there
for email, domain, department in users_to_process:
    target_ou = f'/@{domain}/1.Users/1.4Leerling/{department}'
    try:
        user = service.users().get(userKey=email).execute()
        current_ou = user.get('orgUnitPath', '')  # Get the current OU path

        # Only move the user if they are not already in the target OU
        if current_ou != target_ou:
            user_body = {
                "orgUnitPath": target_ou
            }
            service.users().update(userKey=email, body=user_body).execute()
            print(f'Successfully moved {email} to {target_ou}')
            moved_users_count_per_school[domain] += 1
        else:
            print(f'{email} is already in the correct OU. No action taken.')

    except Exception as e:
        print(f'Failed to process {email}: {e}')

# Output the final breakdown per school (domain)
print("\nBreakdown of moved users per school:\n")
for domain in all_domains:
    moved_count = moved_users_count_per_school.get(domain, 0)
    ous_created = ous_created_per_school.get(domain, [])

    print(f'School (Domain): {domain}')
    print(f'  Total moved to "Leerling" OUs: {moved_count}')

    if ous_created:
        print(f'  OUs created: {", ".join(ous_created)}')
    else:
        print(f'  No OUs created.')

    print('-' * 50)

print(f"Process finished --- {time.time() - start_time} seconds ---")