import os
import csv
import time
import re
import json
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

# Define the scope and credentials
SCOPES = [
    'https://www.googleapis.com/auth/admin.directory.user',
    'https://www.googleapis.com/auth/admin.directory.orgunit'
]

credentials = service_account.Credentials.from_service_account_file(
    os.path.join(os.path.dirname(__file__), '../../service', SERVICE_ACCOUNT_FILE),
    scopes=SCOPES
)
credentials = credentials.with_subject(DELEGATED_ADMIN_EMAIL)
service = build('admin', 'directory_v1', credentials=credentials)

# Define base_dir for your CSV files
base_dir = os.path.dirname(__file__)

# Path to your CSV file
csv_file_path = os.path.join(base_dir, '../../csv/user/merged/merged_user_data.csv')

# Initialize dictionaries to track users per domain (school)
moved_users_count_per_school = defaultdict(int)
ous_created_per_school = defaultdict(list)
all_domains = set()  # To store all domains found in the CSV
ou_check_cache = {}  # To store the OU check results per domain

# Initialize a set to store all OUs that need to be checked or created
required_ous = defaultdict(set)

def sanitize_ou_name(ou_name, allow_period=False):
    """Sanitize the OU name to remove or replace any invalid characters."""
    if not ou_name:
        return None
    if allow_period:
        sanitized_ou_name = re.sub(r'[^\w\s.-]', '', ou_name)
    else:
        sanitized_ou_name = re.sub(r'[^\w\s]', '', ou_name)
    sanitized_ou_name = sanitized_ou_name.strip()
    return sanitized_ou_name if sanitized_ou_name else None

def create_ou(ou_name, parent_ou, domain):
    """Create a new organizational unit under the specified parent OU."""
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
        print(f"Failed to create OU '{ou_name}' under '{parent_ou}': {e}")
        return None

def check_ou_exists_or_create(domain, parent_ou, ou_to_check):
    """Check if the given OU exists under the parent OU for the domain, or create it if it doesn't exist."""
    ou_to_check = sanitize_ou_name(ou_to_check, allow_period=True)
    
    if not ou_to_check:
        print(f"Skipping invalid OU '{ou_to_check}' under '{parent_ou}'")
        return False
    
    try:
        # List all org units under the parent OU
        org_units = service.orgunits().list(customerId='my_customer', type='children', orgUnitPath=parent_ou).execute()
        for ou in org_units.get('organizationUnits', []):
            if ou['name'] == ou_to_check:
                print(f"OU '{ou_to_check}' already exists under '{parent_ou}'")
                return True
        
        # If OU does not exist, create it
        create_ou(ou_to_check, parent_ou, domain)
        return True
    except Exception as e:
        print(f"Failed to check or create OU '{ou_to_check}' for domain {domain}: {e}")
        return False

def check_and_create_required_ous():
    """Check if all required OUs exist for each domain and department. Create any missing OUs."""
    for domain, departments in required_ous.items():
        domain_ou_path = f"/@{domain}"
        
        # Ensure '1.Users' exists under the domain
        if not check_ou_exists_or_create(domain, domain_ou_path, "1.Users"):
            continue

        # Create '1.3Leerkracht' and '1.2Administratie' under '/1.Users' directly
        if "1.3Leerkracht" in departments:
            check_ou_exists_or_create(domain, f"{domain_ou_path}/1.Users", "1.3Leerkracht")
            # Remove from departments so they are not reprocessed later
            departments.discard("1.3Leerkracht")

        if "1.2Administratie" in departments:
            check_ou_exists_or_create(domain, f"{domain_ou_path}/1.Users", "1.2Administratie")
            # Remove from departments so they are not reprocessed later
            departments.discard("1.2Administratie")
        
        # Ensure '1.4Leerling' exists under '/1.Users' before creating sub-OUs (classes)
        if not check_ou_exists_or_create(domain, f"{domain_ou_path}/1.Users", "1.4Leerling"):
            print(f"Skipping department OU creation for {domain} because '1.4Leerling' could not be created.")
            continue
        
        # Check if department-specific OUs (class OUs) exist under '1.4Leerling'
        for department in departments:
            if department:
                if not check_ou_exists_or_create(domain, f"{domain_ou_path}/1.Users/1.4Leerling", department):
                    print(f"Failed to create class OU '{department}' for domain {domain}")
            else:
                print(f"Skipping empty department OU creation for domain {domain}")

# Step 1: Pre-scan the CSV file to gather only non-suspended users with specific job titles
non_suspended_users_leerkracht = []
non_suspended_users_administratie = []
non_suspended_users_leerling = []

target_job_titles_leerkracht = ["Leraar", "Leraar LBV", "Leraar LO", "Zorgcoordinator"]
target_job_titles_administratie = ["Directeur", "Administratief medewerker"]

with open(csv_file_path, mode='r') as file:
    csv_reader = csv.DictReader(file)
    for row in csv_reader:
        email = row['userPrincipalName']
        domain = email.split('@')[1]
        job_title = row.get('jobTitle', '')
        department = row.get('department', '')
        try:
            user = service.users().get(userKey=email).execute()
            is_suspended = user.get('suspended', False)
            if not is_suspended:
                if any(job in job_title for job in target_job_titles_leerkracht):
                    required_ous[domain].add("1.3Leerkracht")
                    non_suspended_users_leerkracht.append((email, domain))
                elif any(job in job_title for job in target_job_titles_administratie):
                    required_ous[domain].add("1.2Administratie")
                    non_suspended_users_administratie.append((email, domain))
                elif job_title == "Leerling" and department:
                    sanitized_department = sanitize_ou_name(department)
                    required_ous[domain].add(sanitized_department)
                    non_suspended_users_leerling.append((email, domain, sanitized_department))
                else:
                    print(f"Skipping user {email} due to unmatched job title.")
            else:
                print(f"Skipping user {email} due to suspension.")
            all_domains.add(domain)
        except Exception as e:
            print(f"Failed to fetch user {email}: {e}")

# Step 2: Check and create all required OUs before moving users
check_and_create_required_ous()

# Step 3: Move users to the correct OU for Leerkracht
for email, domain in non_suspended_users_leerkracht:
    target_ou = f"/@{domain}/1.Users/1.3Leerkracht"
    try:
        user = service.users().get(userKey=email).execute()
        current_ou = user.get('orgUnitPath', '')
        if current_ou != target_ou:
            user_body = {"orgUnitPath": target_ou}
            service.users().update(userKey=email, body=user_body).execute()
            print(f'Successfully moved {email} to {target_ou}')
            moved_users_count_per_school[domain] += 1
        else:
            print(f'{email} is already in the correct OU. No action taken.')
    except Exception as e:
        print(f'Failed to move {email} to {target_ou}: {e}')

# Step 4: Move users to the correct OU for Administratie
for email, domain in non_suspended_users_administratie:
    target_ou = f"/@{domain}/1.Users/1.2Administratie"
    try:
        user = service.users().get(userKey=email).execute()
        current_ou = user.get('orgUnitPath', '')
        if current_ou != target_ou:
            user_body = {"orgUnitPath": target_ou}
            service.users().update(userKey=email, body=user_body).execute()
            print(f'Successfully moved {email} to {target_ou}')
            moved_users_count_per_school[domain] += 1
        else:
            print(f'{email} is already in the correct OU. No action taken.')
    except Exception as e:
        print(f'Failed to move {email}: {e}')

# Step 5: Move users to the correct OU for Leerling
for email, domain, department in non_suspended_users_leerling:
    target_ou = f"/@{domain}/1.Users/1.4Leerling/{department}"
    try:
        user = service.users().get(userKey=email).execute()
        current_ou = user.get('orgUnitPath', '')
        if current_ou != target_ou:
            user_body = {"orgUnitPath": target_ou}
            service.users().update(userKey=email, body=user_body).execute()
            print(f'Successfully moved {email} to {target_ou}')
            moved_users_count_per_school[domain] += 1
        else:
            print(f'{email} is already in the correct OU. No action taken.')
    except Exception as e:
        print(f'Failed to move {email} to {target_ou}: {e}')


# Output the final breakdown per school (domain)
print("\nBreakdown of moved users per school:\n")
for domain in all_domains:
    moved_count = moved_users_count_per_school.get(domain, 0)
    ous_created = ous_created_per_school.get(domain, [])
    print(f'School (Domain): {domain}')
    print(f'  Total moved to OUs: {moved_count}')
    if ous_created:
        print(f'  OUs created: {", ".join(ous_created)}')
    else:
        print(f'  No OUs created.')
    print('-' * 50)

print(f"Process finished --- {time.time() - start_time} seconds ---")
