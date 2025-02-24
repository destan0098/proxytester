import requests
import socks
import socket
import time
import csv
from concurrent.futures import ThreadPoolExecutor
from colorama import Fore, Style

# For successful proxy

def load_proxies(filename):
    proxies = {"http": [], "https": [], "socks4": [], "socks5": []}
    with open(filename, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if len(row) < 2:
                continue
            proxy, ptype = row[0], row[1].lower()
            if ptype in proxies:
                proxies[ptype].append(proxy)
    return proxies


def check_proxy(proxy, proxy_type):
    test_url = "http://httpbin.org/ip"
    if proxy_type == "https":
        test_url = "https://httpbin.org/ip"
    proxies = {}
    start_time = time.time()

    try:
        if proxy_type in ["http", "https"]:
            proxies = {"http": f"http://{proxy}", "https": f"https://{proxy}"}
            response = requests.get(test_url, proxies=proxies, timeout=5)
        else:
            ip, port = proxy.split(":")
            socks_type = socks.SOCKS4 if proxy_type == "socks4" else socks.SOCKS5
            socks.set_default_proxy(socks_type, ip, int(port))
            socket.socket = socks.socksocket
            response = requests.get(test_url, timeout=5)

        if response.status_code == 200:
            ping = round(time.time() - start_time, 2)
            print(f"{Fore.GREEN}[✔] {proxy_type.upper()} {proxy} - Working (Ping: {ping}s){Style.RESET_ALL}")

            return proxy, proxy_type, ping
    except Exception as e:
        print(f"{Fore.RED}[✖] {proxy_type.upper()} {proxy} - Failed{Style.RESET_ALL}")
    return None


def main():
    proxy_file = "proxylist.csv"  # فایل ورودی CSV
    proxy_lists = load_proxies(proxy_file)

    all_proxies = [(proxy, ptype) for ptype, proxies in proxy_lists.items() for proxy in proxies]

    working_proxies = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(lambda p: check_proxy(p[0], p[1]), all_proxies)
        for result in results:
            if result:
                working_proxies.append(result)

    print("\nWorking Proxies:")
    for proxy, ptype, ping in working_proxies:
        print(f"{ptype.upper()} {proxy} - Ping: {ping}s")


if __name__ == "__main__":
    main()
