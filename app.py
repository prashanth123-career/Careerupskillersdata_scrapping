import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
from io import BytesIO

# Streamlit App Config
st.set_page_config(page_title="OSC Seeds Scraper", page_icon="🌱")

def scrape_with_requests(url):
    """Scrape product data using requests and BeautifulSoup"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Mock data extraction - replace with actual selectors for OSCseeds.com
        products = []
        for product in soup.select('.product-item'):  # Update selector
            products.append({
                'name': product.select_one('.product-name').text.strip() if product.select_one('.product-name') else 'N/A',
                'price': product.select_one('.price').text.strip() if product.select_one('.price') else 'N/A',
                'url': url
            })
        
        return products
    
    except Exception as e:
        st.error(f"Error scraping {url}: {str(e)}")
        return []

# Streamlit UI
st.title("🌱 OSC Seeds Product Scraper")
st.write("This version uses requests instead of Selenium for better compatibility with Streamlit Cloud.")

with st.form("scraper_form"):
    url = st.text_input("Enter OSCseeds.com category URL", "https://www.OSCseeds.com/vegetables")
    submit = st.form_submit_button("Start Scraping")

if submit:
    with st.spinner("Scraping in progress..."):
        try:
            products = scrape_with_requests(url)
            
            if products:
                df = pd.DataFrame(products)
                st.success(f"Found {len(df)} products!")
                st.dataframe(df)
                
                # Excel Download
                output = BytesIO()
                df.to_excel(output, index=False)
                st.download_button(
                    label="Download Excel",
                    data=output.getvalue(),
                    file_name="osc_products.xlsx",
                    mime="application/vnd.ms-excel"
                )
            else:
                st.warning("No products found. Check the URL or website structure.")
                
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
