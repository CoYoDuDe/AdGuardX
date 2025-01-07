
document.addEventListener('DOMContentLoaded', () => {
    const statsDiv = document.getElementById('stats');
    fetch('http://127.0.0.1:5000/api/stats')
        .then(response => response.json())
        .then(data => {
            statsDiv.innerHTML = `
                <p>Blocked Requests: ${data.blocked_requests}</p>
                <p>Allowed Requests: ${data.allowed_requests}</p>
            `;
        })
        .catch(error => {
            statsDiv.innerHTML = `<p>Error loading statistics: ${error.message}</p>`;
            console.error('Error fetching stats:', error);
        });
});
