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
    Merges user data from Intune and Google Admin CSV files,
    compares with existing data if available, saves differences,
    and updates the merged data file.
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

    # Path for the compared data output
    compared_output_file = os.path.join(base_dir, '../../csv/user/merged_user_compared_data.csv')

    # Columns to compare
    columns_to_compare = ['jobTitle', 'department', 'companyName', 'suspended', 'orgUnitPath', 'isAdmin']

    # Check if output_file exists
    if os.path.exists(output_file):
        # Read existing data
        existing_df = pd.read_csv(output_file)

        # Merge filtered_df and existing_df on 'userPrincipalName' with suffixes
        merged_comparison = pd.merge(
            filtered_df, existing_df,
            on='userPrincipalName',
            how='outer',
            suffixes=('_new', '_old'),
            indicator=True
        )

        # Initialize differences mask
        differences = merged_comparison['_merge'] != 'both'

        # Compare columns
        for col in columns_to_compare:
            col_new = f'{col}_new'
            col_old = f'{col}_old'
            differences |= merged_comparison[col_new] != merged_comparison[col_old]

        # Extract rows with differences
        diff_df = merged_comparison[differences]

        # Keep relevant columns
        cols_to_keep = ['userPrincipalName'] + [f'{col}_new' for col in columns_to_compare]
        diff_df = diff_df[cols_to_keep]

        # Rename columns to original names
        diff_df.rename(columns={f'{col}_new': col for col in columns_to_compare}, inplace=True)

        # Save diff_df to 'merged_user_compared_data.csv'
        diff_df.to_csv(compared_output_file, index=False)
        print(f"Differences saved to {compared_output_file}")

    else:
        # If 'merged_user_data.csv' does not exist, save filtered_df to 'merged_user_compared_data.csv'
        filtered_df.to_csv(compared_output_file, index=False)
        print(f"No existing data found. All data saved to {compared_output_file}")

    # Overwrite the existing 'merged_user_data.csv' with new data
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