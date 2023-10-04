import sys
import requests
import zipfile
import os
import subprocess
import shutil
import json
from tqdm import tqdm

current_dir = os.path.dirname(os.path.abspath(__file__))
settings_file_path = os.path.join(current_dir, 'appcenter-secrets.json')

try:
    with open(settings_file_path) as file:
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
        print(f"Missing required key '{key}' in the appcenter-secrets.json")
        sys.exit(1)

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
    assert releases, "Releas list is empty"
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
    if answer.lower() in ["n", "no"]:
        sys.exit(0)
    
    with requests.get(download_url, headers=headers, stream=True) as r:
        total_length = int(r.headers.get("Content-Length"))

        with tqdm.wrapattr(r.raw, "read", total=total_length, desc="") as raw:
            with open(output_file, "wb") as output:
                shutil.copyfileobj(raw, output)

    # Unzip the downloaded file
    if file_extension == 'zip':
        unzip_path = os.path.join(download_path, "Unzipped")
        with zipfile.ZipFile(output_file, "r") as zip_ref:
            zip_ref.extractall(unzip_path)

    # Start the installer
    installer_path = next(
        (
            os.path.join(root, file)
            for root, dirs, files in os.walk(unzip_path)
            for file in files
            if file.endswith(installer_filetype)
        ),
        None,
    )
    if installer_path:
        print("Starting the installer...")
        subprocess.run(installer_path, check=True)
        print("Done.")
    else:
        print("No installer file found in the latest release.")

except requests.exceptions.HTTPError as e:
    print(f"HTTP Error: {e}")
    print(f"Response content: {response.content}")

except requests.exceptions.RequestException as e:
    print(f"Error: {e}")