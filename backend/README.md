# Backend REST API server - Prosthetic Socket Recommendation System

This directory contains the REST API server code, database configuration modules, and Pydantic schema validations for integration with MongoDB.

---

## 💾 Database Configuration

The application uses **MongoDB** as the central storage repository for saving patient clinical history, residual limb measurements, and AI Agent evaluation statuses.

### Option 1: Running MongoDB via Docker (Recommended)
If you have Docker installed, you can start a MongoDB container with a single command:
```bash
docker run -d --name prosthetic-mongo -p 27017:27017 -v mongo_data:/data/db mongo:latest
```

### Option 2: Running MongoDB Locally (Windows Service)
1. Download the **MongoDB Community Server** installer from the official MongoDB website.
2. Complete the installation and ensure that the **MongoDB Server (MongoDB)** service is running in Windows Services:
   *   Press `Win + R`, type `services.msc`, and press Enter.
   *   Find **MongoDB Server** and verify its status is **Running** (or start it manually).
3. Alternatively, start it via PowerShell (Administrator):
   ```powershell
   Start-Service -Name MongoDB
   ```

---

## 🛠️ Configuration & Verification

1. Ensure your `.env` file at the project root is properly configured with your database URI and name:
   ```env
   MONGO_URI=mongodb://localhost:27017
   DB_NAME=prosthetic_db
   ```

2. Run the integration test script from the project root folder to verify connectivity, insertion, and retrieval of documents:
   ```bash
   python test_db.py
   ```

   **Expected success output:**
   ```text
   === Starting MongoDB Connection and CRUD Helpers Test ===

   1. Inserting dummy patient with ID: PAT-DB-TEST-99
   [+] Successfully inserted patient ID: PAT-DB-TEST-99

   2. Retrieving patient profile with ID: PAT-DB-TEST-99
   [+] Retrieved Patient Doc: {'_id': 'PAT-DB-TEST-99', ...}

   3. Initializing analysis for patient: PAT-DB-TEST-99
   [+] Analysis document initialized.

   4. Updating analysis fields to processing status...
   [+] Analysis updated.

   5. Retrieving updated analysis document:
   [+] Retrieved Analysis Doc: {'_id': 'PAT-DB-TEST-99', 'status': 'processing', 'progress': 25.0, ...}

   6. Cleaning up test records from collections...
   [+] Patient delete count: 1
   [+] Analysis delete count: 1

   [+] ALL MONGODB INTEGRATION TESTS COMPLETED SUCCESSFULLY!
   ```

---

## 🚀 Running the FastAPI REST API Server

### 1. Launch the Server
To start the development API server with auto-reload enabled:
```bash
uvicorn backend.main:app --reload
```
By default, the server will start listening on **http://127.0.0.1:8000**.

### 2. Access the Interactive API Documentation (Swagger)
Once the server is running, you can view the automatically generated interactive docs:
*   **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
*   **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

These interactive UIs allow you to test endpoints directly from the browser.

### 3. Verify Endpoints via Script
We have provided an automated test script `test_endpoints.py` at the project root. To spin up the server, register a test patient, upload test images, and clean up the database:
```bash
python test_endpoints.py
```
