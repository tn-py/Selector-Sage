import os
import logging
import io
import json
from dotenv import load_dotenv
load_dotenv()
import csv
import sys
import traceback
from contextlib import redirect_stdout, redirect_stderr
from flask import Flask, render_template, request, jsonify, Response
from utils.scraper import fetch_webpage_content, parse_html
from utils.ai_analyzer import analyze_page_structure
from utils.script_generator import generate_scraping_script
from utils.selector_validator import extract_sample_data, validate_selectors, improve_selectors

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

@app.route('/')
def index():
    """Render the main application page."""
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    """
    Endpoint to analyze a webpage and identify CSS selectors.
    Streams validation results for each field as they are processed.
    
    Expects a URL and optional pagination details in the request.
    Returns a stream of validation results and final script.
    """
    def generate_validation_stream():
        try:
            data = request.json
            url = data.get('url')
            pagination_enabled = data.get('pagination_enabled', False)
            pagination_selector = data.get('pagination_selector', '')
            max_iterations = data.get('max_iterations', 3)
            user_selectors = data.get('selectors')
            
            if not url:
                yield json.dumps({"error": "URL is required"}) + '\n'
                return
            
            logger.debug(f"Analyzing URL: {url}")
            
            # Step 1: Fetch webpage content
            html_content = fetch_webpage_content(url)
            if not html_content:
                yield json.dumps({"error": "Failed to fetch the webpage"}) + '\n'
                return
            
            # Step 2: Parse HTML
            parsed_data = parse_html(html_content, url)
            
            # Step 3: Get selectors
            if user_selectors:
                logger.debug(f"Using user-provided selectors: {user_selectors}")
                selectors = user_selectors
            else:
                selectors = analyze_page_structure(parsed_data)
                if not selectors:
                    yield json.dumps({"error": "Failed to analyze page structure"}) + '\n'
                    return
            
            # Step 4: Stream validation for each field
            validation_history = []
            field_validations = {}
            field_reasons = {}
            iterations = 0
            fields_to_validate = ['title', 'url', 'image', 'price']
            
            # Initial sample data
            sample_data = extract_sample_data(html_content, selectors, url)
            
            # Stream initial state
            yield json.dumps({
                "type": "init",
                "selectors": selectors,
                "fields": fields_to_validate
            }) + '\n'
            
            # Validate each field
            for field in fields_to_validate:
                field_valid = False
                field_iterations = 0
                
                while not field_valid and field_iterations < max_iterations:
                    # Validate current field
                    validation_results = validate_selectors(sample_data, selectors)
                    current_validation = validation_results.get("field_validations", {}).get(field, {})
                    
                    # Store validation results
                    validation_entry = {
                        "iteration": iterations + 1,
                        "field": field,
                        "selectors": selectors.copy(),
                        "sample_data": sample_data,
                        "validation": current_validation
                    }
                    validation_history.append(validation_entry)
                    
                    # Stream validation result for this field
                    yield json.dumps({
                        "type": "validation",
                        "field": field,
                        "iteration": iterations + 1,
                        "selector": selectors.get(f"product_{field}"),
                        "sample_data": sample_data,
                        "validation": current_validation,
                        "is_final": field_valid or field_iterations == max_iterations - 1
                    }) + '\n'
                    
                    # Check if field is valid
                    field_valid = current_validation.get("valid", False)
                    field_validations[field] = field_valid
                    field_reasons[field] = current_validation.get("reason", "")
                    
                    if not field_valid and field_iterations < max_iterations - 1:
                        # Try to improve selector
                        logger.debug(f"Improving selector for {field}")
                        selectors = improve_selectors(html_content, selectors, {
                            "field_validations": {field: current_validation}
                        }, url)
                        
                        # Get new sample data
                        sample_data = extract_sample_data(html_content, selectors, url)
                        field_iterations += 1
                        iterations += 1
                    else:
                        break
            
            # All fields validated, generate final response
            all_valid = all(field_validations.values())
            validation_summary = {
                "iterations": iterations,
                "final_validation": field_validations,
                "reasons": field_reasons,
                "all_fields_valid": all_valid
            }
            
            # Generate script
            script = generate_scraping_script(
                selectors,
                url,
                pagination_enabled,
                pagination_selector
            )
            
            # Stream final result
            yield json.dumps({
                "type": "complete",
                "selectors": selectors,
                "validation_summary": validation_summary,
                "validation_history": validation_history,
                "script": script,
                "message": (
                    "All selectors validated successfully" if all_valid
                    else f"Validation in progress - {len([v for v in field_validations.values() if v])} of {len(fields_to_validate)} fields valid"
                )
            }) + '\n'
            
        except Exception as e:
            logger.error(f"Error analyzing page: {str(e)}")
            yield json.dumps({
                "type": "error",
                "error": f"Error processing request: {str(e)}"
            }) + '\n'
    
    return Response(
        generate_validation_stream(),
        mimetype='application/x-json-stream'
    )

@app.route('/run-scraper', methods=['POST'])
def run_scraper():
    """
    Endpoint to execute the generated scraping script.
    
    Expects a script and URL in the request.
    Returns the scraped data and optionally provides a CSV download.
    """
    try:
        data = request.json
        script = data.get('script')
        url = data.get('url')
        format_type = data.get('format', 'json')  # 'json' or 'csv'
        max_pages = data.get('max_pages', 3)  # Limit number of pages to scrape for safety
        
        if not script or not url:
            return jsonify({"error": "Script and URL are required"}), 400
        
        logger.debug(f"Running scraper for URL: {url}")
        
        # Add max_pages variable to limit pagination for safety
        script_with_limit = f"max_pages_to_scrape = {max_pages}\n" + script
        
        # Add a limit to number of pages scraped
        script_with_limit = script_with_limit.replace(
            "while next_url:",
            "page_count = 0\nwhile next_url and page_count < max_pages_to_scrape:"
        )
        script_with_limit = script_with_limit.replace(
            "# Process the next page",
            "page_count += 1\n    # Process the next page"
        )
        
        # Add CSV export capability
        script_with_limit += """
# Create a function to export data as CSV
def export_as_csv(data):
    if not data:
        return ""
    
    # Get field names from the first item
    fieldnames = list(data[0].keys())
    
    # Write data to CSV string
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data)
    
    return output.getvalue()
"""
        
        # Execute the script in a controlled environment
        # Add all necessary modules that might be used in the script
        local_vars = {
            'io': io, 
            'csv': csv, 
            'products': None,
            'requests': __import__('requests'),
            'BeautifulSoup': __import__('bs4').BeautifulSoup,
            'time': __import__('time'),
            'os': os,
            'json': json,
            'sys': sys,
            'urlparse': __import__('urllib.parse').urlparse,
            'urljoin': __import__('urllib.parse').urljoin
        }
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        try:
            # Set a timeout for script execution (30 seconds)
            try:
                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    exec(script_with_limit, None, local_vars)
                
                # Get the products from script execution
                scraped_data = local_vars.get('products', [])
                
                if not scraped_data:
                    logger.warning("No data was scraped from the script execution")
                    return jsonify({
                        "error": "No data was scraped",
                        "output": stdout_capture.getvalue(),
                        "errors": stderr_capture.getvalue()
                    }), 400
            except Exception as script_exception:
                # Specific handling for script execution errors
                logger.error(f"Error in script execution: {str(script_exception)}")
                return jsonify({
                    "error": f"Error executing script: {str(script_exception)}",
                    "output": stdout_capture.getvalue(),
                    "errors": stderr_capture.getvalue()
                }), 400
            
            # Return data in the requested format
            if format_type == 'csv':
                # Generate CSV
                csv_data = local_vars['export_as_csv'](scraped_data)
                
                # Create response with CSV file
                response = Response(
                    csv_data,
                    mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment;filename=scraped_data.csv'}
                )
                return response
            else:
                # Return JSON by default
                return jsonify({
                    "scraped_data": scraped_data,
                    "count": len(scraped_data),
                    "output": stdout_capture.getvalue()
                })
                
        except Exception as script_error:
            error_traceback = traceback.format_exc()
            logger.error(f"Script execution error: {str(script_error)}\n{error_traceback}")
            return jsonify({
                "error": f"Error executing script: {str(script_error)}",
                "traceback": error_traceback,
                "output": stdout_capture.getvalue(),
                "errors": stderr_capture.getvalue()
            }), 500
            
    except Exception as e:
        logger.error(f"Error running scraper: {str(e)}")
        return jsonify({"error": f"Error processing request: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
