import json

import pandas as pd
import requests
from playwright.sync_api import sync_playwright


class VikingLineScraper:
    def __init__(self):
        self.base_url = "https://www.vikingline.se/api/taxfree/articles"
        self.main_page = "https://www.vikingline.se/ombord/taxfree-shopping/helsingfors/vin/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'sv-SE,sv;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': self.main_page,
            'Origin': 'https://www.vikingline.se',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        })

    def get_cookies_from_playwright(self, url: str):
        print("Opening browser with Playwright (non-headless)...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            page.goto(url, timeout=60000)
            print("Page should be loaded now. Interact if necessary (accept cookies, etc).")
            input("Press Enter in the terminal once you see the Vin header and product list...")
            cookies = context.cookies()
            browser.close()
            return cookies

    def set_cookies_to_session(self, cookies, domain=".vikingline.se"):
        for cookie in cookies:
            cookie_dict = {
                'name': cookie['name'],
                'value': cookie['value'],
                'domain': domain,
                'path': cookie.get('path', '/'),
                'expires': cookie.get('expires', None),
                'secure': cookie.get('secure', False),
                'rest': {'HttpOnly': cookie.get('httpOnly', False)}
            }
            self.session.cookies.set(**cookie_dict)
        print(f"Injected {len(cookies)} cookies into requests session")

    def visit_main_page(self):
        try:
            cookies = self.get_cookies_from_playwright(self.main_page)
            if cookies:
                self.set_cookies_to_session(cookies)
                return True
            return False
        except Exception as e:
            print(f"Error getting cookies from Playwright: {e}")
            return False

    def get_products(self, ship_ids: str = "4,7", category_id: int = 7,
                     language: str = "sv", sek_only: bool = False):
        params = {
            'shipId': ship_ids,
            'userCategoryId': category_id,
            'language': language,
            'sekOnly': str(sek_only).lower()
        }
        try:
            response = self.session.get(self.base_url, params=params, timeout=15)
            print(f"Response status: {response.status_code}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error {response.status_code}: {e}")
            print(f"Response content: {response.text[:500]}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
            return None

    def parse_products(self, data):
        if not data:
            return []
        products = []
        items = data.get('articles', []) if isinstance(data, dict) else data
        for item in items:
            product = {
                'id': item.get('id'),
                'name': item.get('name') or item.get('title'),
                'description': item.get('description'),
                'price_sek': item.get('priceSEK') or item.get('price') or item.get('priceSek'),
                'price_eur': item.get('priceEUR') or item.get('priceEur'),
                'category': item.get('category') or item.get('categoryName'),
                'brand': item.get('brand'),
                'country': item.get('country') or item.get('countryOfOrigin'),
                'volume': item.get('volume') or item.get('size'),
                'alcohol_percentage': item.get('alcoholPercentage') or item.get('alcohol'),
                'image_url': item.get('imageUrl') or item.get('image') or item.get('imageURL'),
                'in_stock': item.get('inStock') or item.get('available'),
                'article_number': item.get('articleNumber') or item.get('sku')
            }
            products.append(product)
        return products

    def save_to_csv(self, products, filename='viking_wines.csv'):
        if products:
            df = pd.DataFrame(products)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"Saved {len(products)} products to {filename}")
        else:
            print("No products to save")

    def save_to_json(self, data, filename='viking_wines_raw.json'):
        if data:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Saved raw data to {filename}")

def main():
    scraper = VikingLineScraper()

    # Open browser, confirm page loaded, extract cookies
    if not scraper.visit_main_page():
        print("Failed to get cookies via Playwright. Exiting.")
        return

    print("\nFetching Viking Line wine products...")

    data = scraper.get_products(
        ship_ids="4,7",
        category_id=7,
        language="sv"
    )

    if data:
        # Save raw JSON
        scraper.save_to_json(data)

        # Parse and save to CSV
        products = scraper.parse_products(data)
        scraper.save_to_csv(products)

        print(f"\nFound {len(products)} products")
        if products:
            print("\nSample product:")
            print(json.dumps(products[0], indent=2, ensure_ascii=False))
    else:
        print("\nFailed to fetch data from API")

if __name__ == "__main__":
    main()