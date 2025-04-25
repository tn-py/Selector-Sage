import logging
import os
import json
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai = OpenAI(api_key=OPENAI_API_KEY)

def analyze_page_structure(parsed_data):
    """
    Analyze the parsed page data using OpenAI to identify CSS selectors for products.
    
    Args:
        parsed_data (dict): Parsed webpage data including HTML, potential product elements, etc.
        
    Returns:
        dict: Identified CSS selectors for product title, URL, image, and price
    """
    try:
        # Prepare prompt for OpenAI
        system_prompt = """
        You are an expert web scraper assistant. Your task is to analyze the HTML structure 
        of a webpage and identify the CSS selectors for key product elements.
        
        CRITICAL GUIDELINES:
        1. The product_container selector MUST be specific to actual product items, not general page elements.
           NEVER use broad selectors like "div.container", "div.wrapper", or "div.row" - these are page structure elements.
           Products are almost always in elements with classes containing "product", "item", "card", etc.
           
        2. Product containers typically contain ALL of: title, URL, image, and price in a repeated pattern.
           If an element doesn't contain all or most of these, it's likely NOT a product container.
           
        3. Be precise! Use class names whenever possible (e.g., "div.product-item" instead of just "div").
           Avoid broad tag selectors like "div" or "li" without classes - they will match too many non-product elements.
           
        4. Study the HTML to find REPEATED PATTERNS that represent individual products.
           Products are usually displayed in a grid, list, or carousel with consistent formatting.
           
        5. If you can't identify a clear pattern for products, set all selectors to null rather than guessing.
           
        6. For e-commerce sites, the key product elements should be within the SAME CONTAINER for each product.
        
        The elements to identify are:
        1. Product title
        2. Product URL (link to product details)
        3. Product image URL
        4. Product price
        5. Pagination links (particularly "next page" links)
        
        IMPORTANT GUIDELINES FOR PAGINATION:
        - Avoid selecting pagination links that use JavaScript (href="javascript:..." or href="#")
        - Look for proper links with actual URL paths or query parameters
        - For "next page" links, look for elements containing text/symbols like "Next", "»", "→", etc.
        - If no proper pagination links are found, return null for pagination_next
        
        IMPORTANT GUIDELINES FOR PRODUCT ELEMENTS:
        - Make selectors as specific as possible to avoid capturing non-product elements
        - For prices, target only the main price, not "from" prices, "sale" prices, etc.
        - For images, target the main product image, not thumbnails or decorative images
        - For URLs, ensure they point to the product detail page
        
        Respond with a JSON object in the following format:
        {
            "product_container": "CSS selector for the container of each product",
            "product_title": "CSS selector for the product title within the container",
            "product_url": "CSS selector for the product URL within the container",
            "product_image": "CSS selector for the product image within the container",
            "product_price": "CSS selector for the product price within the container",
            "pagination_next": "CSS selector for the next page button/link (if available)"
        }
        
        Make your selectors as precise as possible. If you cannot identify an element, use null for its value.
        """
        
        # Extract the most relevant information to send to the AI
        # We'll limit the HTML content to avoid token limit issues
        html_sample = parsed_data.get("raw_html", "")[:15000]  # First 15K characters should be enough for analysis
        
        # Create user message
        user_message = f"""
        Page Title: {parsed_data.get('title', 'No title')}
        URL: {parsed_data.get('base_url', 'No URL')}
        
        Possible Product Elements:
        {json.dumps(parsed_data.get('possible_product_elements', []), indent=2)}
        
        Possible Pagination Elements:
        {json.dumps(parsed_data.get('possible_pagination', []), indent=2)}
        
        HTML Sample (truncated for brevity):
        ```html
        {html_sample}
        ```
        
        Based on the above information, identify the CSS selectors for product elements.
        
        IMPORTANT INSTRUCTIONS:
        
        1. Very importantly, the product_container selector MUST be specific to actual product items, not general page layout elements.
           Avoid using broad selectors like "div.container" or "div.row" that might capture navigation or other non-product elements.
           Look for elements that repeat for each individual product, such as "div.product-item", "li.product", "div.product-card", etc.
           
        2. Each product item should typically have ALL of these elements: title, URL, image, and price.
           If you don't see all these within the same container, you're looking at the wrong elements!
           
        3. For product containers, use the most specific selector possible (e.g., 'div.product-card' or 'li.product-item').
           Check that this selector ONLY matches actual product items, not navigation or other page elements.
           
        4. For selectors like product title, URL, image, and price, make them relative to the product container.
           For example, if the container is 'div.product', the title might be 'h3' (not 'div.product h3').
        
        5. Be careful with pagination links - many sites use JavaScript-based pagination (href="javascript:..." or href="#") 
           which will not work with our scraper. Only select real links with actual URLs.
        
        6. If there are multiple product layouts on the page, focus on the main product grid/list,
           not promotional sections or recommendations.
        
        7. If you cannot confidently identify pagination that's based on real URLs (not JavaScript),
           set pagination_next to null.
           
        8. Typical product selectors often look like these patterns:
           - Container: div.product, li.product-item, div.product-card, article.product
           - Title: h2.product-title, h3.title, .product-name, a.product-link
           - URL: a.product-link, .product-title a, .product-name a
           - Image: img.product-image, .product-thumbnail img, .product-img img
           - Price: span.price, .product-price, .price-box .price, .amount
        """
        
        # Query OpenAI
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"},
            max_tokens=1000
        )
        
        # Parse the response
        result = json.loads(response.choices[0].message.content)
        logger.debug(f"AI Analysis Result: {result}")
        
        return result
    
    except Exception as e:
        logger.error(f"Error analyzing page structure with AI: {str(e)}")
        return None
