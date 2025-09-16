# Healthcare Assistant Project

This project consists of a Python Flask backend and a React frontend.

## Prerequisites

*   [Docker](https://www.docker.com/get-started)
*   [Node.js](https://nodejs.org/) (v18 or later)
*   [Python](https://www.python.org/downloads/) (v3.11+)

---

## 1. Backend Setup (Python / Flask)

The backend serves the core API. You can run it using Docker (recommended) or a local Python environment.

### Running with Docker (Recommended)

This is the easiest way to get the backend running.

1.  **Build the Docker image:**
    ```bash
    docker build -t healthcare-app-backend .
    ```

2.  **Run the container:**
    ```bash
    docker run -p 8080:8080 healthcare-app-backend
    ```
    The backend will be available at `http://localhost:8080`.

### Running Locally (Alternative)

1.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the server:**
    ```bash
    gunicorn --bind :8080 --workers 2 --threads 4 server:app
    ```

---

## 2. Frontend Setup (React / Vite)

The frontend is a standard React application.

1.  **Navigate to the UI directory:**
    ```bash
    cd healthcare-assistant-ui
    ```

2.  **Install dependencies:**
    ```bash
    npm install
    ```

3.  **Start the development server:**
    ```bash
    npm run dev
    ```
    The UI will be available at the address shown in your terminal (usually `http://localhost:5173`).
