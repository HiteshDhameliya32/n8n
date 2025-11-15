// Job Description Management JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const addJobDescBtn = document.getElementById('add-job-desc-btn');
    const addFirstJobDescBtn = document.getElementById('add-first-job-desc');
    const closeModalBtn = document.getElementById('close-modal');
    const cancelFormBtn = document.getElementById('cancel-form-btn');
    const jobDescForm = document.getElementById('job-desc-form');
    const closeDeleteModalBtn = document.getElementById('close-delete-modal');
    const cancelDeleteBtn = document.getElementById('cancel-delete-btn');
    const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
    const fileInput = document.getElementById('job-file');
    const fileUploadArea = document.getElementById('job-file-upload-area');
    const fileSelected = document.getElementById('job-file-selected');
    const fileName = document.getElementById('job-file-name');
    const removeFileBtn = document.getElementById('remove-job-file');

    let deleteJobDescId = null;

    // Initialize
    loadJobDescriptions();
    setupEventListeners();

    function setupEventListeners() {
        // Add job description
        if (addJobDescBtn) {
            addJobDescBtn.addEventListener('click', () => openJobDescModal());
        }

        if (addFirstJobDescBtn) {
            addFirstJobDescBtn.addEventListener('click', () => openJobDescModal());
        }

        // Close modal
        if (closeModalBtn) {
            closeModalBtn.addEventListener('click', () => closeJobDescModal());
        }

        if (cancelFormBtn) {
            cancelFormBtn.addEventListener('click', () => closeJobDescModal());
        }

        // Form submission
        if (jobDescForm) {
            jobDescForm.addEventListener('submit', handleFormSubmit);
        }

        // Delete modal
        if (closeDeleteModalBtn) {
            closeDeleteModalBtn.addEventListener('click', () => closeDeleteModal());
        }

        if (cancelDeleteBtn) {
            cancelDeleteBtn.addEventListener('click', () => closeDeleteModal());
        }

        if (confirmDeleteBtn) {
            confirmDeleteBtn.addEventListener('click', handleConfirmDelete);
        }

        // File upload handling
        if (fileInput) {
            fileInput.addEventListener('change', handleFileSelect);
        }

        if (fileUploadArea) {
            fileUploadArea.addEventListener('dragover', handleDragOver);
            fileUploadArea.addEventListener('dragleave', handleDragLeave);
            fileUploadArea.addEventListener('drop', handleDrop);
        }

        if (removeFileBtn) {
            removeFileBtn.addEventListener('click', removeFile);
        }
    }

    function handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            validateAndDisplayFile(file);
        }
    }

    function handleDragOver(e) {
        e.preventDefault();
        fileUploadArea.style.borderColor = 'var(--primary-color)';
        fileUploadArea.style.backgroundColor = 'rgba(102, 126, 234, 0.1)';
    }

    function handleDragLeave(e) {
        e.preventDefault();
        fileUploadArea.style.borderColor = 'var(--border-color)';
        fileUploadArea.style.backgroundColor = 'var(--bg-secondary)';
    }

    function handleDrop(e) {
        e.preventDefault();
        fileUploadArea.style.borderColor = 'var(--border-color)';
        fileUploadArea.style.backgroundColor = 'var(--bg-secondary)';

        const file = e.dataTransfer.files[0];
        if (file) {
            fileInput.files = e.dataTransfer.files;
            validateAndDisplayFile(file);
        }
    }

    function validateAndDisplayFile(file) {
        // Validate file type
        const allowedTypes = ['application/pdf', 'text/plain', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
        const allowedExtensions = ['.pdf', '.txt', '.doc', '.docx'];
        const fileExt = '.' + file.name.split('.').pop().toLowerCase();
        
        if (!allowedExtensions.includes(fileExt)) {
            utils.showAlert('Please upload a PDF, TXT, DOC, or DOCX file', 'error');
            fileInput.value = '';
            return;
        }

        // Validate file size (10MB)
        const maxSize = 10 * 1024 * 1024; // 10MB in bytes
        if (file.size > maxSize) {
            utils.showAlert('File size should be less than 10MB', 'error');
            fileInput.value = '';
            return;
        }

        // Display selected file
        fileName.textContent = file.name;
        fileUploadArea.querySelector('.file-upload-content').style.display = 'none';
        fileSelected.style.display = 'flex';
    }

    function removeFile() {
        fileInput.value = '';
        fileSelected.style.display = 'none';
        fileUploadArea.querySelector('.file-upload-content').style.display = 'block';
    }

    function loadJobDescriptions() {
        fetch('/api/job-descriptions/')
            .then(response => response.json())
            .then(data => {
                updateTable(data.job_descriptions);
            })
            .catch(error => {
                console.error('Error loading job descriptions:', error);
                utils.showAlert('Failed to load job descriptions', 'error');
            });
    }

    function updateTable(jobDescriptions) {
        const tbody = document.getElementById('job-desc-tbody');
        if (!tbody) return;

        tbody.innerHTML = '';

        if (!jobDescriptions || jobDescriptions.length === 0) {
            tbody.innerHTML = `
                <tr class="empty-row">
                    <td colspan="4" class="text-center">No job descriptions saved yet. <button class="btn-link" id="add-first-job-desc">Add your first job description</button></td>
                </tr>
            `;
            // Re-attach event listener
            const addFirstBtn = document.getElementById('add-first-job-desc');
            if (addFirstBtn) {
                addFirstBtn.addEventListener('click', () => openJobDescModal());
            }
            return;
        }

        jobDescriptions.forEach(jd => {
            const row = createTableRow(jd);
            tbody.appendChild(row);
        });
    }

    function createTableRow(jd) {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${jd.title}</td>
            <td>${jd.file_name}</td>
            <td>${utils.formatDate(jd.upload_date)}</td>
            <td>
                <div class="action-buttons">
                    <button class="btn btn-sm btn-danger" onclick="deleteJobDescription(${jd.id})">Delete</button>
                </div>
            </td>
        `;
        return row;
    }

    function openJobDescModal() {
        const modalTitle = document.getElementById('modal-title');
        modalTitle.textContent = 'Add Job Description';
        jobDescForm.reset();
        clearFormErrors();
        removeFile(); // Reset file input
        modal.open('job-desc-modal');
    }

    function closeJobDescModal() {
        modal.close('job-desc-modal');
        jobDescForm.reset();
        clearFormErrors();
        removeFile(); // Reset file input
    }

    function handleFormSubmit(e) {
        e.preventDefault();

        if (!validateForm()) {
            return;
        }

        const formData = new FormData(jobDescForm);

        // Upload to backend
        fetch('/api/upload-job-description/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': utils.getCsrfToken()
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                utils.showAlert(data.message || 'Job description uploaded successfully', 'success');
                closeJobDescModal();
                loadJobDescriptions();
            } else {
                utils.showAlert(data.error || 'Failed to upload job description', 'error');
            }
        })
        .catch(error => {
            console.error('Upload error:', error);
            utils.showAlert('Failed to upload job description. Please try again.', 'error');
        });
    }

    function validateForm() {
        let isValid = true;

        const jobTitle = document.getElementById('job-title').value.trim();
        const jobFile = fileInput.files[0];

        // Validate job title
        if (!jobTitle) {
            showFieldError('job-title', 'Title is required');
            isValid = false;
        } else {
            clearFieldError('job-title');
        }

        // Validate file
        if (!jobFile) {
            showFieldError('job-file', 'Please upload a file');
            isValid = false;
        } else {
            clearFieldError('job-file');
        }

        return isValid;
    }

    function showFieldError(fieldId, message) {
        const errorElement = document.getElementById(`${fieldId}-error`);
        if (errorElement) {
            errorElement.textContent = message;
        }
    }

    function clearFieldError(fieldId) {
        const errorElement = document.getElementById(`${fieldId}-error`);
        if (errorElement) {
            errorElement.textContent = '';
        }
    }

    function clearFormErrors() {
        document.querySelectorAll('.form-error').forEach(error => {
            error.textContent = '';
        });
    }

    function openDeleteModal(jobDescId) {
        deleteJobDescId = jobDescId;
        modal.open('delete-modal');
    }

    function closeDeleteModal() {
        deleteJobDescId = null;
        modal.close('delete-modal');
    }

    function handleConfirmDelete() {
        if (!deleteJobDescId) {
            return;
        }

        fetch(`/api/job-descriptions/${deleteJobDescId}/delete/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': utils.getCsrfToken(),
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                utils.showAlert(data.message || 'Job description deleted successfully', 'success');
                closeDeleteModal();
                loadJobDescriptions();
            } else {
                utils.showAlert(data.error || 'Failed to delete job description', 'error');
            }
        })
        .catch(error => {
            console.error('Delete error:', error);
            utils.showAlert('Failed to delete job description. Please try again.', 'error');
        });
    }

    // Global functions for table actions
    window.deleteJobDescription = function(jobDescId) {
        openDeleteModal(jobDescId);
    };
});
