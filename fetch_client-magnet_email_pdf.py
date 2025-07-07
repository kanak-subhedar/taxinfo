# fetch_client-magnet_email_pdf.py

import os
import requests

# Constants
PDF_FILENAME = "cold_email_script.pdf"
PDF_LOCAL_PATH = os.path.join(os.getcwd(), PDF_FILENAME)

# Replace YOUR_USERNAME and YOUR_REPO with actual details
YOUR_USERNAME = "user-name"           # user name of the private repo on github
YOUR_REPO = "client-magnet-assets"    # private repo on github
GITHUB_REPO_URL = "https://raw.githubusercontent.com/{YOUR_USERNAME}/{YOUR_REPO}/main/cold_email_script.pdf"

def fetch_pdf_if_missing():
    """
    Check if PDF exists locally. If not, download it from GitHub using token.
    """
    if os.path.exists(PDF_LOCAL_PATH):
        print("✅ PDF already exists. No need to fetch.")
        return

    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("❌ GitHub token is missing. Set GITHUB_TOKEN as environment variable in Render.")
        return

    print("📥 PDF not found. Attempting download from GitHub...")

    headers = {
        "Authorization": f"token {github_token}"
    }

    response = requests.get(GITHUB_REPO_URL, headers=headers)

    if response.status_code == 200:
        with open(PDF_LOCAL_PATH, "wb") as f:
            f.write(response.content)
        print("✅ PDF downloaded and saved to:", PDF_LOCAL_PATH)
    else:
        print(f"❌ Failed to fetch PDF from GitHub. Status: {response.status_code}")
