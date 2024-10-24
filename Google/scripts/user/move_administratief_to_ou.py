import os
import csv
import time
import re
from collections import defaultdict
from google.oauth2 import service_account
from googleapiclient.discovery import build
from config import SERVICE_ACCOUNT_FILE, DELEGATED_ADMIN_EMAIL,base_dir

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
required_ous = defaultdict(set)

def sanitize_ou_name(ou_name, allow_period=False):
    if not ou_name:
        return None
    
    if allow_period:
        sanitized_ou_name = re.sub(r'[^\w\s.-]', '', ou_name)
    else:
        sanitized_ou_name = re.sub(r'[^\w\s]', '', ou_name)
    
    sanitized_ou_name = sanitized_ou_name.strip()
    return sanitized_ou_name if sanitized_ou_name else None

def create_ou(ou_name, parent_ou, domain):
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
    ou_to_check = sanitize_ou_name(ou_to_check, allow_period=True)

    if not ou_to_check:
        print(f"Skipping invalid OU '{ou_to_check}' under '{parent_ou}'")
        return False
    
    try:
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
    for domain in required_ous.keys():
        domain_ou_path = f"/@{domain}"
        
        # Check if '1.Users' exists under the domain
        if not check_ou_exists_or_create(domain, domain_ou_path, "1.Users"):
            continue
        
        # Ensure '1.2Administratie' exists before moving users
        check_ou_exists_or_create(domain, f"{domain_ou_path}/1.Users", "1.2Administratie")

# Step 1: Pre-scan the CSV file to gather only non-suspended users with specific job titles
non_suspended_users = []
target_job_titles = ["Directeur", "Administratief medewerker"]  # Add any other relevant job titles

with open(csv_file_path, mode='r') as file:
    csv_reader = csv.DictReader(file)
    
    for row in csv_reader:
        email = row['userPrincipalName']
        domain = row['userPrincipalName'].split('@')[1]
        job_title = row.get('jobTitle', '')
        
        try:
            user = service.users().get(userKey=email).execute()
            is_suspended = user.get('suspended', False)
            
            # Skip suspended users and check if the job title matches the target job titles
            if not is_suspended and any(job in job_title for job in target_job_titles):
                required_ous[domain].add("1.2Administratie")
                non_suspended_users.append((email, domain))
            else:
                print(f"Skipping user {email} due to suspension or unmatched job title.")
                
            all_domains.add(domain)
        except Exception as e:
            print(f"Failed to fetch user {email}: {e}")

# Step 2: Check and create all required OUs before moving users
check_and_create_required_ous()

# Step 3: Move users to the correct OU
for email, domain in non_suspended_users:
    target_ou = f"/@{domain}/1.Users/1.2Administratie"
    
    try:
        user = service.users().get(userKey=email).execute()
        current_ou = user.get('orgUnitPath', '')
        
        # Move the user if not already in the correct OU
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
    print(f'  Total moved to "Administratie" OUs: {moved_count}')
    
    if ous_created:
        print(f'  OUs created: {", ".join(ous_created)}')
    else:
        print(f'  No OUs created.')
    
    print('-' * 50)

print(f"Process finished --- {time.time() - start_time} seconds ---")
