import logging
import json
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai = OpenAI(api_key=OPENAI_API_KEY)

def extract_sample_data(html_content, selectors, base_url):
    """
    Extract sample data and HTML elements from the webpage using the provided selectors.
    
    Args:
        html_content (str): The HTML content of the webpage
        selectors (dict): Dictionary containing CSS selectors for product elements
        base_url (str): Base URL of the webpage
        
    Returns:
        list: List of sample product data with HTML elements and selectors used
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        container_selector = selectors.get('product_container', '')
        
        if not container_selector:
            logger.error("No product container selector provided")
            return []
            
        # Find product containers
        containers = soup.select(container_selector)
        if not containers:
            logger.error(f"No elements found with selector: {container_selector}")
            return []
            
        # Extract data for up to 3 products
        sample_data = []
        for i, container in enumerate(containers[:3]):  # Limit to 3 samples
            product_data = {'elements': {}}
            
            # Extract title with element info
            title_selector = selectors.get('product_title', '')
            if title_selector:
                title_element = container.select_one(title_selector)
                if title_element:
                    product_data['title'] = title_element.text.strip()
                    product_data['elements']['title'] = {
                        'selector': title_selector,
                        'html': str(title_element),
                        'value': title_element.text.strip()
                    }
                else:
                    product_data['title'] = "Not found"
                    product_data['elements']['title'] = {
                        'selector': title_selector,
                        'html': None,
                        'value': None
                    }
            else:
                product_data['title'] = "No selector"
                product_data['elements']['title'] = None
                
            # Extract URL with element info
            url_selector = selectors.get('product_url', '')
            if url_selector:
                url_element = container.select_one(url_selector)
                if url_element and url_element.has_attr('href'):
                    url_value = urljoin(base_url, url_element['href'])
                    product_data['url'] = url_value
                    product_data['elements']['url'] = {
                        'selector': url_selector,
                        'html': str(url_element),
                        'value': url_value
                    }
                else:
                    product_data['url'] = "Not found"
                    product_data['elements']['url'] = {
                        'selector': url_selector,
                        'html': None,
                        'value': None
                    }
            else:
                product_data['url'] = "No selector"
                product_data['elements']['url'] = None
                
            # Extract image URL with element info
            image_selector = selectors.get('product_image', '')
            if image_selector:
                image_element = container.select_one(image_selector)
                if image_element:
                    # Check various image source attributes
                    image_url = None
                    for attr in ['src', 'data-src', 'data-original', 'data-lazy-src']:
                        if image_element.has_attr(attr):
                            image_url = urljoin(base_url, image_element[attr])
                            break
                    
                    if image_url:
                        product_data['image_url'] = image_url
                        product_data['elements']['image'] = {
                            'selector': image_selector,
                            'html': str(image_element),
                            'value': image_url
                        }
                    else:
                        product_data['image_url'] = "Found element but no image source"
                        product_data['elements']['image'] = {
                            'selector': image_selector,
                            'html': str(image_element),
                            'value': None
                        }
                else:
                    product_data['image_url'] = "Not found"
                    product_data['elements']['image'] = {
                        'selector': image_selector,
                        'html': None,
                        'value': None
                    }
            else:
                product_data['image_url'] = "No selector"
                product_data['elements']['image'] = None
                
            # Extract price with element info
            price_selector = selectors.get('product_price', '')
            if price_selector:
                price_element = container.select_one(price_selector)
                if price_element:
                    price_value = price_element.text.strip()
                    product_data['price'] = price_value
                    product_data['elements']['price'] = {
                        'selector': price_selector,
                        'html': str(price_element),
                        'value': price_value
                    }
                else:
                    product_data['price'] = "Not found"
                    product_data['elements']['price'] = {
                        'selector': price_selector,
                        'html': None,
                        'value': None
                    }
            else:
                product_data['price'] = "No selector"
                product_data['elements']['price'] = None
                
            sample_data.append(product_data)
            
            # Stop after 3 samples
            if i >= 2:
                break
                
        return sample_data
        
    except Exception as e:
        logger.error(f"Error extracting sample data: {str(e)}")
        return []

def validate_selectors(sample_data, selectors):
    """
    Validate the extracted sample data using AI to check if each field is correct.
    Provides detailed validation including HTML element, selector, and extracted value.
    
    Args:
        sample_data (list): List of sample product data with HTML elements
        selectors (dict): Dictionary containing CSS selectors for product elements
        
    Returns:
        dict: Validation results with True/False for each field and validation details
    """
    try:
        if not sample_data:
            return {
                "valid": False,
                "message": "No sample data available to validate",
                "field_validations": {}
            }

        field_validations = {}
        overall_valid = True

        # Validate each field individually
        fields_to_validate = {
            'title': {
                'name': 'Product Title',
                'guidelines': 'Should be descriptive product name, 3-100 chars'
            },
            'url': {
                'name': 'Product URL',
                'guidelines': 'Should be valid product page URL'
            },
            'image': {
                'name': 'Product Image',
                'guidelines': 'Should be valid image file URL'
            },
            'price': {
                'name': 'Product Price',
                'guidelines': 'Should have currency symbol or decimal number'
            }
        }

        for field, field_info in fields_to_validate.items():
            # Get element info for the field from sample data
            field_elements = [item['elements'].get(field, {}) for item in sample_data]
            
            # Prepare message for OpenAI with detailed element information
            system_prompt = f"""
            You are a web scraper validator. Your task is to check if the {field_info['name']} is correctly identified.
            You will receive:
            1. The CSS selector used
            2. The HTML element found
            3. The value extracted
            
            Guidelines for {field_info['name']}: {field_info['guidelines']}
            
            Respond with a JSON object:
            {{
                "valid": true/false,
                "reason": "Brief explanation of why the element is valid or invalid"
            }}
            """
        
            user_message = f"""
            Field: {field_info['name']}
            
            Sample Elements:
            {json.dumps([{
                'selector': elem.get('selector'),
                'html': elem.get('html'),
                'extracted_value': elem.get('value')
            } for elem in field_elements if elem], indent=2)}

            Is this field correctly identified? Consider both the selector and the extracted content.
            """

            try:
                response = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=50  # Very small token limit since we only need true/false
                )

                result = json.loads(response.choices[0].message.content)
                field_validations[field] = result["valid"]
                
                if not result["valid"]:
                    overall_valid = False
                    
            except Exception as api_error:
                logger.error(f"OpenAI API error validating {field}: {str(api_error)}")
                field_validations[field] = False
                overall_valid = False

        return {
            "valid": overall_valid,
            "field_validations": field_validations
        }
        
    except Exception as e:
        logger.error(f"Error validating selectors: {str(e)}")
        return {
            "valid": False,
            "message": f"Error validating selectors: {str(e)}",
            "field_validations": {},
            "suggestions": {}
        }

def perform_basic_validation(sample_data, selectors):
    """
    Perform a basic validation of the extracted sample data using pattern matching.
    This is a fallback when the OpenAI API is not available.
    
    Args:
        sample_data (list): List of sample product data
        selectors (dict): Dictionary containing CSS selectors for product elements
        
    Returns:
        dict: Validation results for each field
    """
    if not sample_data:
        return {
            "valid": False,
            "message": "No sample data available to validate",
            "field_validations": {},
            "suggestions": {}
        }
    
    # Initialize results
    field_validations = {}
    overall_valid = True
    suggestions = {}
    
    # Validate container
    container_selector = selectors.get('product_container', '')
    if container_selector:
        container_valid = len(sample_data) > 0
        field_validations["container"] = {
            "valid": container_valid,
            "message": "Container selector found multiple products" if container_valid else "Container selector did not find products"
        }
        if not container_valid:
            overall_valid = False
            suggestions["container"] = "Try a more general selector that captures product items"
    else:
        field_validations["container"] = {
            "valid": False,
            "message": "No container selector provided"
        }
        overall_valid = False
        suggestions["container"] = "You need to provide a container selector"
    
    # Validate title
    title_selector = selectors.get('product_title', '')
    title_valid_count = 0
    for item in sample_data:
        title = item.get('title', '')
        if title and title != "Not found" and title != "No selector" and len(title) > 5 and len(title) < 200:
            title_valid_count += 1
    
    title_valid = title_valid_count > 0 and title_valid_count >= len(sample_data) * 0.5
    field_validations["title"] = {
        "valid": title_valid,
        "message": f"Title selector found valid titles in {title_valid_count}/{len(sample_data)} products" if title_selector else "No title selector provided"
    }
    if not title_valid:
        overall_valid = False
        suggestions["title"] = "Try a more specific selector targeting the product title text"
    
    # Validate URL
    url_selector = selectors.get('product_url', '')
    url_valid_count = 0
    for item in sample_data:
        url = item.get('url', '')
        if url and url != "Not found" and url != "No selector" and ('http' in url or url.startswith('/')):
            url_valid_count += 1
    
    url_valid = url_valid_count > 0 and url_valid_count >= len(sample_data) * 0.5
    field_validations["url"] = {
        "valid": url_valid,
        "message": f"URL selector found valid URLs in {url_valid_count}/{len(sample_data)} products" if url_selector else "No URL selector provided"
    }
    if not url_valid:
        overall_valid = False
        suggestions["url"] = "Look for 'a' elements with href attributes in the product container"
    
    # Validate image
    image_selector = selectors.get('product_image', '')
    image_valid_count = 0
    for item in sample_data:
        img = item.get('image_url', '')
        if img and img != "Not found" and img != "No selector" and ('http' in img or img.startswith('/') or '.' in img):
            image_valid_count += 1
    
    image_valid = image_valid_count > 0 and image_valid_count >= len(sample_data) * 0.5
    field_validations["image"] = {
        "valid": image_valid,
        "message": f"Image selector found valid images in {image_valid_count}/{len(sample_data)} products" if image_selector else "No image selector provided"
    }
    if not image_valid:
        overall_valid = False
        suggestions["image"] = "Look for 'img' elements with src attributes in the product container"
    
    # Validate price
    price_selector = selectors.get('product_price', '')
    price_valid_count = 0
    for item in sample_data:
        price = item.get('price', '')
        if price and price != "Not found" and price != "No selector":
            # Check for currency symbols or numbers with decimals
            if any(c in price for c in '$€£¥₹₽') or (any(c.isdigit() for c in price) and ('.' in price or ',' in price)):
                price_valid_count += 1
    
    price_valid = price_valid_count > 0 and price_valid_count >= len(sample_data) * 0.5
    field_validations["price"] = {
        "valid": price_valid,
        "message": f"Price selector found valid prices in {price_valid_count}/{len(sample_data)} products" if price_selector else "No price selector provided"
    }
    if not price_valid:
        overall_valid = False
        suggestions["price"] = "Look for elements containing currency symbols or numeric values with decimals"
    
    return {
        "valid": overall_valid,
        "message": "All selectors validated successfully" if overall_valid else "Some selectors need improvement",
        "field_validations": field_validations,
        "suggestions": suggestions
    }

def improve_selectors(html_content, current_selectors, validation_results, base_url):
    """
    Attempt to improve selectors one at a time based on validation results.
    
    Args:
        html_content (str): The HTML content of the webpage
        current_selectors (dict): Current CSS selectors
        validation_results (dict): Validation results with True/False for each field
        base_url (str): Base URL of the webpage
        
    Returns:
        dict: Improved selectors
    """
    try:
        # If all validations passed, no need to improve
        if validation_results.get("valid", False):
            return current_selectors

        improved_selectors = current_selectors.copy()
        field_validations = validation_results.get("field_validations", {})

        # Improve each invalid field one at a time
        for field, is_valid in field_validations.items():
            if not is_valid:
                selector_key = f"product_{field}"
                if selector_key not in current_selectors:
                    continue

                system_prompt = f"""
                You are an expert web scraper selector generator. Improve the CSS selector for the {field} field.
                Current selector: {current_selectors[selector_key]}
                
                Guidelines for {field}:
                - Title: Look for h1-h6 tags or elements with class containing 'title', 'name', 'product'
                - URL: Look for 'a' tags linking to product pages
                - Image: Look for 'img' tags or elements with class containing 'image', 'photo'
                - Price: Look for elements with class containing 'price', 'cost', or currency symbols
                
                Respond with a JSON object: {{"selector": "improved-css-selector"}}
                """
        
                # Limit HTML content to avoid token limit issues
                html_sample = html_content[:10000]  # Reduced sample size for focused analysis
                
                user_message = f"""
                HTML Sample (truncated):
                ```html
                {html_sample}
                ```
                
                Suggest an improved CSS selector for the {field} field that will correctly identify the element.
                Current selector is not working: {current_selectors[selector_key]}
                """
                
                try:
                    response = openai.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_message}
                        ],
                        response_format={"type": "json_object"},
                        max_tokens=100  # Reduced token limit since we only need one selector
                    )
                    
                    result = json.loads(response.choices[0].message.content)
                    if result.get("selector"):
                        improved_selectors[selector_key] = result["selector"]
                        logger.debug(f"Improved {field} selector: {result['selector']}")
                        
                except Exception as api_error:
                    logger.error(f"OpenAI API error improving {field} selector: {str(api_error)}")
                    
        return improved_selectors
        
    except Exception as e:
        logger.error(f"Error improving selectors: {str(e)}")
        return current_selectors  # Return original selectors on error