/**
 * JavaScript for the iPhone Flippers form
 */

document.addEventListener('DOMContentLoaded', function() {
    // Get all form elements
    const form = document.getElementById('preferencesForm');
    const checkboxes = document.querySelectorAll('.form-check-input[type="checkbox"]');
    const priceInputs = document.querySelectorAll('input[type="number"]');
    
    // Apply initial highlighting for preferred models
    checkboxes.forEach(checkbox => {
        if (checkbox.checked) {
            checkbox.closest('tr').classList.add('table-success');
        }
        
        // Add event listener for checkbox changes
        checkbox.addEventListener('change', function() {
            if (this.checked) {
                this.closest('tr').classList.add('table-success');
            } else {
                this.closest('tr').classList.remove('table-success');
            }
        });
    });
    
    // Add custom validation for the form
    if (form) {
        form.addEventListener('submit', function(event) {
            let isValid = true;
            
            // Check if location is filled
            const locationInput = document.querySelector('input[name="location"]');
            if (!locationInput.value.trim()) {
                isValid = false;
                locationInput.classList.add('is-invalid');
                
                // Create error message if it doesn't exist
                if (!locationInput.nextElementSibling || !locationInput.nextElementSibling.classList.contains('invalid-feedback')) {
                    const errorDiv = document.createElement('div');
                    errorDiv.classList.add('invalid-feedback', 'd-block');
                    errorDiv.textContent = 'Please enter your location.';
                    locationInput.parentNode.appendChild(errorDiv);
                }
            } else {
                locationInput.classList.remove('is-invalid');
                
                // Remove error message if it exists
                if (locationInput.nextElementSibling && locationInput.nextElementSibling.classList.contains('invalid-feedback')) {
                    locationInput.nextElementSibling.remove();
                }
            }
            
            // Check if at least one notification mode is selected
            const modeInputs = document.querySelectorAll('input[name="notification_mode"]');
            let modeSelected = false;
            
            modeInputs.forEach(input => {
                if (input.checked) {
                    modeSelected = true;
                }
            });
            
            if (!modeSelected) {
                isValid = false;
                
                // Find the notification mode container
                const modeContainer = document.querySelector('.form-group');
                
                // Create error message if it doesn't exist
                if (!modeContainer.querySelector('.invalid-feedback')) {
                    const errorDiv = document.createElement('div');
                    errorDiv.classList.add('invalid-feedback', 'd-block');
                    errorDiv.textContent = 'Please select a notification mode.';
                    modeContainer.appendChild(errorDiv);
                }
            } else {
                // Find the notification mode container
                const modeContainer = document.querySelector('.form-group');
                
                // Remove error message if it exists
                const errorDiv = modeContainer.querySelector('.invalid-feedback');
                if (errorDiv) {
                    errorDiv.remove();
                }
            }
            
            // Validate price inputs
            priceInputs.forEach(input => {
                const value = input.value.trim();
                
                if (value === '' || isNaN(parseInt(value)) || parseInt(value) < 0) {
                    isValid = false;
                    input.classList.add('is-invalid');
                    
                    // Create error message if it doesn't exist
                    if (!input.nextElementSibling || !input.nextElementSibling.classList.contains('invalid-feedback')) {
                        const errorDiv = document.createElement('div');
                        errorDiv.classList.add('invalid-feedback', 'd-block');
                        errorDiv.textContent = 'Please enter a valid price.';
                        input.parentNode.appendChild(errorDiv);
                    }
                } else {
                    input.classList.remove('is-invalid');
                    
                    // Remove error message if it exists
                    if (input.nextElementSibling && input.nextElementSibling.classList.contains('invalid-feedback')) {
                        input.nextElementSibling.remove();
                    }
                }
            });
            
            if (!isValid) {
                event.preventDefault();
                
                // Scroll to the first error
                const firstError = document.querySelector('.is-invalid');
                if (firstError) {
                    firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
        });
    }
    
    // Add bulk selection controls
    const bulkSelectAll = document.getElementById('selectAllProducts');
    const bulkDeselectAll = document.getElementById('deselectAllProducts');
    
    if (bulkSelectAll) {
        bulkSelectAll.addEventListener('click', function(e) {
            e.preventDefault();
            checkboxes.forEach(checkbox => {
                checkbox.checked = true;
                checkbox.closest('tr').classList.add('table-success');
            });
        });
    }
    
    if (bulkDeselectAll) {
        bulkDeselectAll.addEventListener('click', function(e) {
            e.preventDefault();
            checkboxes.forEach(checkbox => {
                checkbox.checked = false;
                checkbox.closest('tr').classList.remove('table-success');
            });
        });
    }
});