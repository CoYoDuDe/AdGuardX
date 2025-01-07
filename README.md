
# AdGuardX_Project

AdGuardX is a powerful modular system for managing network requests, DNS blocking, and filtering rules.

## Features
- HTTP/HTTPS filtering
- DNS-based blocking and source list management
- User-friendly web interface with Flask and Node.js

## Installation
1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Install Node.js dependencies:
   ```bash
   npm install
   ```
3. Start the backend server:
   ```bash
   python run.py
   ```
4. Start the frontend development server (if required):
   ```bash
   npm start
   ```

## Configuration
- Edit `config/default_config.json` to customize settings for the HTTP/HTTPS server and DNS filtering.

## Web Interface
Visit `http://127.0.0.1:5000` to access the AdGuardX Dashboard.
