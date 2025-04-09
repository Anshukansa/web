/**
 * JavaScript for the iPhone Flippers admin panel
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Copy to clipboard functionality
    const copyButtons = document.querySelectorAll('.copy-btn');
    copyButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const textToCopy = this.getAttribute('data-copy');
            const tempInput = document.createElement('input');
            document.body.appendChild(tempInput);
            tempInput.value = textToCopy;
            tempInput.select();
            document.execCommand('copy');
            document.body.removeChild(tempInput);
            
            // Change button text temporarily
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="fas fa-check"></i> Copied!';
            this.classList.add('btn-success');
            this.classList.remove('btn-outline-primary');
            
            setTimeout(() => {
                this.innerHTML = originalText;
                this.classList.remove('btn-success');
                this.classList.add('btn-outline-primary');
            }, 2000);
        });
    });
    
    // Date range picker initialization for filtering
    const dateRangePicker = document.getElementById('dateRangePicker');
    if (dateRangePicker) {
        const today = new Date();
        const thirtyDaysAgo = new Date(today);
        thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
        
        // This is just placeholder code - a real date range picker would require a library
        // But we're showing how you might implement it
        dateRangePicker.addEventListener('change', function() {
            document.getElementById('filterForm').submit();
        });
    }
    
    // Handle bulk actions
    const bulkActionSelect = document.getElementById('bulkAction');
    const bulkActionBtn = document.getElementById('applyBulkAction');
    
    if (bulkActionBtn) {
        bulkActionBtn.addEventListener('click', function() {
            const selectedAction = bulkActionSelect.value;
            if (!selectedAction) return;
            
            const checkedRows = document.querySelectorAll('input[name="selected_rows"]:checked');
            if (checkedRows.length === 0) {
                alert('Please select at least one row');
                return;
            }
            
            if (selectedAction === 'delete') {
                if (confirm(`Are you sure you want to delete ${checkedRows.length} selected responses?`)) {
                    // Submit the form with the bulk action
                    document.getElementById('bulkActionForm').submit();
                }
            } else {
                // For other actions, just submit the form
                document.getElementById('bulkActionForm').submit();
            }
        });
    }
    
    // Select all checkboxes
    const selectAll = document.getElementById('selectAll');
    if (selectAll) {
        selectAll.addEventListener('change', function() {
            const checkboxes = document.querySelectorAll('input[name="selected_rows"]');
            checkboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
            });
        });
    }
    
    // Dashboard charts (placeholder - would use a chart library in production)
    const renderCharts = () => {
        // This is just a placeholder - in a real application, you would use a charting library
        // like Chart.js, Highcharts, or D3.js to create actual charts
        console.log('Charts would be rendered here');
    };
    
    // Call the function to render charts if we're on the dashboard
    if (document.getElementById('dashboardPage')) {
        renderCharts();
    }
    
    // Animate count numbers on dashboard
    const animateValue = (element, start, end, duration) => {
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            const value = Math.floor(progress * (end - start) + start);
            element.textContent = value;
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };
        window.requestAnimationFrame(step);
    };
    
    // Get all elements with the 'counter' class
    const counters = document.querySelectorAll('.counter');
    counters.forEach(counter => {
        const endValue = parseInt(counter.getAttribute('data-count'));
        animateValue(counter, 0, endValue, 1000);
    });
});