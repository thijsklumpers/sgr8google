import os
import csv
import time
import re
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

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
credentials = credentials.with_subject(DELEGATED_ADMIN_EMAIL)

service = build('admin', 'directory_v1', credentials=credentials)

# Path to your CSV file
csv_file_path = os.path.join(base_dir, '../../csv/user/merged_user_data.csv')

# Initialize dictionaries to track users per domain (school)
moved_users_count_per_school = defaultdict(int)
ous_created_per_school = defaultdict(list)
all_domains = set()  # To store all domains found in the CSV
ou_check_cache = {}  # To store the OU check results per domain

# Initialize a set to store all OUs that need to be checked or created
required_ous = defaultdict(set)  # <-- This line is added to initialize 'required_ous'

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
        print(f"Failed to create OU '{ou_name}' under '{parent_ou}': {e}")
        return None

def check_ou_exists_or_create(domain, parent_ou, ou_to_check):
    """
    Check if the given OU exists under the parent OU for the domain, or create it if it doesn't exist.
    :param domain: The domain (OU) to search OUs for.
    :param parent_ou: The parent OU path (e.g., "/@boomhut").
    :param ou_to_check: The child OU to check existence (e.g., "1.Users").
    :return: True if the OU exists or was successfully created, False otherwise.
    """
    ou_to_check = sanitize_ou_name(ou_to_check, allow_period=True)

    if not ou_to_check:
        print(f"Skipping invalid OU '{ou_to_check}' under '{parent_ou}'")
        return False
    
    try:
        # List all org units under the parent OU
        org_units = service.orgunits().list(customerId='my_customer', type='children', orgUnitPath=parent_ou).execute()
        for ou in org_units.get('organizationUnits', []):
            if ou['name'] == ou_to_check:
                return True
        create_ou(ou_to_check, parent_ou, domain)
        return True
    except Exception as e:
        print(f"Failed to check or create OU '{ou_to_check}' for domain {domain}: {e}")
        return False

def check_and_create_required_ous():
    """
    Check if all required OUs exist for each domain and department.
    Create any missing OUs.
    """
    for domain, departments in required_ous.items():
        domain_ou_path = f"/@{domain}"
        
        # Check if '1.Users' exists under the domain
        if not check_ou_exists_or_create(domain, domain_ou_path, "1.Users"):
            continue
        
        # Ensure '1.4Leerling' exists before creating sub-OUs
        if not check_ou_exists_or_create(domain, f"{domain_ou_path}/1.Users", "1.4Leerling"):
            print(f"Skipping department OU creation for {domain} because '1.4Leerling' could not be created.")
            continue
        
        # Check if department-specific OUs exist under '1.4Leerling'
        for department in departments:
            if department:
                check_ou_exists_or_create(domain, f"{domain_ou_path}/1.Users/1.4Leerling", department)
            else:
                print(f"Skipping empty department OU creation for domain {domain}")

# Step 1: Pre-scan the CSV file to gather only non-suspended users
non_suspended_users = []

with open(csv_file_path, mode='r') as file:
    csv_reader = csv.DictReader(file)
    
    for row in csv_reader:
        email = row['userPrincipalName']
        domain = row['userPrincipalName'].split('@')[1]  # This represents the school in your case
        department = row.get('department', '')  # Get the department (class) information
        job_title = row.get('jobTitle', '')  # Get the job title of the user
        
        # Fetch user by email to check if they are suspended
        try:
            user = service.users().get(userKey=email).execute()
            is_suspended = user.get('suspended', False)  # Check if the user is suspended
            
            # Skip suspended users
            if not is_suspended:
                sanitized_department = sanitize_ou_name(department)
                if job_title == "Leerling" and sanitized_department:
                    required_ous[domain].add(sanitized_department)
                    non_suspended_users.append((email, domain, department))
            else:
                print(f"Skipping suspended user {email}.")
                
            all_domains.add(domain)
        except Exception as e:
            print(f"Failed to fetch user {email}: {e}")

# Step 2: Check and create all required OUs before moving users
check_and_create_required_ous()

# Step 3: After OUs are created, check if users are already in the correct OU and move them if necessary
for email, domain, department in non_suspended_users:
    sanitized_department = sanitize_ou_name(department)
    target_ou = f"/@{domain}/1.Users/1.4Leerling/{sanitized_department}"
    
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
        print(f'Failed to move {email}: {e}')

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
