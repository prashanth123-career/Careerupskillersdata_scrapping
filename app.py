import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
from io import BytesIO
from PIL import Image

# Streamlit Config
st.set_page_config(page_title="OSC Seeds Scraper", layout="wide")

# Create image folder
IMAGE_FOLDER = "images"
os.makedirs(IMAGE_FOLDER, exist_ok=True)

def get_valid_urls():
    return {
        "Vegetables": "https://www.oscseeds.com/category/vegetable-seeds/",
        "Flowers": "https://www.oscseeds.com/category/flower-seeds/",
        "Herbs": "https://www.oscseeds.com/category/herb-seeds/",
        "All Products": "https://www.oscseeds.com/product-category/all-products/"
    }

def scrape_osc_seeds(url, max_products=10):
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        product_links = []
        for product in soup.select('div.product-grid-item a.woocommerce-LoopProduct-link'):
            href = product.get('href')
            if href and '/product/' in href:
                product_links.append(href)
                if len(product_links) >= max_products:
                    break

        if not product_links:
            return None, "No products found."

        all_products = []

        for i, product_url in enumerate(product_links):
            try:
                time.sleep(1)
                prod_resp = requests.get(product_url, headers=headers)
                prod_resp.raise_for_status()
                prod_soup = BeautifulSoup(prod_resp.text, 'html.parser')

                title = prod_soup.find('h1', class_='product_title').get_text(strip=True) if prod_soup.find('h1', class_='product_title') else "N/A"
                price = prod_soup.find('p', class_='price').get_text(strip=True) if prod_soup.find('p', class_='price') else "N/A"
                sku = prod_soup.find('span', class_='sku').get_text(strip=True) if prod_soup.find('span', class_='sku') else "N/A"
                desc = prod_soup.find('div', class_='woocommerce-product-details__short-description')
                description = desc.get_text(strip=True) if desc else "N/A"

                # Image
                img_tag = prod_soup.select_one("div.woocommerce-product-gallery__image img")
                image_url = img_tag.get("src") if img_tag else ""
                image_filename = ""
                if image_url:
                    image_name = os.path.basename(image_url.split("?")[0])
                    image_filename = os.path.join(IMAGE_FOLDER, image_name)
                    img_data = requests.get(image_url).content
                    with open(image_filename, "wb") as img_file:
                        img_file.write(img_data)

                # Specs
                specs = {}
                spec_table = prod_soup.find('div', class_='woocommerce-Tabs-panel')
                if spec_table:
                    for row in spec_table.find_all('tr'):
                        cols = row.find_all('td')
                        if len(cols) == 2:
                            specs[cols[0].get_text(strip=True)] = cols[1].get_text(strip=True)

                all_products.append({
                    "Product Name": title,
                    "Price": price,
                    "SKU": sku,
                    "Description": description,
                    "Category": url.split("/")[-2].replace("-", " ").title(),
                    "Image File": image_filename,
                    "Product URL": product_url,
                    "Specifications": "\n".join([f"{k}: {v}" for k, v in specs.items()])
                })

            except Exception as e:
                st.warning(f"Failed: {product_url} — {str(e)}")
                continue

        return pd.DataFrame(all_products), None

    except Exception as e:
        return None, str(e)

# Streamlit UI
st.title("🌱 OSC Seeds Product Scraper + Image Downloader")

valid_urls = get_valid_urls()

with st.form("scraper_form"):
    col1, col2 = st.columns(2)
    with col1:
        category = st.selectbox("Select Category", list(valid_urls.keys()))
    with col2:
        max_products = st.slider("Max Products", 1, 50, 10)

    if st.form_submit_button("Start Scraping"):
        with st.spinner("Scraping in progress..."):
            df, error = scrape_osc_seeds(valid_urls[category], max_products)

            if error:
                st.error(f"❌ {error}")
            elif df is not None:
                st.success(f"✅ Scraped {len(df)} products.")
                st.dataframe(df)

                # Download Excel
                excel_buffer = BytesIO()
                df.to_excel(excel_buffer, index=False)
                st.download_button("📥 Download Excel File", excel_buffer.getvalue(), file_name="osc_products.xlsx")

                st.markdown(f"📸 Images downloaded to: `{IMAGE_FOLDER}/` folder")

# Wider layout
st.markdown("""
<style>
    .main .block-container {
        max-width: 1200px;
    }
    .stDataFrame {
        width: 100% !important;
    }
</style>
""", unsafe_allow_html=True)
