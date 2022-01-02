import requests
from datetime import datetime, timezone, timedelta
import time


# Discord webhook url
WEBHOOK = "https://discord.com/api/webhooks/914687890213208124/8Nx5xnlce3HdixHTFhUTB3utKPu7q1f8yN6xew7kOAf0IDTFYuKqS2EW73TL5SG4E-sU"

# Delay in seconds between checking for new escrows
DELAY = 15

# Escrow URL
URL = "https://hashes.com/en/escrow/viewjson"

# Minimum total bounty to send in USD
MIN_BOUNTY = 0

# Timezone
TIMEZONE = timezone(timedelta(hours=-6))

if __name__ == "__main__":
    last_time = datetime.now(tz=TIMEZONE)
    while True:
        try:
            r = requests.get(URL)
            r.raise_for_status()
            for escrow in r.json():
                total_bounty = float(escrow['maxCracksNeeded']) * float(escrow['pricePerHashUsd'])
                created_at = datetime.fromisoformat(escrow["createdAt"])
                created_at = created_at.replace(tzinfo=TIMEZONE)
                if created_at > last_time and total_bounty >= MIN_BOUNTY:
                    last_time = created_at
                    message = {
                        "content": "@everyone",
                        "embeds": [
                            {
                                "title": "New Paid Hash Cracking Listing",
                                "url": f"https://hashes.com/en/escrow/item/?id={escrow['id']}",
                                "color": 4039668,
                                "fields": [
                                    {
                                        "name": "Algorithim",
                                        "value": f"{escrow['algorithmName']} - {escrow['algorithmId']}",
                                        "inline": True,
                                    },
                                    {
                                        "name": "Total Hashes",
                                        "value": str(escrow["totalHashes"]),
                                        "inline": True,
                                    },
                                    {
                                        "name": "Price Per Hash (BTC)",
                                        "value": str(escrow["pricePerHash"]),
                                        "inline": False,
                                    },
                                    {
                                        "name": "Price Per Hash (USD)",
                                        "value": str(escrow["pricePerHashUsd"]),
                                        "inline": True,
                                    },
                                    {
                                        "name": "Max Cracks Needed",
                                        "value": f"{escrow['maxCracksNeeded']} (${total_bounty:.2f})",
                                        "inline": True,
                                    },
                                    {
                                        "name": "Left List",
                                        "value": f"https://hashes.com{escrow['leftList']}",
                                        "inline": False,
                                    },

                                ],
                            }
                        ],
                        "username": "Hashes.com Watcher",
                    }

                    print("SENDING: ", escrow["id"])
                    p = requests.post(
                        url=WEBHOOK,
                        headers={"Content-Type": "application/json"},
                        json=message
                    )
                    try:
                        p.raise_for_status()
                    except Exception as e:
                        print("Failed to send message to discord webhook: ", e)


        except Exception as e:
            print(f"Failed to get escrows: {e}")

        time.sleep(DELAY)

