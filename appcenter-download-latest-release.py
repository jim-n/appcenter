import argparse
import requests
import zipfile
import os
import subprocess
import shutil
import json
from tqdm import tqdm
import sys
import argparse

class MissingKeyError(Exception):
    pass

def load_settings(file_path):
    try:
        with open(file_path) as file:
            settings = json.load(file)
    except FileNotFoundError:
        print("Settings file appcenter-secrets.json not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print("Invalid JSON format in settings file appcenter-secrets.json")
        sys.exit(1)

    required_keys = ['api_token', 'app_secret', 'owner_name', 'app_name', 'distribution_group_name', 'distribution_group_id', 'download_path', 'installer_filetype']
    for key in required_keys:
        if key not in settings:
            raise MissingKeyError(f"Missing required key '{key}' in the appcenter-secrets.json")

    return settings

def parse_args():
    parser = argparse.ArgumentParser(description="Downloads the latest release from AppCenter and optionally starts the installer.")
    parser.add_argument('--install', action='store_true', help='Start the installer after the download is complete. Add installer arguments to initiate the installer with.')
    return parser.parse_args()

def main():
    args = parse_args()

    current_dir = os.path.dirname(os.path.abspath(__file__))
    settings_file_path = os.path.join(current_dir, 'appcenter-secrets.json')
    settings = load_settings(settings_file_path)

    api_token = settings['api_token']
    app_secret = settings['app_secret']
    owner_name = settings['owner_name']
    app_name = settings['app_name']
    distribution_group_name = settings['distribution_group_name']
    distribution_group_id = settings['distribution_group_id']
    download_path = settings['download_path']
    installer_filetype = settings['installer_filetype']

    # Get releases for the project
    releases_url = f"https://api.appcenter.ms/v0.1/apps/{owner_name}/{app_name}/distribution_groups/{distribution_group_name}/releases"
    print(f"Getting releases for {owner_name}/{app_name}...")
    headers = {"X-API-Token": api_token}

    try:
        response = requests.get(releases_url, headers=headers)
        response.raise_for_status()
        releases = response.json()
        assert releases, "Release list is empty"
        release_id = max(releases, key=lambda x: x['id'])['id']
        uploaded_at = max(releases, key=lambda x: x['id'])['uploaded_at']

        # Download the release
        release_url = f"https://api.appcenter.ms/v0.1/apps/{owner_name}/{app_name}/distribution_groups/{distribution_group_name}/releases/{release_id}"
        response = requests.get(release_url, headers=headers)
        response.raise_for_status()
        release = response.json()
        download_url = release.get('download_url')
        file_extension = release.get('fileExtension')
        version = release.get('version')
        output_file = os.path.join(download_path, f"{version}.{file_extension}")

        # Prompt user to confirm download
        answer = input(f"Do you want to download version {version} uploaded at {uploaded_at}? (Y/N) ")
        if answer.lower() not in ["y", "yes"]:
            print("Answer was not 'Y' or 'Yes'. Aborting.")
            sys.exit(0)
        
        # Prompt the user if the file already exists
        if os.path.exists(output_file):
            answer = input(f"File {output_file} already exists. Do you want to overwrite it? (Y/N) ")
            if answer.lower() not in ["y", "yes"]:
                print("Answer was not 'Y' or 'Yes'. Aborting.")
                sys.exit(0)

        with requests.get(download_url, headers=headers, stream=True) as r:
            total_length = int(r.headers.get("Content-Length"))

            with tqdm.wrapattr(r.raw, "read", total=total_length, desc="Downloading", ncols=80) as raw:
                with open(output_file, "wb") as output:
                    shutil.copyfileobj(raw, output)

        # Unzip the downloaded file
        if file_extension == 'zip':
            unzip_path = os.path.join(download_path, f"{version} Unzipped")
            with zipfile.ZipFile(output_file, "r") as zip_ref:
                print("Unzipping the downloaded file...")
                total_files = len(zip_ref.namelist())
                with tqdm(total=total_files, desc="Unzipping", ncols=80) as pbar:
                    for file in zip_ref.namelist():
                        zip_ref.extract(file, unzip_path)
                        pbar.update(1)
                print("Done.")

        # Start the installer if the --install flag is set
        if args.install is False:
            sys.exit(0)

        # Run the installer with command line arguments if provided
        installer_args = settings.get('installer_args')
        installer_path = next(
            (
                os.path.join(root, file)
                for root, dirs, files in os.walk(unzip_path)
                for file in files
                if file.endswith(installer_filetype)
            ),
            None,
        )

        # Add installer_args to the installer_path if provided
        if installer_args:
            installer_path = f"{installer_path} {installer_args}"

        if installer_path:
            print("Starting the installer with the following command:")
            print(installer_path)
            subprocess.run(installer_path, check=True)
            print("Done.")
        else:
            print("No installer file found in the latest release.")

    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        print(f"Response content: {response.content}")

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()