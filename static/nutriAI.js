document.addEventListener("DOMContentLoaded", () => {
    const getDietBtn = document.getElementById('getDietBtn');
    const routineBox = document.getElementById('routineBox');

    if (getDietBtn) {
        getDietBtn.addEventListener('click', () => {
            const name = document.getElementById('name').value.trim();
            const disease = document.getElementById('disease').value.trim();
            const healthRecords = document.getElementById('healthRecords').value.trim();

            if (name === "" || disease === "" || healthRecords === "") {
                alert("Please fill in all details to get a recommendation.");
                return;
            }

            // Show a loading message
            routineBox.style.display = "block";
            routineBox.innerHTML = `<p>Analyzing your details and generating a diet plan...</p>`;

            const dietRequestData = {
                disease: disease
            };

            fetch('/api/diet-recommendation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(dietRequestData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    throw new Error(data.error);
                }
                
                routineBox.innerHTML = `
                    <h3>AI Diet Recommendation for ${name}</h3>
                    <p><strong>Condition:</strong> ${disease}</p>
                    <p><strong>Recommended Diet:</strong> ${data.diet}</p>
                    <hr>
                    <p><em>This is an AI-generated suggestion. Always consult with a certified doctor or nutritionist for a personalized diet plan.</em></p>
                `;
            })
            .catch(error => {
                routineBox.innerHTML = `<p style="color: red;">Error: Could not retrieve a recommendation. ${error.message}</p>`;
                console.error('Error:', error);
            });
        });
    }
});