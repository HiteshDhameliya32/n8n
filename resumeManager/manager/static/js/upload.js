// Upload Resume JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('resume-file');
    const fileUploadArea = document.getElementById('file-upload-area');
    const fileSelected = document.getElementById('file-selected');
    const fileName = document.getElementById('file-name');
    const removeFileBtn = document.getElementById('remove-file');
    const progressSection = document.getElementById('progress-section');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const progressStatus = document.getElementById('progress-status');
    const submitBtn = document.getElementById('submit-btn');

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

    // Form submission
    if (uploadForm) {
        uploadForm.addEventListener('submit', handleFormSubmit);
    }

    function handleFileSelect(e) {
        const files = Array.from(e.target.files || []);
        if (files.length > 0) {
            validateAndDisplayFiles(files);
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

        const files = Array.from(e.dataTransfer.files || []);
        if (files.length > 0) {
            // Assign dropped files to input
            const dt = new DataTransfer();
            files.forEach(f => dt.items.add(f));
            fileInput.files = dt.files;
            validateAndDisplayFiles(files);
        }
    }

    function validateAndDisplayFiles(files) {
        const maxSize = 10 * 1024 * 1024; // 10MB
        const invalid = files.find(file => file.type !== 'application/pdf' || file.size > maxSize);
        if (invalid) {
            if (invalid.type !== 'application/pdf') {
                utils.showAlert('Please upload PDF files only', 'error');
            } else {
                utils.showAlert('Each file must be smaller than 10MB', 'error');
            }
            fileInput.value = '';
            return;
        }
        // Display selected files
        if (files.length === 1) {
            fileName.textContent = files[0].name;
        } else {
            fileName.textContent = `${files.length} files selected`;
        }
        fileUploadArea.querySelector('.file-upload-content').style.display = 'none';
        fileSelected.style.display = 'flex';
    }

    function removeFile() {
        fileInput.value = '';
        fileSelected.style.display = 'none';
        fileUploadArea.querySelector('.file-upload-content').style.display = 'block';
    }

    function handleFormSubmit(e) {
        e.preventDefault();

        // Validate form
        if (!validateForm()) {
            return;
        }

        // Show progress
        showProgress();
        submitBtn.disabled = true;

        const files = Array.from(fileInput.files || []);
        if (files.length === 0) {
            handleUploadError('Please select at least one PDF');
            return;
        }

        // Prepare form data (multiple)
        const formData = new FormData();
        files.forEach(f => formData.append('resume_file', f));

        // Upload to backend
        fetch('/api/upload-resume/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': utils.getCsrfToken()
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            // Handle both single and batch responses
            if (data.results) {
                const successCount = data.results.filter(r => r.success).length;
                if (successCount > 0) {
                    handleUploadSuccess({ message: `Uploaded ${successCount}/${data.results.length} resumes successfully` });
                } else {
                    handleUploadError(data.results[0]?.error || 'Upload failed');
                }
            } else if (data.success) {
                handleUploadSuccess(data);
            } else {
                handleUploadError(data.error || 'Upload failed');
            }
        })
        .catch(error => {
            console.error('Upload error:', error);
            handleUploadError('Failed to upload resume. Please try again.');
        });
    }

    function validateForm() {
        let isValid = true;

        // Validate resume file
        const resumeFile = fileInput.files[0];
        if (!resumeFile) {
            showFieldError('resume-file', 'Please upload a resume file');
            isValid = false;
        } else {
            clearFieldError('resume-file');
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

    function showProgress() {
        progressSection.style.display = 'block';
        updateProgress(0, 'Uploading resume...');
    }

    function updateProgress(percent, status) {
        progressFill.style.width = `${percent}%`;
        progressText.textContent = `${percent}%`;
        progressStatus.textContent = status;
    }

    function handleUploadSuccess(data) {
        updateProgress(100, 'Upload complete!');
        utils.showAlert(data.message || 'Resume uploaded successfully!', 'success');
        
        // Reset UI for next uploads
        uploadForm.reset();
        removeFile();
        hideProgress();
        submitBtn.disabled = false;

        // Redirect to dashboard after delay
        setTimeout(() => {
            window.location.href = '/';
        }, 1200);
    }

    function handleUploadError(errorMessage) {
        hideProgress();
        utils.showAlert(errorMessage, 'error');
        submitBtn.disabled = false;
    }

    function hideProgress() {
        progressSection.style.display = 'none';
        progressFill.style.width = '0%';
        progressText.textContent = '0%';
        progressStatus.textContent = '';
    }
});
