import os
import time
import requests
import pandas as pd
import pytumblr
import google.generativeai as genai

# Secrets from GitHub Environment
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1wyUX_NyWmsNQRq2XYDP0EoMNxkSccgv3zhWYVaMe0_k/export?format=csv"

# Setup Gemini AI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def get_pexels_photo(query):
    """Fetch photo from Pexels based on Niche"""
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/v1/search?query={query}&per_page=1"
    try:
        res = requests.get(url, headers=headers).json()
        if res.get('photos') and len(res['photos']) > 0:
            return res['photos'][0]['src']['large']
    except Exception as e:
        print(f"Pexels API Error: {e}")
    return None

def generate_ai_content(niche):
    """Generate Caption & Hashtags using Gemini AI"""
    prompt = f"Create an engaging, trending Tumblr post caption for the niche '{niche}'. Include a captivating title, description, and 8-10 trending relevant hashtags at the bottom. Plain text only, no bolding or markdown code blocks."
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini AI Error: {e}")
        return f"Explore top trends in {niche}! #trending #{niche.replace(' ', '')}"

def process_and_post():
    # Read Google Sheet directly
    print("Reading Google Sheet data...")
    df = pd.read_csv(SHEET_URL)
    
    total_accounts = len(df)
    print(f"Total Accounts Found: {total_accounts}")

    for index, row in df.iterrows():
        account_name = str(row.get("Account Name")).strip()
        niche = str(row.get("Niche")).strip()
        consumer_key = str(row.get("OAuth Consumer Key")).strip()
        consumer_secret = str(row.get("Aonsumer_secret")).strip()
        token = str(row.get("Token")).strip()
        token_secret = str(row.get("Token_secret")).strip()

        print(f"\n--------------------------------------------------")
        print(f"Processing Account {index+1}/{total_accounts}: {account_name}")
        print(f"Niche: {niche}")

        try:
            # 1. Fetch Image from Pexels
            image_url = get_pexels_photo(niche)
            if not image_url:
                print(f"[-] Image not found on Pexels for niche '{niche}'. Skipping...")
                continue
            print(f"[+] Image found: {image_url}")

            # 2. Generate Content via Gemini AI
            content = generate_ai_content(niche)
            print("[+] Content generated via Gemini AI.")

            # 3. Setup Tumblr Client
            t_client = pytumblr.TumblrRestClient(
                consumer_key,
                consumer_secret,
                token,
                token_secret
            )

            # 4. Post Photo to Tumblr
            response = t_client.create_photo(
                account_name,
                state="published",
                source=image_url,
                caption=content
            )
            
            if 'id' in response:
                print(f"[✔] Successfully posted on {account_name}! Post ID: {response['id']}")
            else:
                print(f"[❌] Tumblr Error Response: {response}")

        except Exception as e:
            print(f"[❌] Error posting on {account_name}: {str(e)}")

        # Wait 10 Minutes (600 seconds) before processing next account
        if index < total_accounts - 1:
            print("⏳ Waiting 10 minutes (600 seconds) before posting to the next account...")
            time.sleep(600)

if __name__ == "__main__":
    process_and_post()
