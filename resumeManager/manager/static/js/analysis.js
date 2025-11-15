// Resume Analysis JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const resumeId = getResumeIdFromURL();
    const exportPdfBtn = document.getElementById('export-pdf-btn');
    const sendEmailBtn = document.getElementById('send-email-btn');
    let pollingInterval = null;

    // Load analysis data
    if (resumeId) {
        loadAnalysisData(resumeId).then(data => {
            // Start polling only if status is pending/processing
            if (data && (data.status === 'pending' || data.status === 'processing')) {
                startPolling(resumeId);
            }
        });
    }

    // Action buttons
    if (exportPdfBtn) {
        exportPdfBtn.addEventListener('click', handleExportPDF);
    }

    if (sendEmailBtn) {
        sendEmailBtn.addEventListener('click', handleSendEmail);
    }
    
    // Cleanup polling on page unload
    window.addEventListener('beforeunload', function() {
        if (pollingInterval) {
            clearInterval(pollingInterval);
        }
    });

    function getResumeIdFromURL() {
        const path = window.location.pathname;
        const match = path.match(/\/analysis\/(\d+)\//);
        return match ? match[1] : null;
    }

    function loadAnalysisData(resumeId, silent = false) {
        if (!resumeId) {
            if (!silent) utils.showAlert('Invalid resume ID', 'error');
            return Promise.reject('Invalid resume ID');
        }

        // Load resume data from backend
        return fetch(`/api/resumes/${resumeId}/`)
            .then(response => response.json())
            .then(data => {
                displayAnalysisData(data);
                
                // Stop polling if status is completed or failed
                if (data.status === 'completed' || data.status === 'failed') {
                    stopPolling();
                }
                
                return data;
            })
            .catch(error => {
                console.error('Error loading analysis:', error);
                if (!silent) utils.showAlert('Failed to load analysis data', 'error');
                throw error;
            });
    }
    
    function startPolling(resumeId) {
        // Poll every 3 seconds if status is pending/processing
        pollingInterval = setInterval(function() {
            loadAnalysisData(resumeId, true); // silent mode
        }, 3000);
    }
    
    function stopPolling() {
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
        }
    }

    function displayAnalysisData(data) {
        const analysisData = data.analysis_data || {};
        const candidateInfo = analysisData.candidate_info || {};
        
        // Show PDF if available
        if (data.file_url) {
            const pdfViewer = document.getElementById('resume-pdf-viewer');
            const pdfLoading = document.getElementById('pdf-loading');
            if (pdfViewer && pdfLoading) {
                // Ensure file_url is absolute
                let pdfUrl = data.file_url;
                if (!pdfUrl.startsWith('http')) {
                    // Make it absolute if it's relative
                    pdfUrl = window.location.origin + pdfUrl;
                }
                
                // Try to load PDF
                pdfViewer.src = pdfUrl;
                pdfViewer.style.display = 'block';
                pdfLoading.style.display = 'none';
                
                // Set onerror for fallback
                pdfViewer.onerror = function() {
                    pdfLoading.textContent = 'Failed to load PDF. You can download it using the Download button.';
                    pdfLoading.style.display = 'block';
                    pdfViewer.style.display = 'none';
                };
            }
        } else {
            const pdfLoading = document.getElementById('pdf-loading');
            const pdfViewer = document.getElementById('resume-pdf-viewer');
            if (pdfLoading) {
                pdfLoading.textContent = 'PDF not available';
            }
            if (pdfViewer) {
                pdfViewer.style.display = 'none';
            }
        }
        
        // Check if status is not completed
        if (data.status && data.status !== 'completed') {
            const analysisGrid = document.querySelector('.analysis-grid');
            if (analysisGrid) {
                analysisGrid.innerHTML = `
                    <div class="analysis-section card" style="grid-column: 1 / -1; text-align: center; padding: 3rem;">
                        <h3>Resume is being reviewed...</h3>
                        <p style="color: #6b7280; margin-top: 1rem;">Please wait while we analyze the resume. This may take a few moments.</p>
                        <div style="margin-top: 2rem;">
                            <button class="btn btn-primary" onclick="location.reload()">Refresh</button>
                        </div>
                    </div>
                `;
            }
            return;
        }
        
        // Candidate details
        const candidateNameEl = document.getElementById('candidate-name');
        if (candidateNameEl) {
            const candidateName = candidateInfo.name || data.file_name || 'Unknown';
            candidateNameEl.textContent = escapeHtml(candidateName);
        }

        const candidateEmailEl = document.getElementById('candidate-email');
        if (candidateEmailEl) {
            const email = candidateInfo.email || 'N/A';
            const phone = candidateInfo.phone_number ? ` • ${candidateInfo.phone_number}` : '';
            const address = candidateInfo.address ? ` • ${candidateInfo.address}` : '';
            const appliedFor = candidateInfo.candidate_applied_for ? ` • Applied for: ${candidateInfo.candidate_applied_for}` : '';
            
            let emailHTML = escapeHtml(email) + escapeHtml(phone) + escapeHtml(address) + escapeHtml(appliedFor);
            
            // Add LinkedIn link if available
            if (candidateInfo.linkedin_url) {
                const linkedinUrl = escapeHtml(candidateInfo.linkedin_url);
                emailHTML += ` • <a href="${linkedinUrl}" target="_blank" rel="noopener noreferrer">LinkedIn</a>`;
            }
            
            candidateEmailEl.innerHTML = emailHTML;
        }

        const scoreValueEl = document.getElementById('score-value');
        if (scoreValueEl) {
            scoreValueEl.textContent = `${data.overall_score || 0}%`;
        }

        // Update score circle color based on score
        const scoreCircle = document.getElementById('score-circle');
        if (scoreCircle) {
            const score = data.overall_score || 0;
            if (score >= 80) {
                scoreCircle.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
            } else if (score >= 70) {
                scoreCircle.style.background = 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)';
            } else {
                scoreCircle.style.background = 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)';
            }
        }

        // Display summary
        displaySummary(analysisData.summary || '');

        // Display skills (sanitized)
        displaySkills(Array.isArray(analysisData.skills) ? analysisData.skills : []);

        // Display experience (sanitized)
        displayExperience(Array.isArray(analysisData.experience) ? analysisData.experience : []);

        // Display education (sanitized)
        displayEducation(Array.isArray(analysisData.education) ? analysisData.education : []);

        // Display languages
        displayLanguages(Array.isArray(analysisData.languages) ? analysisData.languages : []);

        // Display projects
        displayProjects(Array.isArray(analysisData.projects) ? analysisData.projects : []);
        
        // Display total experience
        displayTotalExperience(analysisData.total_experience || '');

        // Display recommendations and decision
        displayRecommendations(analysisData);
    }
    
    function displayTotalExperience(totalExp) {
        const totalExpEl = document.getElementById('total-experience');
        if (totalExpEl && totalExp) {
            totalExpEl.textContent = escapeHtml(totalExp);
        }
    }

    function displaySkills(skills) {
        const skillsContainer = document.getElementById('skills-container');
        if (!skillsContainer) return;

        if (!skills || skills.length === 0) {
            skillsContainer.innerHTML = '<p class="empty-state">No skill data available</p>';
            return;
        }

        skillsContainer.innerHTML = skills.map(skill => {
            const name = escapeHtml(String(skill.name || ''));
            const match = skill.match != null ? Number(skill.match) : null;
            const width = match != null ? Math.max(0, Math.min(100, match)) : 0;
            return `
            <div class="skill-item">
                <div class="skill-header">
                    <span class="skill-name">${name}</span>
                    <span class="skill-match">${match != null ? width : 'N/A'}${match != null ? '%' : ''}</span>
                </div>
                <div class="skill-bar">
                    <div class="skill-bar-fill" style="width: ${width}%"></div>
                </div>
            </div>
        `;
        }).join('');
    }

    function displayExperience(experience) {
        const experienceList = document.getElementById('experience-list');
        if (!experienceList) return;

        if (!experience || experience.length === 0) {
            experienceList.innerHTML = '<p class="empty-state">No experience data available</p>';
            return;
        }

        experienceList.innerHTML = experience.map(exp => {
            const title = escapeHtml(String(exp.title || ''));
            const company = escapeHtml(String(exp.company || ''));
            const duration = escapeHtml(String(exp.duration || ''));
            const description = escapeHtml(String(exp.description || ''));
            return `
            <div class="experience-item">
                <h5>${title}</h5>
                <p><strong>${company}</strong> • ${duration}</p>
                <p>${description}</p>
            </div>
        `;
        }).join('');
    }

    function displayEducation(education) {
        const educationList = document.getElementById('education-list');
        if (!educationList) return;

        if (!education || education.length === 0) {
            educationList.innerHTML = '<p class="empty-state">No education data available</p>';
            return;
        }

        educationList.innerHTML = education.map(edu => {
            const degree = escapeHtml(String(edu.degree || ''));
            const university = escapeHtml(String(edu.university || ''));
            const year = escapeHtml(String(edu.year || ''));
            const description = escapeHtml(String(edu.description || ''));
            return `
            <div class="education-item">
                <h5>${degree}</h5>
                <p><strong>${university}</strong> • ${year}</p>
                ${description ? `<p>${description}</p>` : ''}
            </div>
        `;
        }).join('');
    }

    function displaySummary(summary) {
        const summaryEl = document.getElementById('summary-text');
        if (summaryEl && summary) {
            summaryEl.textContent = escapeHtml(summary);
        }
    }

    function displayLanguages(languages) {
        const languagesEl = document.getElementById('languages-list');
        if (!languagesEl) return;

        if (!languages || languages.length === 0) {
            languagesEl.innerHTML = '<p class="empty-state">No language data available</p>';
            return;
        }

        languagesEl.innerHTML = languages.map(lang => {
            const langName = escapeHtml(String(lang || ''));
            return `<span class="language-tag">${langName}</span>`;
        }).join('');
    }

    function displayProjects(projects) {
        const projectsEl = document.getElementById('projects-list');
        if (!projectsEl) return;

        if (!projects || projects.length === 0) {
            projectsEl.innerHTML = '<p class="empty-state">No project data available</p>';
            return;
        }

        projectsEl.innerHTML = projects.map(proj => {
            const projText = escapeHtml(String(proj || ''));
            return `
            <div class="project-item">
                <p>${projText}</p>
            </div>
        `;
        }).join('');
    }

    function displayRecommendations(analysisData) {
        const recommendationsEl = document.getElementById('recommendations-text');
        if (recommendationsEl && analysisData.recommendations) {
            recommendationsEl.textContent = escapeHtml(analysisData.recommendations);
        }

        const whyHireEl = document.getElementById('why-hire-text');
        if (whyHireEl && analysisData.why_hire) {
            whyHireEl.textContent = escapeHtml(analysisData.why_hire);
        }

        const whyNotHireEl = document.getElementById('why-not-hire-text');
        if (whyNotHireEl && analysisData.why_not_hire) {
            whyNotHireEl.textContent = escapeHtml(analysisData.why_not_hire);
        }

        const explanationEl = document.getElementById('explanation-text');
        if (explanationEl && analysisData.explanation) {
            explanationEl.textContent = escapeHtml(analysisData.explanation);
        }

        const finalDecisionEl = document.getElementById('final-decision');
        if (finalDecisionEl && analysisData.final_decision) {
            const decision = analysisData.final_decision;
            const selected = decision.selected_for_applied_position || '';
            const preferred = decision.preferred_other_position || '';
            const finalScore = decision.final_score || '';
            
            let decisionHTML = '';
            if (selected) {
                decisionHTML += `<p><strong>Selected for Applied Position:</strong> ${escapeHtml(selected)}</p>`;
            }
            if (preferred) {
                decisionHTML += `<p><strong>Preferred Other Positions:</strong> ${escapeHtml(preferred)}</p>`;
            }
            if (finalScore) {
                decisionHTML += `<p><strong>Final Score:</strong> ${escapeHtml(finalScore)}</p>`;
            }
            
            finalDecisionEl.innerHTML = decisionHTML || '<p class="empty-state">No decision data available</p>';
        }

        const needsReviewEl = document.getElementById('needs-review-badge');
        if (needsReviewEl) {
            if (analysisData.needs_human_review) {
                needsReviewEl.style.display = 'inline-block';
                needsReviewEl.textContent = 'Needs Human Review';
            } else {
                needsReviewEl.style.display = 'none';
            }
        }
    }

    function escapeHtml(text) {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }


    function handleExportPDF() {
        const resumeId = getResumeIdFromURL();
        if (!resumeId) {
            utils.showAlert('Invalid resume ID', 'error');
            return;
        }
        
        // Download the resume PDF
        fetch(`/api/resumes/${resumeId}/download/`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to download PDF');
                }
                return response.blob();
            })
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `resume_${resumeId}.pdf`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                utils.showAlert('Resume PDF downloaded successfully', 'success');
            })
            .catch(error => {
                console.error('Error downloading PDF:', error);
                utils.showAlert('Failed to download PDF', 'error');
            });
    }
    
    function handleSendEmail() {
        const resumeId = getResumeIdFromURL();
        if (!resumeId) {
            utils.showAlert('Invalid resume ID', 'error');
            return;
        }
        
        // Open email and calendar modal
        openEmailCalendarModal(resumeId);
    }
    
    function openEmailCalendarModal(resumeId) {
        // Fetch resume data and email template
        Promise.all([
            fetch(`/api/resumes/${resumeId}/`).then(r => r.json()),
            fetch('/api/email-templates/get/').then(r => r.json())
        ])
            .then(([resumeData, templateData]) => {
                const candidateInfo = resumeData.analysis_data?.candidate_info || {};
                const candidateName = candidateInfo.name || 'Candidate';
                const candidateEmail = candidateInfo.email || '';
                const position = candidateInfo.candidate_applied_for || resumeData.analysis_data?.candidate_applied_for || 'Position';
                
                // Create and show modal with template
                showEmailCalendarModal({
                    resumeId: resumeId,
                    candidateName: candidateName,
                    candidateEmail: candidateEmail,
                    position: position,
                    emailSubject: templateData.subject || 'Interview Invitation',
                    emailBody: templateData.body || `Dear ${candidateName},\n\nWe are pleased to invite you for an interview for the position of ${position}.\n\nPlease let us know your availability.\n\nBest regards`
                });
            })
            .catch(error => {
                console.error('Error fetching data:', error);
                utils.showAlert('Failed to load information', 'error');
            });
    }
    
    function showEmailCalendarModal(data) {
        // Create modal HTML
        const modalHTML = `
            <div id="email-calendar-modal" class="modal active">
                <div class="modal-content" style="max-width: 800px;">
                    <div class="modal-header">
                        <h2>Send Email & Schedule Interview</h2>
                        <button class="modal-close" onclick="closeEmailCalendarModal()">&times;</button>
                    </div>
                    <div class="modal-body" style="display: grid; grid-template-columns: 1fr 1fr; gap: 2rem;">
                        <!-- Email Form -->
                        <div>
                            <h3 style="margin-top: 0; margin-bottom: 1rem; font-size: 1rem; color: #374151;">Email Details</h3>
                            <form id="email-calendar-form">
                                <div class="form-group">
                                    <label for="candidate-email-input">Candidate Email:</label>
                                    <input type="email" id="candidate-email-input" value="${escapeHtml(data.candidateEmail)}" required>
                                </div>
                                <div class="form-group">
                                    <label for="email-subject">Email Subject:</label>
                                    <input type="text" id="email-subject" value="${escapeHtml(data.emailSubject || 'Interview Invitation')}" required>
                                </div>
                                <div class="form-group">
                                    <label for="email-body">Email Body:</label>
                                    <textarea id="email-body" rows="6" required>${escapeHtml(data.emailBody || `Dear ${data.candidateName},\n\nWe are pleased to invite you for an interview for the position of ${data.position}.\n\nPlease let us know your availability.\n\nBest regards`)}</textarea>
                                </div>
                                <div class="form-group">
                                    <label>
                                        <input type="checkbox" id="schedule-calendar" checked>
                                        Add to Google Calendar
                                    </label>
                                </div>
                                <div id="calendar-fields" style="display: block;">
                                    <div class="form-group">
                                        <label for="interview-date">Interview Date:</label>
                                        <input type="date" id="interview-date" required>
                                    </div>
                                    <div class="form-group">
                                        <label for="interview-time">Interview Time:</label>
                                        <input type="time" id="interview-time" required>
                                    </div>
                                    <div class="form-group">
                                        <label for="interview-duration">Duration (minutes):</label>
                                        <input type="number" id="interview-duration" value="60" min="15" step="15" required>
                                    </div>
                                    <div class="form-group">
                                        <label for="interview-location">Location/Meeting Link:</label>
                                        <input type="text" id="interview-location" placeholder="Office address or Google Meet link">
                                    </div>
                                </div>
                            </form>
                        </div>
                        
                        <!-- Calendar View -->
                        <div>
                            <h3 style="margin-top: 0; margin-bottom: 1rem; font-size: 1rem; color: #374151;">Your Calendar</h3>
                            <div id="calendar-events" style="background: #f9fafb; padding: 1rem; border-radius: 0.375rem; max-height: 400px; overflow-y: auto;">
                                <p style="text-align: center; color: #9ca3af;">Loading calendar events...</p>
                            </div>
                        </div>
                    </div>
                    <div class="form-actions" style="grid-column: 1 / -1;">
                        <button type="button" class="btn btn-secondary" onclick="closeEmailCalendarModal()">Cancel</button>
                        <button type="submit" form="email-calendar-form" class="btn btn-primary">Send & Schedule</button>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing modal if any
        const existingModal = document.getElementById('email-calendar-modal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // Add modal to body
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Set default date to tomorrow
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        document.getElementById('interview-date').value = tomorrow.toISOString().split('T')[0];
        
        // Load calendar events if Google Calendar is connected
        loadCalendarEvents();
        
        // Handle checkbox toggle
        document.getElementById('schedule-calendar').addEventListener('change', function(e) {
            const calendarFields = document.getElementById('calendar-fields');
            calendarFields.style.display = e.target.checked ? 'block' : 'none';
            const requiredFields = calendarFields.querySelectorAll('input[required]');
            requiredFields.forEach(field => {
                field.required = e.target.checked;
            });
        });
        
        // Handle form submission
        document.getElementById('email-calendar-form').addEventListener('submit', function(e) {
            e.preventDefault();
            submitEmailCalendar(data.resumeId);
        });
    }
    
    function loadCalendarEvents() {
        fetch('/api/google-calendar/events/')
            .then(response => response.json())
            .then(data => {
                const eventsContainer = document.getElementById('calendar-events');
                if (data.events && data.events.length > 0) {
                    let eventsHTML = '<div style="font-size: 0.875rem;">';
                    data.events.forEach(event => {
                        const eventDate = new Date(event.start).toLocaleString();
                        eventsHTML += `
                            <div style="padding: 0.75rem; border-bottom: 1px solid #e5e7eb; cursor: pointer;" 
                                 onclick="selectEventTime('${event.start}', '${event.end}')"
                                 title="Click to schedule interview">
                                <p style="margin: 0; font-weight: 500; color: #1f2937;">${event.title}</p>
                                <p style="margin: 0.25rem 0; color: #6b7280; font-size: 0.75rem;">${eventDate}</p>
                            </div>
                        `;
                    });
                    eventsHTML += '</div>';
                    eventsContainer.innerHTML = eventsHTML;
                } else {
                    eventsContainer.innerHTML = '<p style="text-align: center; color: #9ca3af; padding: 1rem;">No upcoming events<br><small>Connect Google Calendar from Settings</small></p>';
                }
            })
            .catch(error => {
                console.log('Calendar not connected:', error);
                document.getElementById('calendar-events').innerHTML = '<p style="text-align: center; color: #9ca3af; padding: 1rem;">Calendar not available<br><small><a href="/settings/" target="_blank">Connect in Settings</a></small></p>';
            });
    }
    
    function selectEventTime(startTime, endTime) {
        const startDate = new Date(startTime);
        const dateStr = startDate.toISOString().split('T')[0];
        const timeStr = startDate.toTimeString().split(':').slice(0, 2).join(':');
        
        document.getElementById('interview-date').value = dateStr;
        document.getElementById('interview-time').value = timeStr;
        
        // Highlight the selected time
        event.currentTarget.style.backgroundColor = '#dbeafe';
    }
    
    window.closeEmailCalendarModal = function() {
        const modal = document.getElementById('email-calendar-modal');
        if (modal) {
            modal.remove();
        }
    };
    
    function submitEmailCalendar(resumeId) {
        const candidateEmail = document.getElementById('candidate-email-input').value;
        const subject = document.getElementById('email-subject').value;
        const body = document.getElementById('email-body').value;
        const scheduleCalendar = document.getElementById('schedule-calendar').checked;
        
        const data = {
            resume_id: resumeId,
            candidate_email: candidateEmail,
            subject: subject,
            body: body,
            schedule_calendar: scheduleCalendar
        };
        
        if (scheduleCalendar) {
            data.interview_date = document.getElementById('interview-date').value;
            data.interview_time = document.getElementById('interview-time').value;
            data.duration = parseInt(document.getElementById('interview-duration').value);
            data.location = document.getElementById('interview-location').value;
        }
        
        fetch('/api/send-email-calendar/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': utils.getCsrfToken()
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                // Open mailto link
                if (result.mailto_link) {
                    window.location.href = result.mailto_link;
                }
                
                // Open calendar link if available
                if (result.calendar_link && scheduleCalendar) {
                    setTimeout(function() {
                        window.open(result.calendar_link, '_blank');
                    }, 500);
                }
                
                utils.showAlert('Email client opened! Please send the email and add the calendar event.', 'success');
                closeEmailCalendarModal();
            } else {
                utils.showAlert(result.error || 'Failed to send email', 'error');
            }
        })
        .catch(error => {
            console.error('Error sending email:', error);
            utils.showAlert('Failed to send email. Please try again.', 'error');
        });
    }
});

