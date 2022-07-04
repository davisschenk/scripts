import imaplib
import re
import time
import email
import requests
import sys
import base64

EMAIL = "dronecenter.tcon@gmail.com"
PASSWORD = "morciicwvtjuaqqt"
SERVER = "imap.gmail.com"
WEBHOOK = "https://discord.com/api/webhooks/992882015663816725/sMMnmnqeq7X3aPkpH0yuvXAPFRvYMTk-vtheOppuIEQjhmIQG27jgEediiKskPrjKqwk"
DELAY = 60*5


def format_str(s):
    if isinstance(s, bytes):
        s = s.decode("utf-8")

    s = re.sub("=\?UTF-8\?B\?([A-Za-z\d+/]+=?=?)\?=", lambda m: base64.b64decode(m.group(1)).decode("utf-8"), s)
    return s


if __name__ == "__main__":
    mail_client = imaplib.IMAP4_SSL(SERVER)
    mail_client.login(EMAIL, PASSWORD)
    mail_client.select("inbox")

    while True:
        mail_client._simple_command("NOOP")  # Make sure we have up to date emails

        status, data = mail_client.search(None, "(UNSEEN)")

        if status == "OK":
            for email_id in sorted(data[0].split(), key=int):
                typ, data = mail_client.fetch(email_id, "(RFC822)")
                for response_part in data:
                    if isinstance(response_part, tuple):
                        em = email.message_from_bytes(response_part[1])
                        email_to = format_str(em["To"])
                        email_from = format_str(em["From"])
                        email_subject = format_str(em["Subject"])
                        print("TO:", email_to)
                        print("FROM:", email_from)
                        print("SUBJECT:", email_subject)
                        if em.is_multipart():
                            content = ""

                            for part in em.get_payload():
                                if part.get_content_type() in ('text/plain'):
                                    content += format_str(part.get_payload())
                        else:
                            content = format_str(em.get_payload())

                        message = {
                            "content": "@everyone",
                            "embeds": [
                                {
                                    "title": email_subject,
                                    "color": 4039668,
                                    # "description": content[:min(len(content), 4000)],
                                    "fields": [
                                        {
                                            "name": "From:",
                                            "value": email_from,
                                            "inline": True,
                                        },
                                        {
                                            "name": "To:", "value": email_to,
                                            "inline": True,
                                        },
                                    ],
                                }
                            ],
                            "username": "Email Receiever",
                        }

                        if "forwarding-noreply@google.com" in em["From"]:
                            url = re.search("https://mail-settings.google.com/mail/.*", content).group(0)
                            confirmation = re.search(r"Confirmation code: (\d+)", content).group(1)

                            message["embeds"][0]["fields"].append({
                                "name": "Confirmation Code:",
                                "value": confirmation,
                                "inline": False
                            })

                            message["embeds"][0]["fields"].append({
                                "name": "Mail Settings URL",
                                "value": f"[URL]({url})",
                                "inline": True
                            })

                        elif em["Reply-To"] == "noreply@a.jagex.com":
                            url = re.search("https://secure\.runescape\.com/m=accountappeal/trackinginput.ws\?code=.*", content).group(0)
                            message["embeds"][0]["fields"].append({
                                "name": "Account Appeal URL",
                                "value": f"[URL]({url})",
                                "inline": True
                            })

                        p = requests.post(
                            url=WEBHOOK,
                            headers={"Content-Type": "application/json"},
                            json=message
                        )

                        try:
                            p.raise_for_status()
                            typ, data = mail_client.store(email_id, "+FLAGS", "\\Seen")
                        except Exception as e:
                            print("Failed to send message to discord webhook: ", e, file=sys.stderr)

        time.sleep(DELAY)
