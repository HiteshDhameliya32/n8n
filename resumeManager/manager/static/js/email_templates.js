// Email Templates JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('email-template-form');
    
    // Load active template on page load
    loadActiveTemplate();
    
    // Load templates list
    loadTemplatesList();
    
    if (form) {
        form.addEventListener('submit', handleSaveTemplate);
    }
  
    function loadActiveTemplate() {
        fetch('/api/email-templates/get/')
            .then(response => response.json())
            .then(data => {
                document.getElementById('template-subject').value = data.subject || 'Interview Invitation';
                document.getElementById('template-body').value = data.body || '';
            })
            .catch(error => {
                console.error('Error loading template:', error);
            });
    }
    
    function loadTemplatesList() {
        // This would load from backend if we had a list endpoint
        // For now, we'll just show a message
        const templatesList = document.getElementById('templates-list');
        if (templatesList) {
            templatesList.innerHTML = '<p class="empty-state">Templates will be listed here</p>';
        }
    }
    
    function handleSaveTemplate(e) {
        e.preventDefault();
        
        const subject = document.getElementById('template-subject').value;
        const body = document.getElementById('template-body').value;
        const isActive = document.getElementById('template-active').checked;
        
        if (!subject || !body) {
            utils.showAlert('Subject and body are required', 'error');
            return;
        }
        
        fetch('/api/email-templates/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': utils.getCsrfToken()
            },
            body: JSON.stringify({
                subject: subject,
                body: body,
                is_active: isActive
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                utils.showAlert('Template saved successfully!', 'success');
                loadTemplatesList();
            } else {
                utils.showAlert(data.error || 'Failed to save template', 'error');
            }
        })
        .catch(error => {
            console.error('Error saving template:', error);
            utils.showAlert('Failed to save template. Please try again.', 'error');
        });
    }
});

