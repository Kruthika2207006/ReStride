# Security Policy & Hardening Controls

This document details the production security policies, network safeguards, input validators, and file-upload guardrails implemented across the Prosthetic Socket AI backend.

---

## 1. Cross-Origin Resource Sharing (CORS) Whitelisting
CORS is restricted to authorized domain origins using the `ALLOWED_ORIGINS` environment variable:
- **Default**: Whitelists all origins (`*`) during local development if the variable is omitted or set to `*`.
- **Production**: Should be set to a comma-separated list of trusted client domains (e.g. `ALLOWED_ORIGINS=https://restride-app.com,https://dashboard.restride-app.com`).
- **Methods Restricted**: Only `GET`, `POST`, `PUT`, `DELETE`, and `OPTIONS` operations are allowed.

---

## 2. API Authentication (X-API-Key Header)
Access to all `/api` endpoints is restricted via Header-based API key checks:
- **Header Field**: `X-API-Key`
- **Configuration**: Set `API_KEY` in the `.env` file to require key authentication.
- **Bypass Rule**: If `API_KEY` is not set or empty, authentication is bypassed for development ease. Additionally, pre-flight `OPTIONS` requests and interactive API documentation paths (`/docs`, `/redoc`, `/openapi.json`) are always whitelisted to ensure Swagger UI functions cleanly.
- **Fail Response**: Requests with invalid/missing headers receive `401 Unauthorized` with body:
  ```json
  {"detail": "Invalid or missing API Key in X-API-Key header."}
  ```

---

## 3. Demographics Schema Validation & Sanitization
Input payloads are verified at the server entrance by strict Pydantic schemas:
- **Age Bounds**: Patient age is verified to be within `0 < age < 120` (`gt=0`, `lt=120`).
- **Alphanumeric ID Constraint**: `patient_id` must match pattern `^[a-zA-Z0-9\-]+$`. Special characters or path injection symbols are rejected.
- **Failed Input Response**: Any out-of-bound inputs result in `422 Unprocessable Entity` containing clear structural details on validation failures.

---

## 4. File Upload Safeguards
Robust controls prevent upload denial-of-service (DoS) or file-system poisoning:
- **Size Bounds**: Individual files are checked against `MAX_IMAGE_SIZE_MB` (default `10MB`).
- **File Extensions**: Restricts uploads strictly to `ALLOWED_EXTENSIONS` (`.jpg`, `.jpeg`, `.png`, `.bmp`, `.tiff`).
- **File Count Limit**: A maximum of `10` files (`MAX_FILES_PER_UPLOAD = 10`) can be uploaded per API call.
- **Path Traversal Shield**: Filenames are extracted using `os.path.basename` and joined to resolve absolute paths. The server asserts that the resolved absolute path remains within the designated upload directory. Any traversal attempt (e.g., uploading files with `../` characters) is rejected with `400 Bad Request`.
- **Filename Collision Prevention**: Saved files are prefixed with a high-resolution millisecond timestamp (e.g., `{timestamp}_{original_basename}`) to ensure no two uploads collide or overwrite existing files.

---

## 5. Deployment Error Shielding
To prevent leak of internal stack traces, debug/development tracebacks are caught by a global FastAPI `Exception` decorator:
- Logs full exceptions internally with a UUID-based correlation ID.
- Masked generic output returned to client:
  ```json
  {
    "detail": "Internal server error. Please contact support.",
    "correlation_id": "8b5f39cd-1e24-4f05-950c-e2f4948a4dcf"
  }
  ```
