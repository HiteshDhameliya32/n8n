// Dashboard JavaScript

document.addEventListener('DOMContentLoaded', function() {
    let resumes = [];
    let filteredResumes = [];
    let currentPage = 1;
    const itemsPerPage = 10;

    // Initialize dashboard
    initDashboard();

    function initDashboard() {
        loadResumes();
        setupEventListeners();
        loadJobDescriptions();
    }

    function loadResumes() {
        fetch('/api/resumes/')
            .then(response => response.json())
            .then(data => {
                resumes = data.resumes || [];
                filteredResumes = resumes;
                updateDashboard();
            })
            .catch(error => {
                console.error('Error loading resumes:', error);
                utils.showAlert('Failed to load resumes', 'error');
            });
    }

    function loadJobDescriptions() {
        fetch('/api/job-descriptions/')
            .then(response => response.json())
            .then(data => {
                populateJobDescriptionFilter(data.job_descriptions || []);
            })
            .catch(error => {
                console.error('Error loading job descriptions:', error);
            });
    }

    function populateJobDescriptionFilter(jobDescriptions) {
        const filterSelect = document.getElementById('filter-job');
        if (!filterSelect) return;

        // Clear existing options except the first one
        filterSelect.innerHTML = '<option value="">All Job Descriptions</option>';
        
        jobDescriptions.forEach(jd => {
            const option = document.createElement('option');
            option.value = jd.id;
            option.textContent = jd.title;
            filterSelect.appendChild(option);
        });
    }

    function setupEventListeners() {
        const searchInput = document.getElementById('search-input');
        const searchBtn = document.getElementById('search-btn');
        const filterScore = document.getElementById('filter-score');
        const filterJob = document.getElementById('filter-job');
        const clearFilters = document.getElementById('clear-filters');

        if (searchInput) {
            searchInput.addEventListener('input', utils.debounce(handleSearch, 300));
        }

        if (searchBtn) {
            searchBtn.addEventListener('click', handleSearch);
        }

        if (filterScore) {
            filterScore.addEventListener('change', handleFilter);
        }

        if (filterJob) {
            filterJob.addEventListener('change', handleFilter);
        }

        if (clearFilters) {
            clearFilters.addEventListener('click', clearAllFilters);
        }
    }

    function handleSearch() {
        const searchInput = document.getElementById('search-input');
        const searchTerm = searchInput.value.toLowerCase().trim();

        if (!searchTerm) {
            filteredResumes = resumes;
        } else {
            filteredResumes = resumes.filter(resume => {
                return resume.file_name.toLowerCase().includes(searchTerm);
            });
        }

        currentPage = 1;
        applyFilters();
    }

    function handleFilter() {
        applyFilters();
    }

    function applyFilters() {
        let results = [...filteredResumes];

        // Filter by score
        const filterScore = document.getElementById('filter-score');
        if (filterScore && filterScore.value) {
            const [min, max] = filterScore.value.split('-').map(Number);
            results = results.filter(resume => {
                const score = resume.overall_score || 0;
                return score >= min && score <= max;
            });
        }

        filteredResumes = results;
        updateTable();
        updatePagination();
    }

    function clearAllFilters() {
        const searchInput = document.getElementById('search-input');
        const filterScore = document.getElementById('filter-score');
        const filterJob = document.getElementById('filter-job');
        
        if (searchInput) searchInput.value = '';
        if (filterScore) filterScore.value = '';
        if (filterJob) filterJob.value = '';
        
        filteredResumes = resumes;
        currentPage = 1;
        updateTable();
        updatePagination();
    }

    function updateDashboard() {
        updateWidgets();
        updateTable();
        updatePagination();
    }

    function updateWidgets() {
        // Total resumes
        const totalResumes = resumes.length;
        const totalResumesEl = document.getElementById('total-resumes');
        if (totalResumesEl) {
            totalResumesEl.textContent = totalResumes;
        }

        // Average score
        const avgScore = resumes.length > 0
            ? Math.round(resumes.reduce((sum, r) => sum + (r.overall_score || 0), 0) / resumes.length)
            : 0;
        const avgScoreEl = document.getElementById('avg-score');
        if (avgScoreEl) {
            avgScoreEl.textContent = `${avgScore}%`;
        }

        // Top matched skills (placeholder - would need analysis data)
        const topSkillsEl = document.getElementById('top-skills');
        if (topSkillsEl) {
            topSkillsEl.textContent = 'N/A';
        }
    }

    function updateTable() {
        const tbody = document.getElementById('resumes-tbody');
        if (!tbody) return;

        tbody.innerHTML = '';

        if (filteredResumes.length === 0) {
            tbody.innerHTML = `
                <tr class="empty-row">
                    <td colspan="6" class="text-center">No resumes found matching your criteria.</td>
                </tr>
            `;
            return;
        }

        const start = (currentPage - 1) * itemsPerPage;
        const end = start + itemsPerPage;
        const pageResumes = filteredResumes.slice(start, end);

        pageResumes.forEach(resume => {
            const row = createTableRow(resume);
            tbody.appendChild(row);
        });
    }

    function createTableRow(resume) {
        const row = document.createElement('tr');
        
        const score = resume.overall_score || 0;
        const scoreClass = score >= 80 ? 'success' : 
                          score >= 70 ? 'warning' : 'danger';
        
        // Get candidate info
        const candidateName = resume.candidate_name || 'N/A';
        const candidateEmail = resume.candidate_email || 'N/A';
        const jobDescription = resume.candidate_applied_for || 'N/A';
        const uploadDate = resume.created_at || resume.upload_date;
        const status = resume.status || 'pending';
        
        // Show status badge if not completed
        let statusBadge = '';
        if (status === 'pending' || status === 'processing') {
            statusBadge = '<span class="status-badge status-reviewing">Reviewing...</span>';
        } else if (status === 'failed') {
            statusBadge = '<span class="status-badge status-failed">Failed</span>';
        }

        row.innerHTML = `
            <td>${escapeHtml(candidateName)}${statusBadge ? '<br>' + statusBadge : ''}</td>
            <td>${escapeHtml(candidateEmail)}</td>
            <td>${escapeHtml(jobDescription)}</td>
            <td>${utils.formatDate(uploadDate)}</td>
            <td>
                ${status === 'completed' ? `<span class="score-badge score-${scoreClass}">${score}%</span>` : '<span class="score-badge">-</span>'}
            </td>
            <td>
                <div class="action-buttons">
                    ${status === 'completed' ? `<a href="/analysis/${resume.id}/" class="btn btn-sm btn-primary">View</a>` : ''}
                    <button class="btn btn-sm btn-danger" onclick="deleteResume(${resume.id})">Delete</button>
                </div>
            </td>
        `;

        return row;
    }
    
    function escapeHtml(text) {
        if (!text) return 'N/A';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function updatePagination() {
        const pagination = document.getElementById('pagination');
        if (!pagination) return;

        const totalPages = Math.ceil(filteredResumes.length / itemsPerPage);
        
        if (totalPages <= 1) {
            pagination.innerHTML = '';
            return;
        }

        let paginationHTML = '';
        
        // Previous button
        paginationHTML += `
            <button class="pagination-btn" ${currentPage === 1 ? 'disabled' : ''} 
                    onclick="goToPage(${currentPage - 1})">Previous</button>
        `;

        // Page numbers
        for (let i = 1; i <= totalPages; i++) {
            if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
                paginationHTML += `
                    <button class="pagination-btn ${i === currentPage ? 'active' : ''}" 
                            onclick="goToPage(${i})">${i}</button>
                `;
            } else if (i === currentPage - 3 || i === currentPage + 3) {
                paginationHTML += `<span class="pagination-ellipsis">...</span>`;
            }
        }

        // Next button
        paginationHTML += `
            <button class="pagination-btn" ${currentPage === totalPages ? 'disabled' : ''} 
                    onclick="goToPage(${currentPage + 1})">Next</button>
        `;

        pagination.innerHTML = paginationHTML;
    }

    // Global functions for table actions
    window.goToPage = function(page) {
        currentPage = page;
        updateTable();
        updatePagination();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    window.deleteResume = function(resumeId) {
        if (!confirm('Are you sure you want to delete this resume? This action cannot be undone.')) {
            return;
        }

        fetch(`/api/resumes/${resumeId}/delete/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': utils.getCsrfToken(),
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            // Check if response is JSON
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return response.json().then(data => {
                    if (data.success) {
                        utils.showAlert('Resume deleted successfully', 'success');
                        loadResumes();
                    } else {
                        utils.showAlert(data.error || 'Failed to delete resume', 'error');
                    }
                });
            } else {
                // Handle non-JSON response (HTML error page)
                return response.text().then(text => {
                    console.error('Delete error: Server returned non-JSON response', text.substring(0, 200));
                    utils.showAlert('Failed to delete resume. Server error occurred.', 'error');
                });
            }
        })
        .catch(error => {
            console.error('Delete error:', error);
            utils.showAlert('Failed to delete resume. Please try again.', 'error');
        });
    };
});

// Add CSS for score badges
const style = document.createElement('style');
style.textContent = `
    .score-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.875rem;
    }
    .score-success {
        background-color: #d1fae5;
        color: #065f46;
    }
    .score-warning {
        background-color: #fef3c7;
        color: #92400e;
    }
    .score-danger {
        background-color: #fee2e2;
        color: #991b1b;
    }
    .action-buttons {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
    }
    .btn-sm {
        padding: 0.5rem 1rem;
        font-size: 0.875rem;
    }
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.75rem;
        font-weight: 600;
        margin-top: 0.25rem;
    }
    .status-reviewing {
        background-color: #dbeafe;
        color: #1e40af;
    }
    .status-failed {
        background-color: #fee2e2;
        color: #991b1b;
    }
`;
document.head.appendChild(style);
