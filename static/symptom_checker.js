document.addEventListener('DOMContentLoaded', () => {
    // --- NEW FILE ---
    // - This file makes the Symptom Checker page functional.
    // - It connects the button to the backend API and displays the result.
    // ----------------

    const checkBtn = document.getElementById('check-symptoms-btn');
    const symptomsInput = document.getElementById('symptoms-input');
    const resultBox = document.getElementById('result-box');
    const recommendationText = document.getElementById('recommendation-text');

    checkBtn.addEventListener('click', async () => {
        const symptoms = symptomsInput.value.trim();
        if (symptoms === '') {
            alert('Please describe your symptoms.');
            return;
        }

        try {
            const response = await fetch('/api/symptom-check', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symptoms })
            });

            if (!response.ok) {
                throw new Error('Failed to get recommendation.');
            }

            const data = await response.json();
            recommendationText.textContent = `Based on your symptoms, we recommend you see ${data.recommendation}.`;
            resultBox.classList.remove('hidden');

        } catch (error) {
            recommendationText.textContent = `Error: ${error.message}`;
            resultBox.classList.remove('hidden');
        }
    });
});