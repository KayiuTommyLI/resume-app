document.addEventListener('DOMContentLoaded', function() {
    const applicationForm = document.getElementById('application-form');
    const spinnerOverlay = document.getElementById('spinner-overlay');
    const resultContainer = document.getElementById('result-container');

    // --- FORM SUBMISSION ---
    applicationForm.addEventListener('submit', async function(event) {
        event.preventDefault();
        const jobDescription = document.getElementById('jd-input').value;
        const resumeFile = document.getElementById('resume-upload').files[0];
        const storyFile = document.getElementById('story-upload').files[0];
        
        if (!jobDescription || !resumeFile || !storyFile) {
            showNotification('Please fill out the job description and provide both PDF files.', 'error');
            return;
        }

        spinnerOverlay.style.display = 'flex';
        resultContainer.style.display = 'none';
        
        // Scroll to top when processing starts
        window.scrollTo({ top: 0, behavior: 'smooth' });

        const formData = new FormData();
        formData.append('job_description', jobDescription);
        formData.append('master_resume_file', resumeFile);
        formData.append('story_file', storyFile);

        try {
            const response = await fetch('http://127.0.0.1:8000/generate-full-application/', {
                method: 'POST',
                body: formData,
            });

            const result = await response.json();

            if (!response.ok) throw new Error(result.detail || `HTTP error! status: ${response.status}`);
            
            // Populate all sections with results
            document.getElementById('analysis-output').innerHTML = marked.parse(`**Keywords & Persona:**\n\`\`\`json\n${JSON.stringify(result.analysis, null, 2)}\n\`\`\``);
            document.getElementById('resume-output').innerHTML = marked.parse(result.resume);
            document.getElementById('review-output').innerHTML = marked.parse(result.review);
            document.getElementById('cover-letter-output').innerHTML = marked.parse(result.cover_letter);
            
            resultContainer.style.display = 'block';
            
            // Scroll to results
            setTimeout(() => {
                resultContainer.scrollIntoView({ behavior: 'smooth' });
            }, 300);

            showNotification('Application package generated successfully!', 'success');

        } catch (error) {
            console.error('Error:', error);
            showNotification('An error occurred: ' + error.message, 'error');
        } finally {
            spinnerOverlay.style.display = 'none';
        }
    });

    // --- ACCORDION LOGIC ---
    document.querySelectorAll('.accordion-button').forEach(button => {
        button.addEventListener('click', () => {
            const isActive = button.classList.contains('active');
            const content = document.getElementById(button.getAttribute('data-target'));
            
            // Close all accordions first
            document.querySelectorAll('.accordion-button').forEach(btn => {
                btn.classList.remove('active');
            });
            document.querySelectorAll('.accordion-content').forEach(c => {
                c.style.maxHeight = null;
            });
            
            // If this wasn't active, open it
            if (!isActive) {
                button.classList.add('active');
                content.style.maxHeight = content.scrollHeight + "px";
            }
        });
    });

    // --- COPY BUTTON LOGIC ---
    document.querySelectorAll('.copy-button').forEach(button => {
        button.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent accordion from closing
            const targetId = button.getAttribute('data-copy-target');
            const textToCopy = document.getElementById(targetId).innerText;

            navigator.clipboard.writeText(textToCopy).then(() => {
                const icon = button.querySelector('i');
                const text = button.querySelector(':not(i)');
                const originalIcon = icon.className;
                const originalText = text ? text.textContent : button.textContent;
                
                // Update button appearance
                button.classList.add('copied');
                icon.className = 'fas fa-check';
                if (text) text.textContent = 'Copied!';
                else button.innerHTML = '<i class="fas fa-check"></i> Copied!';
                
                // Reset after 2 seconds
                setTimeout(() => {
                    button.classList.remove('copied');
                    icon.className = originalIcon;
                    if (text) text.textContent = originalText;
                    else button.innerHTML = '<i class="fas fa-copy"></i> ' + originalText.replace('Copied!', '').trim();
                }, 2000);
            }).catch(() => {
                showNotification('Failed to copy to clipboard', 'error');
            });
        });
    });

    // --- NOTIFICATION SYSTEM ---
    function showNotification(message, type = 'info') {
        // Remove existing notifications
        const existingNotifications = document.querySelectorAll('.notification');
        existingNotifications.forEach(n => n.remove());

        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            z-index: 10000;
            transform: translateX(100%);
            transition: transform 0.3s ease;
            max-width: 400px;
            box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
        `;

        // Set background color based on type
        const colors = {
            success: '#10b981',
            error: '#ef4444',
            warning: '#f59e0b',
            info: '#3b82f6'
        };
        notification.style.background = colors[type] || colors.info;

        notification.textContent = message;
        document.body.appendChild(notification);

        // Animate in
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 100);

        // Auto remove after 5 seconds
        setTimeout(() => {
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }

    // --- FILE UPLOAD ENHANCEMENT ---
    document.querySelectorAll('input[type="file"]').forEach(input => {
        input.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                showNotification(`File "${file.name}" uploaded successfully`, 'success');
            }
        });
    });
});