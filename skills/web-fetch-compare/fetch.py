import requests

def fetch_price(url):
    r = requests.get(url)
    return r.text[:1000]

if __name__ == "__main__":
    print(fetch_price("https://supermercadosrd.com"))