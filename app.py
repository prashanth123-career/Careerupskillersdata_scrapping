import os
import time
import requests
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
import io
from io import BytesIO
import base64

# Streamlit Config
st.set_page_config(page_title="OSC Seeds Scraper", layout="wide")

# Constants
BASE_URL = "https://www.OSCseeds.com"
OUTPUT_FOLDER = "data"
EXCEL_FILE = "products.xlsx"
IMAGE_FOLDER = "images"

# Initialize session state
if 'scraped_data' not in st.session_state:
    st.session_state.scraped_data = None

# --- Helper Functions ---
@st.cache_resource
def get_driver():
    """Cached ChromeDriver instance for Streamlit"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def setup_folders():
    """Create necessary folders"""
    os.makedirs(IMAGE_FOLDER, exist_ok=True)

def mock_scrape_product(url):
    """Mock scraping function for demo purposes"""
    return {
        'name': f"Product {int(time.time()) % 1000}",
        'price': f"${(time.time() % 50):.2f}",
        'sku': f"SKU-{int(time.time()) % 10000}",
        'description': "Sample product description",
        'image_url': "https://via.placeholder.com/300",
        'product_url': url
    }

def download_image(url, filename):
    """Download and save image with error handling"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        img_path = os.path.join(IMAGE_FOLDER, f"{filename}.jpg")
        with open(img_path, 'wb') as f:
            f.write(response.content)
        return img_path
    except Exception as e:
        st.warning(f"Couldn't download image: {str(e)}")
        return None

# --- Streamlit UI ---
st.title("🌱 OSC Seeds Product Scraper")
st.markdown("""
This tool extracts product data from OSCseeds.com.  
For demonstration purposes, this uses mock data.  
To scrape the real website, modify the `scrape_product()` function.
""")

with st.form("scraper_config"):
    col1, col2 = st.columns(2)
    with col1:
        category = st.selectbox("Category", ["Vegetables", "Flowers", "Herbs", "Fruits"])
    with col2:
        max_products = st.slider("Products to scrape", 1, 50, 5)
    
    if st.form_submit_button("Start Scraping", type="primary"):
        with st.spinner("Scraping in progress..."):
            try:
                setup_folders()
                driver = get_driver()
                
                # Mock product URLs (replace with real scraping)
                product_urls = [f"{BASE_URL}/{category.lower()}/{i}" for i in range(max_products)]
                
                results = []
                progress_bar = st.progress(0)
                
                for i, url in enumerate(product_urls):
                    # Update progress
                    progress = (i + 1) / len(product_urls)
                    progress_bar.progress(progress)
                    
                    # Mock scraping (replace with real implementation)
                    product_data = mock_scrape_product(url)
                    
                    # Download image
                    if product_data['image_url']:
                        product_data['image_path'] = download_image(
                            product_data['image_url'],
                            product_data['sku'] or f"product_{i}"
                        )
                    
                    results.append(product_data)
                
                # Save to DataFrame
                df = pd.DataFrame(results)
                st.session_state.scraped_data = df
                
                st.success(f"Successfully scraped {len(df)} products!")
                st.balloons()
                
            except Exception as e:
                st.error(f"Scraping failed: {str(e)}")
            finally:
                if 'driver' in locals():
                    driver.quit()

# Display results if available
if st.session_state.scraped_data is not None:
    st.subheader("Scraped Data Preview")
    st.dataframe(st.session_state.scraped_data, use_container_width=True)
    
    # Export options
    st.subheader("Export Data")
    col1, col2 = st.columns(2)
    
    with col1:
        # Excel export
        excel_buffer = BytesIO()
        st.session_state.scraped_data.to_excel(excel_buffer, index=False)
        st.download_button(
            label="Download Excel",
            data=excel_buffer.getvalue(),
            file_name=EXCEL_FILE,
            mime="application/vnd.ms-excel"
        )
    
    with col2:
        # CSV export
        csv_buffer = BytesIO()
        st.session_state.scraped_data.to_csv(csv_buffer, index=False)
        st.download_button(
            label="Download CSV",
            data=csv_buffer.getvalue(),
            file_name="products.csv",
            mime="text/csv"
        )
    
    # Display sample images
    if 'image_path' in st.session_state.scraped_data.columns:
        st.subheader("Sample Images")
        cols = st.columns(3)
        for idx, row in st.session_state.scraped_data.head(3).iterrows():
            if row['image_path'] and os.path.exists(row['image_path']):
                cols[idx%3].image(row['image_path'], caption=row['name'], width=200)
