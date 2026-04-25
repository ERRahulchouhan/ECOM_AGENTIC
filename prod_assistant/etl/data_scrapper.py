import csv
import time
import re
import os
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options

from webdriver_manager.chrome import ChromeDriverManager


class FlipkartScraper:
    def __init__(self, output_dir="data"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def create_driver(self):
        """Create Chrome driver with auto download"""
        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        return driver

    def get_top_reviews(self, product_url, count=2):
        """Get top reviews of a product"""
        driver = self.create_driver()

        if not product_url.startswith("http"):
            driver.quit()
            return "No reviews found"

        try:
            driver.get(product_url)
            time.sleep(4)

            # Close login popup
            try:
                driver.find_element(By.XPATH, "//button[contains(text(), '✕')]").click()
                time.sleep(1)
            except:
                pass

            # Scroll to load reviews
            for _ in range(4):
                ActionChains(driver).send_keys(Keys.END).perform()
                time.sleep(1.5)

            soup = BeautifulSoup(driver.page_source, "html.parser")
            review_blocks = soup.select("div._27M-vq, div.col.EPCmJX, div._6K-7Co")

            seen = set()
            reviews = []

            for block in review_blocks:
                text = block.get_text(separator=" ", strip=True)
                if text and text not in seen:
                    reviews.append(text)
                    seen.add(text)

                if len(reviews) >= count:
                    break

        except Exception as e:
            print("Review error:", e)
            reviews = []

        driver.quit()
        return " || ".join(reviews) if reviews else "No reviews found"

    def scrape_flipkart_products(self, query, max_products=1, review_count=2):
        """Scrape products"""
        driver = self.create_driver()

        search_url = f"https://www.flipkart.com/search?q={query.replace(' ', '+')}"
        driver.get(search_url)
        time.sleep(4)

        # Close popup
        try:
            driver.find_element(By.XPATH, "//button[contains(text(), '✕')]").click()
        except:
            pass

        time.sleep(2)
        products = []

        items = driver.find_elements(By.CSS_SELECTOR, "div[data-id]")[:max_products]

        for item in items:
            try:
                title = item.find_element(By.CSS_SELECTOR, "div.RG5Slk").text.strip()
                price = item.find_element(By.CSS_SELECTOR, "div.QiMO5r").text.strip()
                rating = item.find_element(By.CSS_SELECTOR, "div.MKiFS6").text.strip()
                reviews_text = item.find_element(By.CSS_SELECTOR, "span.PvbNMB").text.strip()
                price = price.replace("₹", "").replace(",", "")
                match = re.search(r"\d+(,\d+)?(?=\s+Reviews)", reviews_text)
                total_reviews = match.group(0) if match else "N/A"

                link_el = item.find_element(By.CSS_SELECTOR, "a[href*='/p/']")
                href = link_el.get_attribute("href")

                product_link = href if href.startswith("http") else "https://www.flipkart.com" + href

                match = re.findall(r"/p/(itm[0-9A-Za-z]+)", href)
                product_id = match[0] if match else "N/A"

            except Exception as e:
                print("Item error:", e)
                continue

            # Get reviews
            top_reviews = self.get_top_reviews(product_link, count=review_count)

            products.append([
                product_id,
                title,
                rating,
                total_reviews,
                price,
                top_reviews
            ])

        driver.quit()
        return products

    def save_to_csv(self, data, filename="product_reviews.csv"):
        """Save to CSV"""
        # path = os.path.join(self.output_dir, filename)
        
        
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        print("Base dir:", base_dir)
        
        path = os.path.join(base_dir, "", filename)

        os.makedirs(os.path.dirname(path), exist_ok=True)

        print("Saving to:", path)  # debug
        print("datadata", data)
        
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["product_id", "product_title", "rating", "total_reviews", "price", "top_reviews"])
            writer.writerows(data)


# ✅ Run scraper
if __name__ == "__main__":
    scraper = FlipkartScraper()

    data = scraper.scrape_flipkart_products(
        query="iphone 15",
        max_products=2,
        review_count=2
    )

    scraper.save_to_csv(data)

    print("✅ Done! Data saved.")