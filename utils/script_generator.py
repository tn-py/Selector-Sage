import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def generate_scraping_script(selectors, base_url, pagination_enabled=False, pagination_selector=""):
    """
    Generate a Python script for web scraping based on the identified selectors.
    
    Args:
        selectors (dict): Dictionary containing CSS selectors for product elements
        base_url (str): Base URL of the target website
        pagination_enabled (bool): Whether pagination should be included in the script
        pagination_selector (str): CSS selector for pagination (if provided by user)
        
    Returns:
        str: Generated Python script as a string
    """
    try:
        # Use the pagination selector from selectors if not provided and pagination is enabled
        if pagination_enabled and not pagination_selector and selectors.get('pagination_next'):
            pagination_selector = selectors.get('pagination_next')
            
        # Default to empty string if still None to avoid errors
        pagination_selector = pagination_selector or ""
        
        # Create the script components as separate strings
        script_imports = """
import requests
from bs4 import BeautifulSoup
import csv
import time
import random
import re
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
"""

        # Function definition and docstring
        max_pages = 10 if pagination_enabled else 1
        max_pages_str = "10 if pagination enabled" if pagination_enabled else "1"
        
        script_function_header = f"""
def scrape_product_data(url, max_pages={max_pages}):
    '''
    Scrape product data from the given URL.
    
    Args:
        url (str): Starting URL to scrape
        max_pages (int): Maximum number of pages to scrape (default: {max_pages_str})
        
    Returns:
        list: List of dictionaries containing product data
    '''
    products = []
    current_page = 1
    current_url = url
    
    headers = {{
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }}
    
    while current_page <= max_pages:
        print(f"Scraping page {{current_page}}: {{current_url}}")
        
        # Fetch the page
        try:
            response = requests.get(current_url, headers=headers)
            response.raise_for_status()
        except Exception as e:
            print(f"Error fetching page: {{e}}")
            break
            
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
"""

        # Product extraction part
        product_container = selectors.get('product_container', '')
        product_title = selectors.get('product_title', '')
        product_url = selectors.get('product_url', '')  
        product_image = selectors.get('product_image', '')
        product_price = selectors.get('product_price', '')
        
        script_product_extraction = f"""
        # Find all product containers
        product_containers = soup.select("{product_container}")
        
        if not product_containers:
            print("No products found on this page.")
            break
            
        # Extract product information
        for container in product_containers:
            product = {{}}
            
            # First, verify if this container looks like a product before processing
            # Skip elements that are just for navigation
            probable_nav_element = False
            container_html = str(container).lower()
            nav_indicators = ['nav', 'navigation', 'menu', 'footer', 'header', 'breadcrumb']
            if any(indicator in container_html for indicator in nav_indicators) and container.select('a') and len(container.select('a')) > 3:
                probable_nav_element = True
            
            if probable_nav_element:
                print(f"Skipping probable navigation element: {container.name}.{' '.join(container.get('class', []))}")
                continue
                
            # Try multiple approaches to find product title with better prioritization
            title_selectors = [
                "{product_title}",  # AI-detected selector
                ".product-title", ".product-name", ".title", ".name",  # Classes with name/title keywords
                "h1.product-title", "h2.product-title", "h3.product-title",  # Specific heading classes
                "h1", "h2", "h3", "h4", "h5",  # Generic headings (last resort)
                "a[title]"  # Link with title attribute
            ]
            
            title_element = None
            used_title_selector = None
            for selector in title_selectors:
                if not selector:
                    continue
                try:
                    title_element = container.select_one(selector)
                    if title_element and title_element.text.strip():
                        # Check if text is too short or too long
                        text = title_element.text.strip()
                        if 3 <= len(text) <= 200:  # Reasonable product title length
                            used_title_selector = selector
                            break
                except Exception:
                    continue
                    
            product['title'] = title_element.text.strip() if title_element else "N/A"
            
            # Try multiple approaches to find product URL - with link verification
            url_selectors = [
                "{product_url}",  # AI-detected selector
                "a.product-link", "a.details", ".product-title a", ".title a", ".name a",  # Specific link patterns
                "a:not(.pagination-link):not(.nav-link)"  # Any link that's not pagination/navigation
            ]
            
            url_element = None
            used_url_selector = None
            for selector in url_selectors:
                if not selector:
                    continue
                try:
                    links = container.select(selector)
                    for link in links:
                        if link and link.has_attr('href'):
                            href = link['href']
                            # Skip JavaScript links and anchors
                            if href.startswith('javascript:') or href == '#':
                                continue
                            # Skip navigation/utility links
                            if any(word in href.lower() for word in ['login', 'cart', 'account', 'search']):
                                continue
                            url_element = link
                            used_url_selector = selector
                            break
                    if url_element:
                        break
                except Exception:
                    continue
                    
            product['url'] = urljoin(url, url_element['href']) if url_element and url_element.has_attr('href') else "N/A"
            
            # Try multiple approaches to find product image - with image verification
            image_selectors = [
                "{product_image}",  # AI-detected selector
                ".product-image", ".product-img", ".product-photo",  # Specific image classes
                "a:first-child img", ".product-thumbnail img", ".image img",  # Common containers
                "img.product", "img.thumbnail", "img"  # Last resort - any image
            ]
            
            image_element = None
            used_image_selector = None
            for selector in image_selectors:
                if not selector:
                    continue
                try:
                    images = container.select(selector)
                    for img in images:
                        # Check if this is a real product image (skip icons, tiny images, etc.)
                        if img.has_attr('src') or img.has_attr('data-src'):
                            # Try to get image dimensions if available
                            width = img.get('width', '')
                            height = img.get('height', '')
                            
                            # Skip very small images that are likely icons
                            if width and height and int(width) < 50 and int(height) < 50:
                                continue
                                
                            # Skip common non-product images
                            src = img.get('src', img.get('data-src', ''))
                            skip_indicators = ['icon', 'logo', 'banner', 'button', 'pixel.gif', 'spacer.gif']
                            if any(indicator in src.lower() for indicator in skip_indicators):
                                continue
                                
                            image_element = img
                            used_image_selector = selector
                            break
                    if image_element:
                        break
                except Exception:
                    continue
            
            # Process image source, handling different image source attributes
            img_src = None
            if image_element:
                # Check various image source attributes
                for attr in ['src', 'data-src', 'data-original', 'data-lazy-src', 'data-srcset']:
                    if image_element.has_attr(attr):
                        src = image_element[attr]
                        if src and not src.startswith('data:'):  # Skip data URIs
                            # For srcset, extract first URL
                            if attr == 'data-srcset':
                                src = src.split(',')[0].split(' ')[0]
                            img_src = src
                            break
                            
            product['image_url'] = urljoin(url, img_src) if img_src else "N/A"
            
            # Try multiple approaches to find product price
            price_selectors = [
                "{product_price}",  # AI-detected selector
                ".price", ".product-price", ".offer-price", ".sale-price",  # Price classes
                "span.price", "div.price", "p.price",  # Container with price class
                ".cost", ".amount", ".value",  # Other price indicators
                "*[itemprop='price']",  # Schema.org markup
                "*:contains('$')", "*:contains('€')", "*:contains('£')"  # Currency symbol
            ]
            
            price_element = None
            used_price_selector = None
            for selector in price_selectors:
                if not selector:
                    continue
                try:
                    price_candidates = container.select(selector)
                    for candidate in price_candidates:
                        text = candidate.text.strip()
                        # Simple price validation
                        if text and any(c in text for c in ['$', '€', '£', 'USD', 'EUR', 'GBP']) or re.search(r'\d+\.\d{2}', text):
                            price_element = candidate
                            used_price_selector = selector
                            break
                    if price_element:
                        break
                except Exception:
                    continue
                    
            product['price'] = price_element.text.strip() if price_element else "N/A"
            
            # Print debugging info for this product
            print(f"Debug - Product {{len(products) + 1}} info:")
            print(f"  Container: {{container.name}}.{{' '.join(container.get('class', []))}}")
            print(f"  Title: {{product['title']}}")
            print(f"  URL: {{product['url']}}")
            print(f"  Image URL: {{product['image_url']}}")
            print(f"  Price: {{product['price']}}")
            print(f"  Used selectors: title={{used_title_selector}}, url={{used_url_selector}}, image={{used_image_selector}}, price={{used_price_selector}}")
            
            # Add product to list
            products.append(product)
        
        print(f"Found {{len(product_containers)}} products on page {{current_page}}.")
"""

        # Basic pagination (no actual pagination, just break)
        script_no_pagination = """
        # No pagination, only scraping one page
        break
"""

        # Advanced pagination with multiple methods
        script_with_pagination = f"""
        # Proceed to next page if pagination is enabled
        if current_page < max_pages:
            # Try different pagination methods
            
            # Method 1: CSS Selector-based pagination
            pagination_selector = "{pagination_selector}"
            if pagination_selector:
                next_page = soup.select_one(pagination_selector)
                if next_page and next_page.has_attr('href'):
                    href = next_page['href']
                    
                    # Skip JavaScript links
                    if href.startswith('javascript:') or href == '#':
                        print("Skipping JavaScript link:", href)
                        break
                        
                    current_url = urljoin(current_url, href)
                    current_page += 1
                    
                    # Add a small delay to avoid overloading the server
                    time.sleep(random.uniform(1, 3))
                    continue
            
            # Method 2: URL Parameter-based pagination (?page=X)
            parsed_url = urlparse(current_url)
            query_params = parse_qs(parsed_url.query)
            
            # Check if 'page' parameter exists
            if 'page' in query_params:
                # Increment page number
                try:
                    current_page_num = int(query_params['page'][0])
                    query_params['page'] = [str(current_page_num + 1)]
                    
                    # Rebuild URL with new page number
                    new_query = urlencode(query_params, doseq=True)
                    new_url = urlunparse(
                        (parsed_url.scheme, parsed_url.netloc, parsed_url.path, 
                         parsed_url.params, new_query, parsed_url.fragment)
                    )
                    current_url = new_url
                    current_page += 1
                    time.sleep(random.uniform(1, 3))
                    continue
                except (ValueError, IndexError):
                    pass
            else:
                # Try adding page parameter if it doesn't exist
                query_params['page'] = ['2']  # Start with page 2
                new_query = urlencode(query_params, doseq=True)
                new_url = urlunparse(
                    (parsed_url.scheme, parsed_url.netloc, parsed_url.path, 
                     parsed_url.params, new_query, parsed_url.fragment)
                )
                current_url = new_url
                current_page += 1
                time.sleep(random.uniform(1, 3))
                continue
                
            # Method 3: Simple path-based pagination (/page/X)
            page_pattern = re.search(r'/page/(\d+)', parsed_url.path)
            if page_pattern:
                page_num = int(page_pattern.group(1))
                new_path = re.sub(r'/page/\d+', f'/page/{{page_num + 1}}', parsed_url.path)
                new_url = urlunparse(
                    (parsed_url.scheme, parsed_url.netloc, new_path, 
                     parsed_url.params, parsed_url.query, parsed_url.fragment)
                )
                current_url = new_url
                current_page += 1
                time.sleep(random.uniform(1, 3))
                continue
                
            # If we got here, we couldn't find a way to paginate
            print("No next page found using any pagination method.")
            break
        else:
            break
"""

        # Function end and save to CSV function
        script_function_end = """
    return products


def save_to_csv(products, filename="products.csv"):
    '''
    Save product data to a CSV file.
    
    Args:
        products (list): List of product dictionaries
        filename (str): Name of the CSV file to save
    '''
    if not products:
        print("No products to save.")
        return
        
    with open(filename, 'w', newline='', encoding='utf-8') as csv_file:
        fieldnames = ['title', 'url', 'image_url', 'price']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        
        writer.writeheader()
        for product in products:
            writer.writerow(product)
            
    print(f"Saved {len(products)} products to {filename}")
"""

        # Main function
        script_main = f"""
if __name__ == "__main__":
    # URL to scrape
    target_url = "{base_url}"
    
    # Scrape product data
    products = scrape_product_data(target_url)
    
    # Save data to CSV
    save_to_csv(products)
"""

        # Combine all script parts
        script = script_imports + script_function_header + script_product_extraction
        
        # Add the appropriate pagination code
        if pagination_enabled:
            script += script_with_pagination
        else:
            script += script_no_pagination
            
        # Add the function end, CSV function and main section
        script += script_function_end + script_main
        
        return script
        
    except Exception as e:
        logger.error(f"Error generating scraping script: {str(e)}")
        return "# Error generating script\n# Please try again with different selectors"