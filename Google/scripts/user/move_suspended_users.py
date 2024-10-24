import os
import csv
import time
from collections import defaultdict
from google.oauth2 import service_account
from googleapiclient.discovery import build
from config_user import SERVICE_ACCOUNT_FILE, DELEGATED_ADMIN_EMAIL,base_dir

start_time = time.time()

# Define the scope and credentials
SCOPES = [
    'https://www.googleapis.com/auth/admin.directory.user',
    'https://www.googleapis.com/auth/admin.directory.orgunit'
]

credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
credentials = credentials.with_subject(DELEGATED_ADMIN_EMAIL)
service = build('admin', 'directory_v1', credentials=credentials, cache_discovery=False)

# Path to your CSV file
csv_file_path = os.path.join(base_dir, '../../csv/user/merged_data.csv')

# Initialize dictionaries to track suspended and moved users per domain (school)
suspended_users_count_per_school = defaultdict(int)
moved_users_count_per_school = defaultdict(int)
ous_created_per_school = defaultdict(list)
all_domains = set()  # To store all domains found in the CSV
ou_check_cache = {}  # To store the OU check results per domain

# Precheck: Only gather users who are suspended and not already in the suspended OU
suspended_users = []

with open(csv_file_path, mode='r') as file:
    csv_reader = csv.DictReader(file)
    for row in csv_reader:
        if row['suspended'].lower() == 'true':
            # Skip users who are already in the suspended OU
            if "/1.Users/1.6Suspended" not in row['orgUnitPath']:
                suspended_users.append(row)

# If no suspended users are found, output a message and skip further processing
if not suspended_users:
    print("No suspended users found or all users are already in the suspended OU.")
else:
    print(f"Processing {len(suspended_users)} suspended users...")  # Debugging print

def create_ou(ou_name, parent_ou, domain):
    """
    Create a new organizational unit under the specified parent OU.
    """
    body = {
        "name": ou_name,
        "parentOrgUnitPath": parent_ou
    }
    try:
        created_ou = service.orgunits().insert(customerId='my_customer', body=body).execute()
        ous_created_per_school[domain].append(f"{parent_ou}/{ou_name}")  # Track the created OU
        return created_ou
    except Exception as e:
        print(f"Failed to create OU '{ou_name}' under '{parent_ou}': {e}")
        raise e  # Re-raise the exception to trigger retry

def check_ou_exists_or_create(domain, parent_ou, ou_to_check):
    """
    Check if the given OU exists under the parent OU for the domain, or create it if it doesn't exist.
    """
    try:
        org_units = service.orgunits().list(customerId='my_customer', type='children', orgUnitPath=parent_ou).execute()
        for ou in org_units.get('organizationUnits', []):
            if ou['name'] == ou_to_check:
                return True
        create_ou(ou_to_check, parent_ou, domain)
        return True
    except Exception as e:
        print(f"Failed to check or create OU '{ou_to_check}' for domain {domain}: {e}")
        raise e  # Re-raise the exception so that tenacity knows to retry

def check_required_ous_or_create(domain):
    """
    Check if both '1.Users' and '1.6Suspended' OUs exist for the given domain, or create them if they don't.
    """
    if domain in ou_check_cache:
        return ou_check_cache[domain]
    
    domain_ou_path = f"/@{domain}"
    
    if not check_ou_exists_or_create(domain, "/", f"@{domain}"):
        print(f"Domain OU '@{domain}' does not exist. Skipping this domain.")
        ou_check_cache[domain] = False
        return False
    
    if not check_ou_exists_or_create(domain, domain_ou_path, "1.Users"):
        ou_check_cache[domain] = False
        return False
    
    if not check_ou_exists_or_create(domain, f"{domain_ou_path}/1.Users", "1.6Suspended"):
        ou_check_cache[domain] = False
        return False
    
    ou_check_cache[domain] = True
    return True

def process_user(user_data):
    """
    Process an individual user: check if they need to be moved and move them if necessary.
    """
    email = user_data['userPrincipalName']
    domain = email.split('@')[1]
    current_ou = user_data['orgUnitPath']  # Use the orgUnitPath from the CSV
    all_domains.add(domain)
    
    if not check_required_ous_or_create(domain):
        return
    
    # Construct the correct suspended OU path
    target_ou = f"/@{domain}/1.Users/1.6Suspended"
    
    # Count the user if they are suspended
    suspended_users_count_per_school[domain] += 1
    
    # If the user is already in the suspended OU, skip further processing
    if current_ou == target_ou:
        return
    
    try:
        # Move the user to the suspended OU
        user_body = {"orgUnitPath": target_ou}
        service.users().update(userKey=email, body=user_body).execute()
        moved_users_count_per_school[domain] += 1
    
    except Exception as e:
        print(f'Failed to move {email}: {e}')

# Process each suspended user sequentially
for user_data in suspended_users:
    process_user(user_data)

# Output the final breakdown per school (domain)
if not all_domains:
    print("No domains found or all users are already in the suspended OU")
else:
    print("\nBreakdown of suspended and moved users per school:\n")
    for domain in all_domains:
        suspended_count = suspended_users_count_per_school.get(domain, 0)
        moved_count = moved_users_count_per_school.get(domain, 0)
        ous_created = ous_created_per_school.get(domain, [])
        
        print(f'School (Domain): {domain}')
        print(f'  Total suspended users: {suspended_count}')
        print(f'  Total moved to suspended OU: {moved_count}')
        
        if ous_created:
            print(f'  OUs created: {", ".join(ous_created)}')
        else:
            print(f'  No OUs created.')
        
        print('-' * 50)

print("Process finished --- %s seconds ---" % (time.time() - start_time))
