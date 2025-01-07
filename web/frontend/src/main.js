
console.log('AdGuardX Frontend Loaded');
fetch('/api/stats')
    .then(response => response.json())
    .then(data => console.log(data));
