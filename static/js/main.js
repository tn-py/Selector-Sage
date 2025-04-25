document.addEventListener('DOMContentLoaded', function() {
    // Current scraped data
    let scrapedData = [];
    // DOM Elements
    const scraperForm = document.getElementById('scraper-form');
    const urlInput = document.getElementById('url-input');
    const paginationToggle = document.getElementById('pagination-toggle');
    const paginationSection = document.getElementById('pagination-section');
    const paginationSelector = document.getElementById('pagination-selector');
    const analyzeBtn = document.getElementById('analyze-btn');
    
    const loadingSection = document.getElementById('loading-section');
    const loadingStatus = document.getElementById('loading-status');
    
    const resultsSection = document.getElementById('results-section');
    const validationBadge = document.getElementById('validation-badge');
    const productContainerSelector = document.getElementById('product-container-selector');
    const productTitleSelector = document.getElementById('product-title-selector');
    const productUrlSelector = document.getElementById('product-url-selector');
    const productImageSelector = document.getElementById('product-image-selector');
    const productPriceSelector = document.getElementById('product-price-selector');
    const paginationNextSelector = document.getElementById('pagination-next-selector');
    const containerValidation = document.getElementById('container-validation');
    const titleValidation = document.getElementById('title-validation');
    const urlValidation = document.getElementById('url-validation');
    const imageValidation = document.getElementById('image-validation');
    const priceValidation = document.getElementById('price-validation');
    const paginationValidation = document.getElementById('pagination-validation');
    const editSelectorsBtn = document.getElementById('edit-selectors-btn');
    
    const validationSection = document.getElementById('validation-section');
    const validationStatus = document.getElementById('validation-status');
    const validationIterations = document.getElementById('validation-iterations');
    const validationMessage = document.getElementById('validation-message');
    const toggleValidationDetailsBtn = document.getElementById('toggle-validation-details-btn');
    const validationDetails = document.getElementById('validation-details');
    const sampleDataTable = document.getElementById('sample-data-table');
    const fieldValidations = document.getElementById('field-validations');
    const improvementSuggestions = document.getElementById('improvement-suggestions');
    
    const scriptSection = document.getElementById('script-section');
    const scriptCode = document.getElementById('script-code');
    const runScriptBtn = document.getElementById('run-script-btn');
    const regenerateScriptBtn = document.getElementById('regenerate-script-btn');
    const downloadScriptBtn = document.getElementById('download-script-btn');
    const exportCsvBtn = document.getElementById('export-csv-btn');
    
    const scrapedDataSection = document.getElementById('scraped-data-section');
    const scrapedCount = document.getElementById('scraped-count');
    const scraperResultsLoading = document.getElementById('scraper-results-loading');
    const scraperResultsError = document.getElementById('scraper-results-error');
    const scraperErrorMessage = document.getElementById('scraper-error-message');
    const scraperErrorDetails = document.getElementById('scraper-error-details');
    const scraperResultsContent = document.getElementById('scraper-results-content');
    const scrapedDataTable = document.getElementById('scraped-data-table');
    
    const instructionsSection = document.getElementById('instructions-section');
    
    // Edit Selectors Modal Elements
    const editSelectorsModal = new bootstrap.Modal(document.getElementById('edit-selectors-modal'));
    const editProductContainer = document.getElementById('edit-product-container');
    const editProductTitle = document.getElementById('edit-product-title');
    const editProductUrl = document.getElementById('edit-product-url');
    const editProductImage = document.getElementById('edit-product-image');
    const editProductPrice = document.getElementById('edit-product-price');
    const editPaginationNext = document.getElementById('edit-pagination-next');
    const saveSelectorsBtn = document.getElementById('save-selectors-btn');
    
    // Current state
    let currentSelectors = {
        product_container: '',
        product_title: '',
        product_url: '',
        product_image: '',
        product_price: '',
        pagination_next: ''
    };
    let currentUrl = '';
    
    // Show/hide pagination section based on toggle
    paginationToggle.addEventListener('change', function() {
        if (this.checked) {
            paginationSection.classList.remove('d-none');
        } else {
            paginationSection.classList.add('d-none');
        }
    });
    
    // Form submission
    scraperForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Get URL and pagination settings
        const url = urlInput.value.trim();
        const paginationEnabled = paginationToggle.checked;
        const paginationSelectorValue = paginationSelector.value.trim();
        
        if (!url) {
            alert('Please enter a valid URL');
            return;
        }
        
        // Log current selectors for debugging
        console.log('Current Selectors before submission:', currentSelectors);
        
        // Check if currentSelectors is populated
        if (Object.keys(currentSelectors).length === 0) {
            alert('Please fill in the selectors before analyzing.');
            return;
        }
        
        currentUrl = url;
        
        // Show loading state
        scraperForm.classList.add('d-none');
        loadingSection.classList.remove('d-none');
        resultsSection.classList.add('d-none');
        scriptSection.classList.add('d-none');
        instructionsSection.classList.add('d-none');
        
        // Send request to server
        analyzeWebpage(url, paginationEnabled, paginationSelectorValue);
    });
    
    // Function to analyze webpage
    function analyzeWebpage(url, paginationEnabled, paginationSelectorValue) {
        loadingStatus.textContent = 'Fetching webpage content...';
        
        fetch('/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                url: url,
                pagination_enabled: paginationEnabled,
                pagination_selector: paginationSelectorValue,
                max_iterations: 3,  // Allow up to 3 iterations for selector refinement
                selectors: currentSelectors  // Include current selectors in the request
            }),
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || 'Error analyzing webpage');
                });
            }
            return response.json();
        })
        .then(data => {
            console.log('Analysis response:', data);
            
            if (!data.selectors) {
                throw new Error('Selectors data is missing from the response.');
            }
            
            // Save current selectors
            currentSelectors = data.selectors;
            
            // Update UI with selectors
            updateSelectorsDisplay(data.selectors);
            
            // Update validation UI
            updateValidationDisplay(data);
            
            // Update script code
            scriptCode.textContent = data.script;
            Prism.highlightElement(scriptCode);
            
            // Set up validation details toggle
            toggleValidationDetailsBtn.addEventListener('click', function() {
                if (validationDetails.classList.contains('d-none')) {
                    validationDetails.classList.remove('d-none');
                    this.innerHTML = '<i class="fas fa-chevron-up me-1"></i> Hide Details';
                } else {
                    validationDetails.classList.add('d-none');
                    this.innerHTML = '<i class="fas fa-chevron-down me-1"></i> Show Details';
                }
            });
            
            // Show results
            loadingSection.classList.add('d-none');
            scraperForm.classList.remove('d-none');
            resultsSection.classList.remove('d-none');
            validationSection.classList.remove('d-none');
            scriptSection.classList.remove('d-none');
            instructionsSection.classList.remove('d-none');
        })
        .catch(error => {
            console.error('Error:', error);
            loadingSection.classList.add('d-none');
            scraperForm.classList.remove('d-none');
            alert('Error: ' + error.message);
        });
    }
    
    // Function to update the validation display
    function updateValidationDisplay(data) {
        const validationSummary = data.validation_summary;
        const allFieldsValid = validationSummary.all_fields_valid;
        const iterations = validationSummary.iterations;
        const finalValidation = validationSummary.final_validation;
        
        // Create status table if it doesn't exist
        if (!document.getElementById('validation-status-table')) {
            const statusTable = document.createElement('table');
            statusTable.id = 'validation-status-table';
            statusTable.className = 'table table-bordered mt-3';
            statusTable.innerHTML = `
                <thead>
                    <tr>
                        <th>Field</th>
                        <th>Selector</th>
                        <th>Sample Value</th>
                        <th>Status</th>
                        <th>Reason</th>
                    </tr>
                </thead>
                <tbody></tbody>
            `;
            validationSection.insertBefore(statusTable, validationDetails);
        }
        
        const statusTableBody = document.querySelector('#validation-status-table tbody');
        statusTableBody.innerHTML = '';
        
        // Update live status for each field
        const lastValidation = data.validation_history[data.validation_history.length - 1];
        if (lastValidation && lastValidation.sample_data && lastValidation.sample_data[0]) {
            const sampleData = lastValidation.sample_data[0];
            const elements = sampleData.elements;
            
            for (const [field, element] of Object.entries(elements)) {
                if (!element) continue;
                
                const row = document.createElement('tr');
                const isValid = finalValidation[field];
                
                row.innerHTML = `
                    <td>${capitalizeField(field)}</td>
                    <td><code>${escapeHtml(element.selector)}</code></td>
                    <td><code>${escapeHtml(element.value || 'Not found')}</code></td>
                    <td>
                        <span class="badge text-bg-${isValid ? 'success' : 'warning'}">
                            ${isValid ? 'Valid' : 'Validating...'}
                        </span>
                    </td>
                    <td>${finalValidation.reasons?.[field] || ''}</td>
                `;
                
                statusTableBody.appendChild(row);
            }
        }
        
        // Update overall status
        validationBadge.className = `badge text-bg-${allFieldsValid ? 'success' : 'warning'} me-2`;
        validationBadge.textContent = `Validation: ${allFieldsValid ? 'Complete' : 'In Progress'}`;
        
        validationStatus.textContent = allFieldsValid ? 'All Fields Valid' : 'Validating Fields';
        validationStatus.className = allFieldsValid ? 'text-success' : 'text-warning';
        
        validationIterations.textContent = iterations;
        validationMessage.textContent = data.message ||
            (allFieldsValid ? 'All selectors validated successfully.' :
             `Validating fields - ${iterations} iterations so far`);
        
        // Update sample data table with detailed element information
        sampleDataTable.querySelector('tbody').innerHTML = '';
        
        if (lastValidation && lastValidation.sample_data) {
            lastValidation.sample_data.forEach((product, index) => {
                const row = document.createElement('tr');
                
                // For each field, show both the extracted value and the HTML element
                const fields = ['title', 'url', 'image_url', 'price'];
                const cells = fields.map(field => {
                    const element = product.elements[field];
                    if (!element) return '<td>No selector</td>';
                    
                    const isValid = finalValidation[field];
                    return `
                        <td>
                            <div class="mb-2">
                                <strong>Value:</strong> ${escapeHtml(element.value || 'Not found')}
                                <span class="badge text-bg-${isValid ? 'success' : 'warning'} ms-2">
                                    ${isValid ? 'Valid' : 'Validating...'}
                                </span>
                            </div>
                            <div class="small">
                                <strong>Selector:</strong> <code>${escapeHtml(element.selector)}</code>
                            </div>
                            <div class="small">
                                <strong>HTML:</strong> <code>${escapeHtml(element.html || 'Not found')}</code>
                            </div>
                        </td>
                    `;
                });
                
                row.innerHTML = `
                    <td>${index + 1}</td>
                    ${cells.join('')}
                `;
                
                sampleDataTable.querySelector('tbody').appendChild(row);
            });
        }
        
        // Clear and update field validations
        fieldValidations.innerHTML = '';
        
        // Add field validation details
        if (finalValidation) {
            for (const [field, isValid] of Object.entries(finalValidation)) {
                const fieldElement = document.createElement('div');
                fieldElement.className = 'mb-3';
                
                const fieldStatus = isValid ?
                    '<span class="badge text-bg-success me-2">Valid</span>' :
                    '<span class="badge text-bg-warning me-2">Invalid</span>';
                
                fieldElement.innerHTML = `
                    <h6>${fieldStatus} ${capitalizeField(field)}</h6>
                    <p>${isValid ?
                        'Field correctly identified and validated.' :
                        'Field needs improvement - current value does not match expected pattern.'}</p>
                `;
                
                fieldValidations.appendChild(fieldElement);
            }
        }
    }
    
    // Helper function to update field validation badges
    function updateFieldValidationBadge(element, validation) {
        if (!validation) {
            element.className = 'badge rounded-pill text-bg-secondary';
            element.textContent = 'N/A';
            return;
        }
        
        if (validation.valid) {
            element.className = 'badge rounded-pill text-bg-success';
            element.textContent = 'Valid';
        } else {
            element.className = 'badge rounded-pill text-bg-warning';
            element.textContent = 'Issue';
        }
    }
    
    // Helper function to capitalize field names
    function capitalizeField(field) {
        const fieldNames = {
            'container': 'Product Container',
            'title': 'Product Title',
            'url': 'Product URL',
            'image': 'Product Image',
            'price': 'Product Price'
        };
        
        return fieldNames[field] || field.charAt(0).toUpperCase() + field.slice(1);
    }
    
    // Helper function to escape HTML
    function escapeHtml(text) {
        if (!text) return 'N/A';
        
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // Function to update selectors display
    function updateSelectorsDisplay(selectors) {
        productContainerSelector.textContent = selectors.product_container || 'Not identified';
        productTitleSelector.textContent = selectors.product_title || 'Not identified';
        productUrlSelector.textContent = selectors.product_url || 'Not identified';
        productImageSelector.textContent = selectors.product_image || 'Not identified';
        productPriceSelector.textContent = selectors.product_price || 'Not identified';
        paginationNextSelector.textContent = selectors.pagination_next || 'Not identified';
    }
    
    // Edit selectors button
    editSelectorsBtn.addEventListener('click', function() {
        // Fill the form with current selectors
        editProductContainer.value = currentSelectors.product_container || '';
        editProductTitle.value = currentSelectors.product_title || '';
        editProductUrl.value = currentSelectors.product_url || '';
        editProductImage.value = currentSelectors.product_image || '';
        editProductPrice.value = currentSelectors.product_price || '';
        editPaginationNext.value = currentSelectors.pagination_next || '';
        
        // Show the modal
        editSelectorsModal.show();
    });
    
    // Save selectors button
    saveSelectorsBtn.addEventListener('click', function() {
        console.log('Save button clicked');
        // Log form values for debugging
        console.log('Form Values:', {
            product_container: editProductContainer.value.trim(),
            product_title: editProductTitle.value.trim(),
            product_url: editProductUrl.value.trim(),
            product_image: editProductImage.value.trim(),
            product_price: editProductPrice.value.trim(),
            pagination_next: editPaginationNext.value.trim()
        });

        // Update current selectors
        currentSelectors = {
            product_container: editProductContainer.value.trim(),
            product_title: editProductTitle.value.trim(),
            product_url: editProductUrl.value.trim(),
            product_image: editProductImage.value.trim(),
            product_price: editProductPrice.value.trim(),
            pagination_next: editPaginationNext.value.trim()
        };
        
        // Log current selectors for debugging
        console.log('Current Selectors after saving:', currentSelectors);
        alert('Selectors saved: ' + JSON.stringify(currentSelectors));
        
        // Update UI
        updateSelectorsDisplay(currentSelectors);
        
        // Regenerate script
        regenerateScript();
        
        // Hide modal
        editSelectorsModal.hide();
    });
    
    // Regenerate script button
    regenerateScriptBtn.addEventListener('click', regenerateScript);
    
    // Function to regenerate script
    function regenerateScript() {
        // Show loading
        scriptSection.classList.add('d-none');
        validationSection.classList.add('d-none');
        loadingSection.classList.remove('d-none');
        loadingStatus.textContent = 'Regenerating script and validating selectors...';
        
        fetch('/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                url: currentUrl,
                pagination_enabled: paginationToggle.checked,
                pagination_selector: paginationSelector.value.trim(),
                selectors: currentSelectors,  // Pass the current selectors
                max_iterations: 3  // Allow up to 3 iterations for selector refinement
            }),
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || 'Error regenerating script');
                });
            }
            return response.json();
        })
        .then(data => {
            console.log('Regenerate response:', data);
            
            // Save current selectors (they might have been improved)
            currentSelectors = data.selectors;
            
            // Update UI with selectors
            updateSelectorsDisplay(data.selectors);
            
            // Update validation UI
            updateValidationDisplay(data);
            
            // Update script code
            scriptCode.textContent = data.script;
            Prism.highlightElement(scriptCode);
            
            // Show results
            loadingSection.classList.add('d-none');
            validationSection.classList.remove('d-none');
            scriptSection.classList.remove('d-none');
        })
        .catch(error => {
            console.error('Error:', error);
            loadingSection.classList.add('d-none');
            scriptSection.classList.remove('d-none');
            alert('Error: ' + error.message);
        });
    }
    
    // Download script button
    downloadScriptBtn.addEventListener('click', function() {
        const script = scriptCode.textContent;
        const blob = new Blob([script], {type: 'text/plain;charset=utf-8'});
        saveAs(blob, 'scraper_script.py');
    });
    
    // Run script button
    runScriptBtn.addEventListener('click', function() {
        runScraper();
    });
    
    // Export CSV button
    exportCsvBtn.addEventListener('click', function() {
        exportScrapedDataAsCSV();
    });
    
    // Function to run the scraper
    function runScraper() {
        // Reset and show scraped data section
        scrapedDataSection.classList.remove('d-none');
        scraperResultsLoading.classList.remove('d-none');
        scraperResultsError.classList.add('d-none');
        scraperResultsContent.classList.add('d-none');
        
        // Scroll to the data section
        scrapedDataSection.scrollIntoView({ behavior: 'smooth' });
        
        // Send request to server
        fetch('/run-scraper', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                script: scriptCode.textContent,
                url: currentUrl,
                format: 'json',
                max_pages: 3  // Limit to 3 pages for safety
            }),
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || 'Error running scraper');
                });
            }
            return response.json();
        })
        .then(data => {
            console.log('Scraper response:', data);
            
            // Save scraped data
            scrapedData = data.scraped_data || [];
            
            // Update scraped count
            scrapedCount.textContent = `${scrapedData.length} items`;
            
            // Clear and update the table
            updateScrapedDataTable(scrapedData);
            
            // Hide loading, show content
            scraperResultsLoading.classList.add('d-none');
            scraperResultsContent.classList.remove('d-none');
        })
        .catch(error => {
            console.error('Error:', error);
            
            // Show error state
            scraperResultsLoading.classList.add('d-none');
            scraperResultsError.classList.remove('d-none');
            
            // Update error message
            scraperErrorMessage.textContent = error.message;
            
            // If there are detailed error logs, show them
            if (error.traceback) {
                scraperErrorDetails.textContent = error.traceback;
            } else if (error.errors) {
                scraperErrorDetails.textContent = error.errors;
            } else {
                scraperErrorDetails.textContent = 'No detailed error information available.';
            }
        });
    }
    
    // Function to update the scraped data table
    function updateScrapedDataTable(data) {
        // Clear the table
        const tbody = scrapedDataTable.querySelector('tbody');
        tbody.innerHTML = '';
        
        // Add data to table
        data.forEach((product, index) => {
            const row = document.createElement('tr');
            
            // Truncate long content for better display
            const title = product.title ? (product.title.length > 100 ? product.title.substring(0, 100) + '...' : product.title) : 'N/A';
            const url = product.url ? (product.url.length > 60 ? product.url.substring(0, 60) + '...' : product.url) : 'N/A';
            const image = product.image_url || 'N/A';
            const price = product.price || 'N/A';
            
            row.innerHTML = `
                <td>${index + 1}</td>
                <td title="${escapeHtml(product.title || '')}">${escapeHtml(title)}</td>
                <td title="${escapeHtml(product.url || '')}">
                    <a href="${escapeHtml(product.url || '#')}" target="_blank" rel="noopener noreferrer">
                        ${escapeHtml(url)}
                    </a>
                </td>
                <td title="${escapeHtml(product.image_url || '')}">
                    ${image !== 'N/A' ? 
                      `<a href="${escapeHtml(image)}" target="_blank" rel="noopener noreferrer">
                         <i class="fas fa-image"></i> View
                       </a>` : 
                      'N/A'}
                </td>
                <td>${escapeHtml(price)}</td>
            `;
            
            tbody.appendChild(row);
        });
        
        // If no data, show a message
        if (data.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td colspan="5" class="text-center">No data scraped. Please check your selectors and try again.</td>
            `;
            tbody.appendChild(row);
        }
    }
    
    // Function to export scraped data as CSV
    function exportScrapedDataAsCSV() {
        if (scrapedData.length === 0) {
            // If no data has been scraped yet, run the scraper first with CSV format
            // Show loading state
            scrapedDataSection.classList.remove('d-none');
            scraperResultsLoading.classList.remove('d-none');
            scraperResultsError.classList.add('d-none');
            scraperResultsContent.classList.add('d-none');
            
            // Direct CSV export via server
            fetch('/run-scraper', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    script: scriptCode.textContent,
                    url: currentUrl,
                    format: 'csv',
                    max_pages: 3  // Limit to 3 pages for safety
                }),
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => {
                        throw new Error(data.error || 'Error exporting CSV');
                    });
                }
                
                // For CSV format, we get a blob directly
                return response.blob();
            })
            .then(blob => {
                // Create a download link
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = 'scraped_data.csv';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                
                // Hide loading, show content
                scraperResultsLoading.classList.add('d-none');
                runScraper(); // Now run the scraper to show the data in the UI
            })
            .catch(error => {
                console.error('Error:', error);
                
                // Show error state
                scraperResultsLoading.classList.add('d-none');
                scraperResultsError.classList.remove('d-none');
                
                // Update error message
                scraperErrorMessage.textContent = error.message;
            });
        } else {
            // If we already have data, we can generate CSV directly in the browser
            // Create CSV content
            let csvContent = "data:text/csv;charset=utf-8,";
            
            // Add headers
            const headers = ["Title", "URL", "Image URL", "Price"];
            csvContent += headers.join(",") + "\r\n";
            
            // Add data rows
            scrapedData.forEach(product => {
                const row = [
                    `"${(product.title || '').replace(/"/g, '""')}"`,
                    `"${(product.url || '').replace(/"/g, '""')}"`,
                    `"${(product.image_url || '').replace(/"/g, '""')}"`,
                    `"${(product.price || '').replace(/"/g, '""')}"`
                ];
                csvContent += row.join(",") + "\r\n";
            });
            
            // Create download link
            const encodedUri = encodeURI(csvContent);
            const link = document.createElement("a");
            link.setAttribute("href", encodedUri);
            link.setAttribute("download", "scraped_data.csv");
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    }
    
    // Reset to form view when URL changes
    urlInput.addEventListener('input', function() {
        if (this.value.trim() !== currentUrl) {
            resultsSection.classList.add('d-none');
            validationSection.classList.add('d-none');
            scriptSection.classList.add('d-none');
            scrapedDataSection.classList.add('d-none');
            instructionsSection.classList.add('d-none');
        }
    });
});
