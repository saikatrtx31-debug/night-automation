import os
import time
import requests
import pandas as pd
import pytumblr
import google.generativeai as genai

# Secrets from GitHub Environment
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")  # Optional: specific chat ID if known
SHEET_URL = "https://docs.google.com/spreadsheets/d/1wyUX_NyWmsNQRq2XYDP0EoMNxkSccgv3zhWYVaMe0_k/export?format=csv"

# Setup Gemini AI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')


def send_telegram_message(message):
    """Send status updates to Telegram"""
    if not TELEGRAM_BOT_TOKEN:
        print("Telegram bot token not configured.")
        return

    # If CHAT_ID is not provided, get the latest chat_id from bot updates
    chat_id = TELEGRAM_CHAT_ID
    if not chat_id:
        try:
            updates_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            res = requests.get(updates_url).json()
            if res.get("ok") and res.get("result"):
                chat_id = res["result"][-1]["message"]["chat"]["id"]
        except Exception as e:
            print(f"Failed to fetch Telegram Chat ID: {e}")

    if chat_id:
        send_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        try:
            requests.post(send_url, json=payload)
            print(f"Telegram notification sent to Chat ID: {chat_id}")
        except Exception as e:
            print(f"Failed to send Telegram message: {e}")
    else:
        print("Telegram Chat ID not found. Please message your bot first on Telegram.")


def get_pexels_photo(query):
    """Fetch photo from Pexels based on Niche"""
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/v1/search?query={query}&per_page=1"
    try:
        res = requests.get(url, headers=headers).json()
        if res.get('photos'):
            return res['photos'][0]['src']['large']
    except Exception as e:
        print(f"Pexels Error: {e}")
    return None


def generate_caption(niche, target_url):
    """Generate Tumblr Post Caption with Gemini AI"""
    prompt = f"""
    Write an engaging, aesthetic Tumblr post caption for the niche: '{niche}'.
    Include a mysterious/curiosity-driven call-to-action encouraging readers to click a link.
    Include relevant hashtags.
    Return ONLY the post text/html.
    Link to include: {target_url}
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini Error: {e}")
        return f"Explore more details here: {target_url} #aesthetic #{niche.replace(' ', '')}"


def process_and_post():
    # Read Google Sheet Data
    try:
        df = pd.read_csv(SHEET_URL)
    except Exception as e:
        err_msg = f"❌ Error loading Google Sheet: {e}"
        print(err_msg)
        send_telegram_message(err_msg)
        return

    total_accounts = len(df)
    send_telegram_message(f"🚀 **Automation Started!**\nProcessing {total_accounts} Tumblr accounts.")

    success_count = 0
    fail_count = 0

    for index, row in df.iterrows():
        blog_identifier = row.get('Blog Identifier')
        consumer_key = row.get('Consumer Key')
        consumer_secret = row.get('Consumer Secret')
        oauth_token = row.get('OAuth Token')
        oauth_secret = row.get('OAuth Token Secret')
        niche = row.get('Niche', 'Aesthetic')
        target_url = row.get('Target Link', '')

        print(f"\n[{index+1}/{total_accounts}] Processing Blog: {blog_identifier}")

        try:
            # Initialize Tumblr Client
            client = pytumblr.TumblrRestClient(
                consumer_key,
                consumer_secret,
                oauth_token,
                oauth_secret
            )

            # Get Photo
            photo_url = get_pexels_photo(niche)

            # Get Caption
            caption = generate_caption(niche, target_url)

            # Post to Tumblr
            if photo_url:
                res = client.create_photo(
                    blog_identifier,
                    state="published",
                    source=photo_url,
                    caption=caption
                )
            else:
                res = client.create_text(
                    blog_identifier,
                    state="published",
                    body=caption
                )

            if "id" in res:
                msg = f"✅ [{index+1}/{total_accounts}] Successfully posted to `{blog_identifier}`!"
                print(msg)
                send_telegram_message(msg)
                success_count += 1
            else:
                msg = f"⚠️ [{index+1}/{total_accounts}] Post failed for `{blog_identifier}`: {res}"
                print(msg)
                send_telegram_message(msg)
                fail_count += 1

        except Exception as e:
            msg = f"❌ [{index+1}/{total_accounts}] Error on `{blog_identifier}`: {e}"
            print(msg)
            send_telegram_message(msg)
            fail_count += 1

        # Wait 10 minutes before posting to the next account (if not last)
        if index < total_accounts - 1:
            print("Waiting 10 minutes before next account...")
            time.sleep(600)

    # Final Summary Telegram Message
    summary_msg = (
        f"🎉 **Automation Run Completed!**\n\n"
        f"📊 **Total Accounts:** {total_accounts}\n"
        f"✅ **Successful:** {success_count}\n"
        f"❌ **Failed:** {fail_count}"
    )
    print(summary_msg)
    send_telegram_message(summary_msg)


if __name__ == "__main__":
    process_and_post()
