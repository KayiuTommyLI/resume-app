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
        
        // The original check is fine, but you could enhance it to check for storyFile too
        if (!jobDescription || !resumeFile || !storyFile) {
            alert('Please fill out the job description and provide both PDF files.');
            return;
        }

        spinnerOverlay.style.display = 'flex';
        resultContainer.style.display = 'none';

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

        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred: ' + error.message);
        } finally {
            spinnerOverlay.style.display = 'none';
        }
    });

    // --- ACCORDION LOGIC ---
    document.querySelectorAll('.accordion-button').forEach(button => {
        button.addEventListener('click', () => {
            const content = document.getElementById(button.getAttribute('data-target'));
            if (content.style.maxHeight) {
                content.style.maxHeight = null;
            } else {
                // Close all other accordions first
                document.querySelectorAll('.accordion-content').forEach(c => c.style.maxHeight = null);
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
                const originalText = button.textContent;
                button.textContent = 'Copied!';
                setTimeout(() => button.textContent = originalText, 2000);
            });
        });
    });
});