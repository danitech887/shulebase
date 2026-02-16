/**
 * Custom JS for Jazzmin Admin
 * 
 * This file is loaded after the default Jazzmin scripts.
 * Add your custom logic here.
 */

document.addEventListener("DOMContentLoaded", function() {
    // console.log("Jazzmin custom extensions loaded.");
});



// =====================================================
// Django Admin Custom JavaScript
// =====================================================

(function() {
    'use strict';

    // Wait for DOM to be ready
    document.addEventListener('DOMContentLoaded', function() {
        initializeAdminEnhancements();
    });

    /**
     * Main initialization function
     */
    function initializeAdminEnhancements() {
        enhanceTableInteractions();
        addConfirmationDialogs();
        enhanceFormValidation();
        addKeyboardShortcuts();
        enhanceSearchFilters();
        addLoadingStates();
        improveAccessibility();
        addAnimations();
        enhanceMessages();
        addTableSorting();
    }

    /**
     * Enhance table row interactions with highlighting
     */
    function enhanceTableInteractions() {
        const tables = document.querySelectorAll('table');
        
        tables.forEach(table => {
            const rows = table.querySelectorAll('tbody tr');
            
            rows.forEach(row => {
                // Add click-to-highlight functionality
                row.addEventListener('click', function(e) {
                    // Don't highlight if clicking on a link or checkbox
                    if (e.target.tagName === 'A' || e.target.tagName === 'INPUT') {
                        return;
                    }
                    
                    // Remove previous highlights
                    rows.forEach(r => r.classList.remove('row-highlighted'));
                    
                    // Add highlight to clicked row
                    this.classList.add('row-highlighted');
                });
            });
        });

        // Add CSS for highlighted rows
        addDynamicStyle(`
            tbody tr.row-highlighted {
                background-color: #dbeafe !important;
                box-shadow: inset 3px 0 0 #2563eb;
            }
        `);
    }

    /**
     * Add confirmation dialogs for dangerous actions
     */
    function addConfirmationDialogs() {
        // Enhance delete confirmations
        const deleteLinks = document.querySelectorAll('.deletelink, .deletelink-box a');
        
        deleteLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                const itemName = this.closest('tr')?.querySelector('th')?.textContent || 'this item';
                
                if (!confirm(`Are you sure you want to delete ${itemName}?\n\nThis action cannot be undone.`)) {
                    e.preventDefault();
                    return false;
                }
            });
        });

        // Enhance action confirmations
        const actionSelect = document.querySelector('select[name="action"]');
        if (actionSelect) {
            const actionForm = actionSelect.closest('form');
            if (actionForm) {
                actionForm.addEventListener('submit', function(e) {
                    const selectedAction = actionSelect.value;
                    const actionText = actionSelect.options[actionSelect.selectedIndex]?.text;
                    
                    if (selectedAction.includes('delete') || selectedAction.includes('remove')) {
                        const checkedItems = document.querySelectorAll('input[name="_selected_action"]:checked');
                        
                        if (checkedItems.length === 0) {
                            alert('Please select at least one item.');
                            e.preventDefault();
                            return false;
                        }
                        
                        if (!confirm(`Are you sure you want to ${actionText} ${checkedItems.length} item(s)?\n\nThis action cannot be undone.`)) {
                            e.preventDefault();
                            return false;
                        }
                    }
                });
            }
        }
    }

    /**
     * Enhance form validation with better UX
     */
    function enhanceFormValidation() {
        const forms = document.querySelectorAll('form');
        
        forms.forEach(form => {
            const requiredFields = form.querySelectorAll('input[required], textarea[required], select[required]');
            
            requiredFields.forEach(field => {
                // Add visual indicator for required fields
                const label = field.closest('.form-row')?.querySelector('label');
                if (label && !label.querySelector('.required-indicator')) {
                    const indicator = document.createElement('span');
                    indicator.className = 'required-indicator';
                    indicator.textContent = ' *';
                    indicator.style.color = '#ef4444';
                    label.appendChild(indicator);
                }

                // Real-time validation
                field.addEventListener('blur', function() {
                    validateField(this);
                });

                field.addEventListener('input', function() {
                    if (this.classList.contains('error')) {
                        validateField(this);
                    }
                });
            });

            // Form submission validation
            form.addEventListener('submit', function(e) {
                let isValid = true;
                
                requiredFields.forEach(field => {
                    if (!validateField(field)) {
                        isValid = false;
                    }
                });

                if (!isValid) {
                    e.preventDefault();
                    
                    // Scroll to first error
                    const firstError = form.querySelector('.error');
                    if (firstError) {
                        firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                    
                    showNotification('Please fix the errors in the form.', 'error');
                    return false;
                }
            });
        });
    }

    /**
     * Validate a single form field
     */
    function validateField(field) {
        const formRow = field.closest('.form-row');
        const existingError = formRow?.querySelector('.field-error');
        
        // Remove existing error
        if (existingError) {
            existingError.remove();
        }
        field.classList.remove('error');

        // Check if field is valid
        if (field.required && !field.value.trim()) {
            field.classList.add('error');
            showFieldError(field, 'This field is required.');
            return false;
        }

        // Email validation
        if (field.type === 'email' && field.value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(field.value)) {
                field.classList.add('error');
                showFieldError(field, 'Please enter a valid email address.');
                return false;
            }
        }

        // URL validation
        if (field.type === 'url' && field.value) {
            try {
                new URL(field.value);
            } catch {
                field.classList.add('error');
                showFieldError(field, 'Please enter a valid URL.');
                return false;
            }
        }

        return true;
    }

    /**
     * Show field error message
     */
    function showFieldError(field, message) {
        const formRow = field.closest('.form-row');
        if (formRow) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'field-error';
            errorDiv.textContent = message;
            errorDiv.style.color = '#ef4444';
            errorDiv.style.fontSize = '0.75rem';
            errorDiv.style.marginTop = '0.25rem';
            field.parentNode.appendChild(errorDiv);
        }
    }

    /**
     * Add keyboard shortcuts for common actions
     */
    function addKeyboardShortcuts() {
        document.addEventListener('keydown', function(e) {
            // Ctrl/Cmd + S to save
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                const saveButton = document.querySelector('input[name="_save"], input[type="submit"]');
                if (saveButton) {
                    saveButton.click();
                }
            }

            // Ctrl/Cmd + K to focus search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                const searchInput = document.querySelector('#searchbar, input[name="q"]');
                if (searchInput) {
                    searchInput.focus();
                }
            }

            // Escape to cancel/go back
            if (e.key === 'Escape') {
                const cancelButton = document.querySelector('.cancel-link, a[href*="cancel"]');
                if (cancelButton) {
                    window.location.href = cancelButton.href;
                }
            }
        });

        // Add keyboard shortcut hints
        addDynamicStyle(`
            .keyboard-hint {
                font-size: 0.75rem;
                color: #64748b;
                margin-left: 0.5rem;
            }
        `);
    }

    /**
     * Enhance search and filter functionality
     */
    function enhanceSearchFilters() {
        // Add search highlighting
        const searchInput = document.querySelector('#searchbar, input[name="q"]');
        if (searchInput && searchInput.value) {
            highlightSearchTerms(searchInput.value);
        }

        // Add filter collapse/expand
        const filterHeaders = document.querySelectorAll('#changelist-filter h3');
        filterHeaders.forEach(header => {
            header.style.cursor = 'pointer';
            header.style.userSelect = 'none';
            
            header.addEventListener('click', function() {
                const filterList = this.nextElementSibling;
                if (filterList && filterList.tagName === 'UL') {
                    filterList.style.display = filterList.style.display === 'none' ? 'block' : 'none';
                    this.style.opacity = filterList.style.display === 'none' ? '0.6' : '1';
                }
            });
        });
    }

    /**
     * Highlight search terms in results
     */
    function highlightSearchTerms(searchTerm) {
        if (!searchTerm) return;

        const resultsTable = document.querySelector('#result_list tbody');
        if (!resultsTable) return;

        const cells = resultsTable.querySelectorAll('td, th');
        const terms = searchTerm.toLowerCase().split(' ');

        cells.forEach(cell => {
            let html = cell.innerHTML;
            
            terms.forEach(term => {
                if (term.length > 2) {
                    const regex = new RegExp(`(${term})`, 'gi');
                    html = html.replace(regex, '<mark style="background: #fef08a; padding: 2px 4px; border-radius: 2px;">$1</mark>');
                }
            });
            
            cell.innerHTML = html;
        });
    }

    /**
     * Add loading states to forms and buttons
     */
    function addLoadingStates() {
        const forms = document.querySelectorAll('form');
        
        forms.forEach(form => {
            form.addEventListener('submit', function() {
                const submitButtons = this.querySelectorAll('input[type="submit"], button[type="submit"]');
                
                submitButtons.forEach(button => {
                    const originalText = button.value || button.textContent;
                    button.disabled = true;
                    button.style.opacity = '0.6';
                    button.style.cursor = 'wait';
                    
                    if (button.tagName === 'INPUT') {
                        button.value = 'Processing...';
                    } else {
                        button.textContent = 'Processing...';
                    }
                    
                    // Add spinner
                    const spinner = document.createElement('span');
                    spinner.className = 'loading-spinner';
                    spinner.innerHTML = ' ⟳';
                    button.appendChild(spinner);
                });
            });
        });

        // Add spinner animation
        addDynamicStyle(`
            @keyframes spin {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }
            .loading-spinner {
                display: inline-block;
                animation: spin 1s linear infinite;
            }
        `);
    }

    /**
     * Improve accessibility
     */
    function improveAccessibility() {
        // Add ARIA labels to action checkboxes
        const checkboxes = document.querySelectorAll('input[name="_selected_action"]');
        checkboxes.forEach((checkbox, index) => {
            const row = checkbox.closest('tr');
            const itemName = row?.querySelector('th')?.textContent || `item ${index + 1}`;
            checkbox.setAttribute('aria-label', `Select ${itemName}`);
        });

        // Add focus indicators
        addDynamicStyle(`
            *:focus {
                outline: 2px solid #2563eb;
                outline-offset: 2px;
            }
            
            input:focus, 
            textarea:focus, 
            select:focus {
                outline: none;
                border-color: #2563eb;
                box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
            }
        `);
    }

    /**
     * Add smooth animations
     */
    function addAnimations() {
        // Animate new rows added dynamically
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1 && node.tagName === 'TR') {
                        node.style.animation = 'slideIn 0.3s ease';
                    }
                });
            });
        });

        const tables = document.querySelectorAll('tbody');
        tables.forEach(table => {
            observer.observe(table, { childList: true });
        });

        addDynamicStyle(`
            @keyframes slideIn {
                from {
                    opacity: 0;
                    transform: translateX(-20px);
                }
                to {
                    opacity: 1;
                    transform: translateX(0);
                }
            }
        `);
    }

    /**
     * Enhance message display with auto-dismiss
     */
    function enhanceMessages() {
        const messages = document.querySelectorAll('.messagelist li');
        
        messages.forEach((message, index) => {
            // Add close button
            const closeBtn = document.createElement('span');
            closeBtn.innerHTML = '×';
            closeBtn.style.cssText = 'float: right; cursor: pointer; font-size: 1.25rem; font-weight: bold; margin-left: 1rem;';
            closeBtn.addEventListener('click', function() {
                message.style.animation = 'slideOut 0.3s ease';
                setTimeout(() => message.remove(), 300);
            });
            message.insertBefore(closeBtn, message.firstChild);

            // Auto-dismiss after 5 seconds
            setTimeout(() => {
                if (message.parentNode) {
                    message.style.animation = 'slideOut 0.3s ease';
                    setTimeout(() => message.remove(), 300);
                }
            }, 5000 + (index * 500));
        });

        addDynamicStyle(`
            @keyframes slideOut {
                to {
                    opacity: 0;
                    transform: translateX(100%);
                }
            }
        `);
    }

    /**
     * Add table sorting enhancement
     */
    function addTableSorting() {
        const headers = document.querySelectorAll('thead th');
        
        headers.forEach(header => {
            if (header.querySelector('a')) {
                header.style.cursor = 'pointer';
                
                // Add sort indicator
                const link = header.querySelector('a');
                if (link) {
                    const indicator = document.createElement('span');
                    indicator.className = 'sort-indicator';
                    indicator.textContent = ' ⇅';
                    indicator.style.opacity = '0.4';
                    link.appendChild(indicator);
                    
                    header.addEventListener('mouseenter', function() {
                        indicator.style.opacity = '1';
                    });
                    
                    header.addEventListener('mouseleave', function() {
                        indicator.style.opacity = '0.4';
                    });
                }
            }
        });
    }

    /**
     * Show notification toast
     */
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            box-shadow: 0 10px 15px rgba(0, 0, 0, 0.1);
            z-index: 9999;
            animation: slideInRight 0.3s ease;
            max-width: 300px;
        `;

        const colors = {
            success: { bg: '#d1fae5', text: '#065f46', border: '#10b981' },
            error: { bg: '#fee2e2', text: '#991b1b', border: '#ef4444' },
            warning: { bg: '#fef3c7', text: '#92400e', border: '#f59e0b' },
            info: { bg: '#dbeafe', text: '#1e40af', border: '#2563eb' }
        };

        const color = colors[type] || colors.info;
        notification.style.background = color.bg;
        notification.style.color = color.text;
        notification.style.borderLeft = `4px solid ${color.border}`;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    /**
     * Add dynamic CSS styles
     */
    function addDynamicStyle(css) {
        const style = document.createElement('style');
        style.textContent = css;
        document.head.appendChild(style);
    }

    // Add animation keyframes for notifications
    addDynamicStyle(`
        @keyframes slideInRight {
            from {
                opacity: 0;
                transform: translateX(100%);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        
        @keyframes slideOutRight {
            to {
                opacity: 0;
                transform: translateX(100%);
            }
        }
    `);

})();