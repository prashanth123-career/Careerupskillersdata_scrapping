import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import re
import zipfile
import random
from io import BytesIO
from time import sleep
from urllib.parse import urlparse
from PIL import Image

# --- CONFIG ---
REQUEST_DELAY = 1.5
IMAGE_FOLDER = "seed_images"
LOG_FILE = "scrape_log.txt"
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# --- USER AGENTS & PROXIES (FOR ROTATION) ---
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
    'Mozilla/5.0 (X11; Linux x86_64)',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)'
]
PROXIES = [
    None,  # No proxy (default)
    # Example: {"http": "http://123.123.123.123:8080", "https": "http://123.123.123.123:8080"}
]

# --- STREAMLIT CONFIG ---
st.set_page_config(page_title="OSC Seeds Scraper", layout="centered")
st.title("🌱 OSC Seeds Product Scraper")
st.markdown("Extract product data from [OSCSeeds.com](https://www.oscseeds.com) with retry & proxy support.")

# --- INPUTS ---
with st.form("scraper_inputs"):
    category_url = st.text_input(
        "Enter Product Category URL",
        "https://www.oscseeds.com/product-category/vegetables/",
        help="Example: https://www.oscseeds.com/product-category/flowers/"
    )
    max_products = st.slider("Number of products to extract", 1, 100, 10)
    max_retries = st.slider("Max retries per product (for errors)", 0, 5, 2)
    submit = st.form_submit_button("Start Scraping")

# --- MAIN SCRAPING LOGIC ---
if submit:
    if not category_url.startswith('https://www.oscseeds.com'):
        st.error("Please enter a valid OSCSeeds.com category URL")
        st.stop()

    with st.spinner(f"Scraping {max_products} products..."):
        all_products = []
        image_files = []

        def log_error(msg):
            with open(LOG_FILE, "a") as log:
                log.write(msg + "\n")

        def get_random_headers():
            return {
                'User-Agent': random.choice(USER_AGENTS),
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.oscseeds.com/'
            }

        def get_product_links(base_url, limit):
            links = []
            page = 1
            seen_links = set()
            while len(links) < limit:
                url = f"{base_url}page/{page}/" if page > 1 else base_url
                try:
                    resp = requests.get(url, headers=get_random_headers(), timeout=10, proxies=random.choice(PROXIES))
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    products = soup.select("li.product a.woocommerce-LoopProduct-link[href]")
                    if not products:
                        break
                    for p in products:
                        link = p.get('href').split('?')[0]
                        if link and link not in seen_links:
                            seen_links.add(link)
                            links.append(link)
                            if len(links) >= limit:
                                break
                    page += 1
                    sleep(REQUEST_DELAY)
                except Exception as e:
                    log_error(f"Page {page} Error: {e}")
                    break
            return links[:limit]

        def download_image(img_url, product_name):
            try:
                if not img_url.startswith('http'):
                    return ""
                response = requests.get(img_url, headers=get_random_headers(), stream=True, timeout=15, proxies=random.choice(PROXIES))
                response.raise_for_status()
                safe_name = re.sub(r'[^\w\-_\. ]', '_', product_name)[:50]
                ext = os.path.splitext(urlparse(img_url).path)[1][:4] or '.jpg'
                filename = f"{safe_name}{ext}"
                filepath = os.path.join(IMAGE_FOLDER, filename)
                with Image.open(BytesIO(response.content)) as img:
                    img.save(filepath)
                return filepath
            except Exception as e:
                log_error(f"Image download failed for {product_name}: {e}")
                return ""

        def scrape_product(url):
            for attempt in range(max_retries + 1):
                try:
                    response = requests.get(url, headers=get_random_headers(), timeout=10, proxies=random.choice(PROXIES))
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, 'html.parser')
                    name = (soup.select_one("h1.product_title") or soup.select_one("h1.entry-title")).get_text(strip=True)
                    price = (soup.select_one("p.price") or soup.select_one("span.woocommerce-Price-amount")).get_text(strip=True)
                    desc = (soup.select_one("div.woocommerce-product-details__short-description") or soup.select_one("div.product_meta") or soup.select_one("div.product_description"))
                    desc_text = desc.get_text(" ", strip=True) if desc else "N/A"
                    img = (soup.select_one("div.woocommerce-product-gallery__image img") or soup.select_one("img.wp-post-image") or soup.select_one("img.attachment-woocommerce_single"))
                    data = {
                        "Product Name": name if name else "N/A",
                        "Price": re.sub(r'\s+', ' ', price).strip() if price else "N/A",
                        "Description": desc_text,
                        "Product URL": url,
                        "Image File": ""
                    }
                    if img and img.get("src"):
                        img_path = download_image(img.get("src"), data["Product Name"])
                        data["Image File"] = os.path.basename(img_path) if img_path else ""
                        if img_path:
                            image_files.append(img_path)
                    return data
                except Exception as e:
                    log_error(f"Attempt {attempt+1} failed for {url}: {e}")
                    sleep(REQUEST_DELAY)
            return None

        links = get_product_links(category_url, max_products)
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, link in enumerate(links, 1):
            status_text.text(f"Processing {i}/{len(links)}: {link[:50]}...")
            product_data = scrape_product(link)
            if product_data:
                all_products.append(product_data)
            progress_bar.progress(i / len(links))
            sleep(REQUEST_DELAY)

        progress_bar.empty()
        status_text.empty()

        if not all_products:
            st.error("No products were scraped. Check logs in scrape_log.txt.")
            st.stop()

        df = pd.DataFrame(all_products)
        excel_file = "osc_seeds_data.xlsx"
        df.to_excel(excel_file, index=False)

        st.success(f"✅ Successfully scraped {len(df)} products!")

        with st.expander("View Scraped Data"):
            st.dataframe(df)

        col1, col2 = st.columns(2)
        with col1:
            with open(excel_file, "rb") as f:
                st.download_button(
                    "📥 Download Excel",
                    f,
                    file_name=excel_file,
                    mime="application/vnd.ms-excel",
                    help="Contains all product data including descriptions"
                )

        with col2:
            if image_files:
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for img_path in image_files:
                        zipf.write(img_path, os.path.basename(img_path))
                zip_buffer.seek(0)
                st.download_button(
                    "📦 Download Images (ZIP)",
                    data=zip_buffer,
                    file_name="osc_seeds_images.zip",
                    mime="application/zip",
                    help="Contains all product images with proper filenames"
                )
            else:
                st.warning("No images were downloaded. The website may be blocking image downloads.")

st.markdown("""
<style>
    .stDownloadButton button {
        width: 100%;
        transition: all 0.2s;
    }
    .stDownloadButton button:hover {
        transform: scale(1.02);
    }
    .stSpinner > div {
        justify-content: center;
    }
    .stDataFrame {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)
