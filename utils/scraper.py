import logging
import requests
import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import trafilatura

logger = logging.getLogger(__name__)

def fetch_webpage_content(url):
    """
    Fetch HTML content from the provided URL.
    
    Args:
        url (str): The URL to fetch content from
        
    Returns:
        str: HTML content of the page or None if failed
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logger.error(f"Error fetching URL {url}: {str(e)}")
        return None

def get_readable_content(html_content):
    """
    Extract readable text content from HTML using trafilatura.
    
    Args:
        html_content (str): Raw HTML content
        
    Returns:
        str: Extracted readable content
    """
    try:
        return trafilatura.extract(html_content)
    except Exception as e:
        logger.error(f"Error extracting readable content: {str(e)}")
        return ""

def parse_html(html_content, base_url):
    """
    Parse HTML content to extract relevant information for analysis.
    
    Args:
        html_content (str): HTML content of the page
        base_url (str): Base URL of the page
        
    Returns:
        dict: Parsed data including raw HTML, readable content, and metadata
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract title
        title = soup.title.string if soup.title else "No title"
        
        # Get readable content
        readable_content = get_readable_content(html_content)
        
        # Find all links
        links = []
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            # Convert relative URLs to absolute
            if not bool(urlparse(href).netloc):
                href = urljoin(base_url, href)
            links.append(href)
        
        # Find all images
        images = []
        for img_tag in soup.find_all('img', src=True):
            src = img_tag['src']
            if not bool(urlparse(src).netloc):
                src = urljoin(base_url, src)
            alt = img_tag.get('alt', '')
            images.append({"src": src, "alt": alt})
        
        # Check if it looks like a product listing page
        possible_product_elements = []
        
        # Look for possible product containers - focus on more specific product identifiers
        product_containers = []
        
        # First, try to find containers with common product class names
        product_class_keywords = ['product', 'item', 'card', 'listing', 'goods', 'merchandise']
        for element in soup.find_all(['div', 'li', 'article', 'section'], class_=True):
            classes = ' '.join(element.get('class', []))
            if any(keyword in classes.lower() for keyword in product_class_keywords):
                product_containers.append(element)
        
        # If no product-specific classes found, look for repeating patterns
        if not product_containers:
            # Look for divs/elements that might contain product information
            candidates = soup.find_all(['div', 'li', 'article'], class_=True)
            for container in candidates:
                # Check if it has typical product elements
                has_image = bool(container.find('img'))
                has_price = bool(container.find(text=lambda t: '$' in t or '€' in t or '£' in t or 'price' in t.lower() if t else False))
                has_title = bool(container.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']))
                has_link = bool(container.find('a'))
                
                if ((has_image and has_price) or 
                    (has_image and has_title) or 
                    (has_title and has_price) or
                    (has_link and has_image)):
                    product_containers.append(container)
        
        # Process the identified containers
        for container in product_containers:
            # Check what product elements it has
            has_image = bool(container.find('img'))
            has_price = bool(container.find(text=lambda t: '$' in t or '€' in t or '£' in t or 'price' in t.lower() if t else False))
            has_title = bool(container.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']) or container.find(class_=lambda c: c and ('title' in c.lower() or 'name' in c.lower())))
            has_link = bool(container.find('a'))
            
            # Get CSS path
            path = get_css_path(container)
            if path:
                possible_product_elements.append({
                    "path": path,
                    "has_image": has_image,
                    "has_price": has_price,
                    "has_title": has_title,
                    "has_link": has_link,
                    "num_children": len(container.find_all()),
                    "element_type": container.name,
                    "class_names": container.get('class', [])
                })
        
        # Identify possible pagination elements
        possible_pagination = []
        
        # Look for standard pagination containers
        pagination_candidates = soup.find_all(['div', 'nav', 'ul', 'ol'], class_=True)
        
        for candidate in pagination_candidates:
            # Check if it has page numbers or pagination links
            links = candidate.find_all('a')
            
            # Look for various pagination indicators
            pagination_indicators = [
                'page', 'pag', 'next', 'weiter', 'siguiente', 'suivant', 
                'arrow', 'chevron', '»', '>', '›', 'forward'
            ]
            
            # Check links for pagination indicators
            has_pagination_indicator = False
            for link in links:
                # Check href attribute
                href = link.get('href', '')
                if any(indicator in href.lower() for indicator in pagination_indicators):
                    has_pagination_indicator = True
                    break
                    
                # Check text content
                text = link.get_text(strip=True)
                if any(indicator in text.lower() for indicator in pagination_indicators):
                    has_pagination_indicator = True
                    break
                    
                # Check for common pagination classes
                classes = link.get('class', [])
                class_str = ' '.join(classes).lower()
                if any(indicator in class_str for indicator in pagination_indicators):
                    has_pagination_indicator = True
                    break
                    
                # Check for page numbers pattern (multiple sequential numbers)
                if text.isdigit() and len(links) > 2 and any(l.get_text(strip=True).isdigit() for l in links if l != link):
                    has_pagination_indicator = True
                    break
            
            if has_pagination_indicator:
                # Try to find the next page link specifically
                next_link = None
                
                # Look for "next", "»", ">" text or class indicators
                for link in links:
                    text = link.get_text(strip=True).lower()
                    classes = ' '.join(link.get('class', [])).lower()
                    href = link.get('href', '')
                    
                    # Check for next page indicators
                    if (text in ['next', 'siguiente', 'suivant', 'weiter', '»', '>', '›']) or \
                       any(n in classes for n in ['next', 'arrow-right', 'forward', 'chevron-right']) or \
                       re.search(r'page=(\d+)', href):
                        next_link = link
                        break
                
                # If found a specific next link, add its CSS path
                if next_link:
                    path = get_css_path(next_link)
                    if path:
                        possible_pagination.append(path)
                else:
                    # Otherwise add the container's CSS path
                    path = get_css_path(candidate)
                    if path:
                        possible_pagination.append(path)
                        
        # Also check for standalone next links (not in obvious pagination containers)
        standalone_next_links = soup.find_all('a', string=re.compile(r'next|more|load more|show more|›|»|>', re.IGNORECASE))
        for link in standalone_next_links:
            path = get_css_path(link)
            if path and path not in possible_pagination:
                possible_pagination.append(path)
        
        return {
            "title": title,
            "base_url": base_url,
            "raw_html": html_content,
            "readable_content": readable_content,
            "links": links,
            "images": images,
            "possible_product_elements": possible_product_elements,
            "possible_pagination": possible_pagination
        }
        
    except Exception as e:
        logger.error(f"Error parsing HTML: {str(e)}")
        return {
            "title": "Error parsing page",
            "base_url": base_url,
            "raw_html": html_content,
            "readable_content": "",
            "links": [],
            "images": [],
            "possible_product_elements": [],
            "possible_pagination": []
        }

def get_css_path(element):
    """
    Generate a CSS selector path for an element.
    
    Args:
        element (BeautifulSoup tag): Element to generate path for
        
    Returns:
        str: CSS selector path
    """
    try:
        # Try to use class if available
        if element.get('class'):
            class_name = '.'.join(element['class'])
            return f"{element.name}.{class_name}"
        
        # Try to use id if available
        if element.get('id'):
            return f"#{element['id']}"
        
        # Use tag name and position as fallback
        parent = element.parent
        if parent:
            siblings = parent.find_all(element.name, recursive=False)
            if len(siblings) > 1:
                index = siblings.index(element) + 1
                return f"{element.name}:nth-of-type({index})"
        
        return element.name
    except Exception as e:
        logger.error(f"Error generating CSS path: {str(e)}")
        return None
