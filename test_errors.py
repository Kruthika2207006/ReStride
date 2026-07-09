"""Integration tests to verify robust error handling, schema validations, and exception tracking."""

import os
import sys
import asyncio
import httpx
import shutil
import subprocess

# Ensure project root is in Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.database import patients_collection, analysis_collection


async def cleanup_db(patient_id: str):
    """Cleans up the database records for the test patient."""
    try:
        await patients_collection.delete_one({"_id": patient_id})
        await analysis_collection.delete_one({"_id": patient_id})
        print(f"[+] Cleaned database records for: {patient_id}")
    except Exception as e:
        print(f"[-] Database cleanup failed for {patient_id}: {e}")


async def main():
    print("=== Launching FastAPI Server Process on Port 8081 with INVALID API Key ===")
    
    test_patient_id = "PAT-ERR-TEST-99"
    upload_dir = os.path.join(project_root, "uploads", test_patient_id)
    
    # Clean up prior data
    await cleanup_db(test_patient_id)
    if os.path.exists(upload_dir):
        shutil.rmtree(upload_dir)

    # 1. Start uvicorn with GOOGLE_API_KEY set to dummy to force failure in background task
    env_override = os.environ.copy()
    env_override["GOOGLE_API_KEY"] = "DUMMY_INVALID_KEY_TO_FORCE_API_FAILURE"
    
    server_process = subprocess.Popen(
        ["uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8081"],
        stdout=None,
        stderr=None,
        env=env_override,
        text=True,
    )

    # Wait for the server port to open dynamically
    print("Waiting for uvicorn server to start and bind to port 8081...")
    server_ready = False
    for attempt in range(1, 20):
        await asyncio.sleep(1.0)
        if server_process.poll() is not None:
            print("[-] Uvicorn process terminated unexpectedly.")
            sys.exit(1)
        try:
            async with httpx.AsyncClient(base_url="http://127.0.0.1:8081", timeout=1.0) as client:
                # Query test-error endpoint (should return 500 once server is running)
                res = await client.get("/api/test-error")
                server_ready = True
                print(f"[+] Server is ready and listening after {attempt} seconds.")
                break
        except (httpx.ConnectError, httpx.ConnectTimeout):
            pass

    if not server_ready:
        print("[-] Uvicorn failed to become responsive within 20 seconds.")
        server_process.terminate()
        sys.exit(1)

    base_url = "http://127.0.0.1:8081"
    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
            # Test Scenario 1: Malformed JSON to /api/patient (Validation bounds)
            print("\n--- Test 1: POST /api/patient with negative age and weight (422) ---")
            patient_invalid_payload = {
                "patient_id": test_patient_id,
                "full_name": "Error Test Patient",
                "age": -5,  # Constraint: gt=0
                "gender": "Male",
                "weight_kg": -10.5,  # Constraint: gt=0.0
                "height_cm": 0.0,  # Constraint: gt=0.0
                "activity_level": "K3",
                "amputation_level": "transtibial",
                "clinical_history": {},
                "limb_details": {}
            }
            res_invalid = await client.post("/api/patient", json=patient_invalid_payload)
            print(f"Status Code: {res_invalid.status_code}")
            print(f"Response: {res_invalid.json()}")
            assert res_invalid.status_code == 422, "Expected 422 Unprocessable Entity for invalid parameters!"
            print("[+] Test 1 PASSED: Correctly rejected malformed demographic fields.")

            # Test Scenario 2: Unhandled exception correlation ID (500)
            print("\n--- Test 2: GET /api/test-error (500) ---")
            res_error = await client.get("/api/test-error")
            print(f"Status Code: {res_error.status_code}")
            error_data = res_error.json()
            print(f"Response Body: {error_data}")
            assert res_error.status_code == 500, "Expected 500 Internal Server Error!"
            assert "correlation_id" in error_data, "Expected a correlation_id in response payload!"
            assert error_data.get("detail") == "Internal server error. Please contact support.", "Expected user-friendly message!"
            print(f"[+] Test 2 PASSED: Received correlation ID: {error_data.get('correlation_id')}")

            # Test Scenario 3: Register valid patient and upload images with missing API key context
            print("\n--- Test 3: Register valid patient and trigger pipeline with bad key ---")
            patient_payload = {
                "patient_id": test_patient_id,
                "full_name": "API Error Patient",
                "age": 45,
                "gender": "Male",
                "weight_kg": 75.0,
                "height_cm": 170.0,
                "activity_level": "K3",
                "amputation_level": "transtibial",
                "clinical_history": {},
                "limb_details": {}
            }
            res_valid_patient = await client.post("/api/patient", json=patient_payload)
            assert res_valid_patient.status_code == 201, "Failed to register valid patient!"

            # Upload dummy jpeg file
            dummy_file = os.path.join(project_root, "dummy_err.jpg")
            with open(dummy_file, "wb") as f:
                f.write(b"dummy image content bytes")

            try:
                with open(dummy_file, "rb") as f_in:
                    files_payload = [
                        ("files", ("dummy_err.jpg", f_in, "image/jpeg")),
                    ]
                    res_upload = await client.post(f"/api/upload/{test_patient_id}", files=files_payload)
                assert res_upload.status_code == 202, "Expected 202 accepted status code!"
            finally:
                if os.path.exists(dummy_file):
                    os.remove(dummy_file)

            # Poll status until status becomes 'failed'
            print("\n--- Test 4: Polling status for PAT-ERR-TEST-99 (expecting 'failed') ---")
            max_polls = 20
            poll_interval = 2.0
            failed_state = False
            error_msg = ""
            progress_val = -1

            for poll in range(1, max_polls + 1):
                await asyncio.sleep(poll_interval)
                res_status = await client.get(f"/api/analysis/{test_patient_id}")
                assert res_status.status_code == 200, "Failed to fetch analysis status!"
                status_data = res_status.json()
                
                print(f"Poll #{poll}: status='{status_data.get('status')}', progress={status_data.get('progress')}%, error='{status_data.get('error')}'")
                
                if status_data.get("status") == "failed":
                    failed_state = True
                    error_msg = status_data.get("error")
                    progress_val = status_data.get("progress")
                    break
                elif status_data.get("status") == "completed":
                    print("[-] Error Scenario Failed: Pipeline completed successfully but should have failed!")
                    break

            assert failed_state, "Expected analysis pipeline to fail due to invalid/missing Gemini API key!"
            assert progress_val == 0.0, f"Expected progress to reset to 0.0 on failure, but got: {progress_val}"
            assert error_msg is not None and len(error_msg) > 0, "Expected an error message stored in the database!"
            print(f"[+] Test 3 & 4 PASSED: Pipeline failed as expected with progress=0.0.")
            print(f"[+] Stored DB Error Message: {error_msg}")

            print("\n[+] ALL ERROR SCENARIOS COMPLETED AND VALIDATED SUCCESSFULLY!")

    except Exception as e:
        print(f"\n[-] Integration Error Scenario Test FAILED: {e}")
        sys.exit(1)

    finally:
        # Shut down server and cleanup
        print("\n--- Terminating FastAPI Server & Cleaning database collections ---")
        server_process.terminate()
        server_process.wait()

        await cleanup_db(test_patient_id)
        if os.path.exists(upload_dir):
            try:
                shutil.rmtree(upload_dir)
            except Exception:
                pass
        print("[+] Cleanup complete.")


if __name__ == "__main__":
    asyncio.run(main())
