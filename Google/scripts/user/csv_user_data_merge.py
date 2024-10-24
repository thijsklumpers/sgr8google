import pandas as pd
import os
import time
import unicodedata
from config_user import base_dir

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
    This function merges user data from Intune and Google Admin CSV files
    and saves a combined file with selected fields for users present in both.
    
    Parameters:
    intune_file: str - Path to the Intune user data CSV file.
    google_admin_file: str - Path to the Google Admin user data CSV file.
    output_file: str - Path where the output merged CSV file will be saved.
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

    # Keep the relevant columns, including orgUnitPath from Google Admin
    filtered_df = merged_df[['userPrincipalName', 'jobTitle', 'department', 'companyName', 'suspended', 'orgUnitPath', 'isAdmin']]

    # Save the resulting dataframe to a new CSV file
    filtered_df.to_csv(output_file, index=False)
    print(f"Data successfully merged and saved to {output_file}")

if __name__ == "__main__":
    # Dynamically construct paths relative to the current working directory
    intune_file = os.path.join(base_dir, '../../csv/user/core/multi_school_intune.csv')
    google_admin_file = os.path.join(base_dir, '../../csv/user/core/all_google_user_data.csv')
    output_file = os.path.join(base_dir, '../../csv/user/merged_user_data.csv')

    # Call the function with dynamically resolved file paths
    merge_user_data(intune_file, google_admin_file, output_file)

print("Process finished in --- %s seconds ---" % (time.time() - start_time))