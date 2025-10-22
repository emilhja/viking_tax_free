import time

import pandas as pd
from playwright.sync_api import sync_playwright

BASE_URL = "https://www.vikingline.se/ombord/taxfree-shopping/helsingfors/vin/"

def scrape_product_details_in_same_window(product_id, page):
    url = f"{BASE_URL}{product_id}"
    print(f"Navigating to product {product_id} in the same window...")
    try:
        page.goto(url, timeout=120000)
        page.wait_for_selector("ul.list-unstyled.txfree-product-info", timeout=120000)
        content = page.inner_text("ul.list-unstyled.txfree-product-info")
        lines = content.split('\n')
        key_map = {
            "Passar till": "food_pairing",
            "Karaktär": "character",
            "Druva": "grape_variety",
            "Land": "country",
            "Område": "region",
            "Producent": "producer",
            "År": "year",
            "Volym": "volume",
            "Alkohol": "alcohol"
        }
        details = {}
        current_key = None
        current_value = []
        for line in lines:
            if line in key_map:
                if current_key:
                    details[key_map[current_key]] = ', '.join(current_value)
                current_key = line
                current_value = []
            elif current_key:
                current_value.append(line.strip())
        if current_key and current_value:
            details[key_map[current_key]] = ', '.join(current_value)

        print("Waiting 10 seconds before next request...")
        time.sleep(10)  # polite 10 seconds delay

        return details
    except Exception as e:
        print(f"Error navigating to product {product_id}: {e}")
        return {}

def main(num_rows=None):
    input_csv = "viking_wines_summary_incomplete.csv"
    output_csv = "viking_wines_in_same_window.csv"
    df = pd.read_csv(input_csv)
    if num_rows is not None:
        df = df.head(num_rows)
    details_list = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        for _, row in df.iterrows():
            product_id = row.get('id')
            if pd.notna(product_id):
                details = scrape_product_details_in_same_window(product_id, page)
                details_list.append(details)
            else:
                details_list.append({})
        browser.close()

    details_df = pd.DataFrame(details_list)
    combined_df = pd.concat([df, details_df], axis=1)
    combined_df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"Saved detailed product data in the same window to {output_csv}")

if __name__ == "__main__":
    main(70)  # run for first 20 rows
