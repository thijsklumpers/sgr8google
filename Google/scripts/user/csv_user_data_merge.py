import pandas as pd
import os
import time
import unicodedata
import json

start_time = time.time()

def remove_special_characters(text):
    """
    This function normalizes text to remove special characters, such as accents and diacritics.
    """
    if isinstance(text, str):
        return unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
    return text

def merge_user_data(intune_file, google_admin_file, output_file):
    """
    Merges user data from Intune and Google Admin CSV files and saves the combined data.
    """
    # Read both CSV files
    intune_df = pd.read_csv(intune_file)
    google_admin_df = pd.read_csv(google_admin_file)

    # Check if 'jobTitle' column exists in Intune DataFrame
    if 'jobTitle' in intune_df.columns:
        # Normalize the jobTitle field in Intune DataFrame
        intune_df['jobTitle'] = intune_df['jobTitle'].apply(remove_special_characters)
    else:
        print("Warning: 'jobTitle' column not found in Intune CSV file.")

    # Merge the data based on matching userPrincipalName and primaryEmail
    # Assuming userPrincipalName matches primaryEmail for common users
    merged_df = pd.merge(
        intune_df,
        google_admin_df,
        left_on='userPrincipalName',
        right_on='primaryEmail',
        how='inner'
    )

    # Keep the relevant columns
    filtered_df = merged_df[['userPrincipalName', 'jobTitle', 'department', 'companyName', 'suspended', 'orgUnitPath', 'isAdmin']]

    # Save the merged data to 'merged_user_data.csv'
    filtered_df.to_csv(output_file, index=False)
    print(f"Data successfully merged and saved to {output_file}")

if __name__ == "__main__":
    # Load configuration from config.json
    config_path = os.path.join(os.path.dirname(__file__), '../../service/config.json')
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)

    # Retrieve base_dir from the configuration, defaulting to the script's directory if not set
    base_dir = os.path.join(os.path.dirname(__file__))

    # Dynamically construct paths relative to base_dir
    intune_file = os.path.join(base_dir, 'csv', 'user', 'core', 'multi_school_intune.csv')
    google_admin_file = os.path.join(base_dir, 'csv', 'user', 'core', 'all_google_user_data.csv')
    output_file = os.path.join(base_dir, 'csv', 'user', 'merged', 'merged_user_data.csv')

    # Call the function with dynamically resolved file paths
    merge_user_data(intune_file, google_admin_file, output_file)

print("Process finished in --- %s seconds ---" % (time.time() - start_time))
