import json
import time
from typing import Dict, List

import pandas as pd
import requests


class VikingLineScraper:
    def __init__(self):
        self.base_url = "https://www.vikingline.se/api/taxfree/articles"
        self.main_page = "https://www.vikingline.se/ombord/taxfree-shopping/helsingfors/vin/"
        self.session = requests.Session()
        
        # More complete browser headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'sv-SE,sv;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.vikingline.se/ombord/taxfree-shopping/helsingfors/vin/',
            'Origin': 'https://www.vikingline.se',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        })
    
    def visit_main_page(self):
        """Visit the main page first to get cookies"""
        try:
            print("Visiting main page to get cookies...")
            response = self.session.get(self.main_page, timeout=10)
            response.raise_for_status()
            print(f"Main page visited successfully, got cookies: {len(self.session.cookies)} cookies")
            time.sleep(1)  # Be polite, wait a bit
            return True
        except Exception as e:
            print(f"Warning: Could not visit main page: {e}")
            return False
    
    def get_products(self, ship_ids: str = "4,7", category_id: int = 7, 
                     language: str = "sv", sek_only: bool = False) -> Dict:
        """
        Fetch products from Viking Line API
        
        Args:
            ship_ids: Comma-separated ship IDs (default: "4,7" for Helsinki route)
            category_id: User category ID (7 appears to be wine)
            language: Language code (sv, fi, en)
            sek_only: Whether to show only SEK prices
        """
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
    
    def parse_products(self, data: Dict) -> List[Dict]:
        """Parse product data into a list of dictionaries"""
        if not data:
            return []
        
        products = []
        
        # The structure may vary, adjust based on actual API response
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and 'articles' in data:
            items = data['articles']
        elif isinstance(data, dict) and 'products' in data:
            items = data['products']
        elif isinstance(data, dict) and 'items' in data:
            items = data['items']
        else:
            # If we can't find a clear list, try to work with the whole data
            print(f"Data structure: {list(data.keys()) if isinstance(data, dict) else type(data)}")
            items = [data]
        
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
    
    def save_to_csv(self, products: List[Dict], filename: str = 'viking_wines.csv'):
        """Save products to CSV file"""
        if products:
            df = pd.DataFrame(products)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"Saved {len(products)} products to {filename}")
        else:
            print("No products to save")
    
    def save_to_json(self, data: Dict, filename: str = 'viking_wines_raw.json'):
        """Save raw JSON response"""
        if data:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Saved raw data to {filename}")

def main():
    scraper = VikingLineScraper()
    
    # First visit the main page to get cookies
    scraper.visit_main_page()
    
    print("\nFetching Viking Line wine products...")
    
    # Category IDs you might want to try:
    # 7 = Wine (from your URL)
    # Other categories might include spirits, beer, etc.
    
    data = scraper.get_products(
        ship_ids="4,7",  # Helsinki route ships
        category_id=7,    # Wine category
        language="sv"
    )
    
    if data:
        # Save raw JSON
        scraper.save_to_json(data)
        
        # Parse and save to CSV
        products = scraper.parse_products(data)
        scraper.save_to_csv(products)
        
        # Print summary
        print(f"\nFound {len(products)} products")
        if products:
            print("\nSample product:")
            print(json.dumps(products[0], indent=2, ensure_ascii=False))
    else:
        print("\nFailed to fetch data. The API might require:")
        print("1. Visiting the site in a real browser first")
        print("2. Additional authentication/tokens")
        print("3. Using a different approach like Selenium")

if __name__ == "__main__":
    main()