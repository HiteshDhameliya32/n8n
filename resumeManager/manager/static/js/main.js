// Main JavaScript file for common functionality

// Utility Functions
const utils = {
    // Show alert message
    showAlert: function(message, type = 'info') {
        const messagesContainer = document.querySelector('.messages') || document.body;
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.textContent = message;
        messagesContainer.appendChild(alert);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            alert.remove();
        }, 5000);
    },

    // Format date
    formatDate: function(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    },

    // Format percentage
    formatPercentage: function(value) {
        return `${Math.round(value)}%`;
    },

    // Debounce function
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Get CSRF token
    getCsrfToken: function() {
        // Try to get from hidden input field
        const tokenInput = document.querySelector('[name=csrfmiddlewaretoken]');
        if (tokenInput) {
            return tokenInput.value;
        }
        // Try to get from cookies
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue || '';
    },

    // Make AJAX request
    ajax: function(url, options = {}) {
        const defaultOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            },
            credentials: 'same-origin'
        };

        const config = { ...defaultOptions, ...options };
        
        if (config.body && typeof config.body === 'object' && !(config.body instanceof FormData)) {
            config.body = JSON.stringify(config.body);
        }

        return fetch(url, config)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .catch(error => {
                console.error('AJAX error:', error);
                throw error;
            });
    }
};

// Modal functionality
const modal = {
    open: function(modalId) {
        const modalElement = document.getElementById(modalId);
        if (modalElement) {
            modalElement.classList.add('active');
            document.body.style.overflow = 'hidden';
        }
    },

    close: function(modalId) {
        const modalElement = document.getElementById(modalId);
        if (modalElement) {
            modalElement.classList.remove('active');
            document.body.style.overflow = '';
        }
    },

    init: function() {
        // Close modal on outside click
        document.addEventListener('click', function(e) {
            if (e.target.classList.contains('modal')) {
                e.target.classList.remove('active');
                document.body.style.overflow = '';
            }
        });

        // Close modal on ESC key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                document.querySelectorAll('.modal.active').forEach(modal => {
                    modal.classList.remove('active');
                    document.body.style.overflow = '';
                });
            }
        });
    }
};

// Initialize modal functionality on page load
document.addEventListener('DOMContentLoaded', function() {
    modal.init();
    setActiveNavigation();
});

// Set active navigation based on current URL
function setActiveNavigation() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        link.classList.remove('active');
        const linkPath = link.getAttribute('href');
        
        // Remove trailing slash for comparison
        const normalizedCurrent = currentPath.replace(/\/$/, '') || '/';
        const normalizedLink = linkPath.replace(/\/$/, '') || '/';
        
        // Check if current path matches link path
        if (normalizedCurrent === normalizedLink) {
            link.classList.add('active');
        }
        // Special case: home page (dashboard)
        else if (normalizedCurrent === '/' && normalizedLink === '/') {
            link.classList.add('active');
        }
    });
}

// Export utilities
window.utils = utils;
window.modal = modal;

