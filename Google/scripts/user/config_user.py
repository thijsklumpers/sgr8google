import os

# Get the current working directory dynamically
base_dir = os.path.dirname(os.path.abspath(__file__))

# Service account file relative to the root of the repository
SERVICE_ACCOUNT_FILE = os.path.join(base_dir, '..', '..', 'service', 'automatic-ou-user-sync-test-b35f84558a8c.json')
#SERVICE_ACCOUNT_FILE = r'C:\Users\ThijsKlumpers\Git\sgr8google\Google\service\automatic-ou-user-sync-test-b35f84558a8c.json'

# Delegated admin email
DELEGATED_ADMIN_EMAIL = 'thijs.klumpers@sgrbrussel.be'


