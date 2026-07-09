"""Integration tests to verify API key security, CORS configurations, schema sanitizations, and upload limits."""

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
    print("=== Launching FastAPI Server Process on Port 8082 for Security Verification ===")
    
    test_patient_id = "PAT-SEC-TEST-99"
    upload_dir = os.path.join(project_root, "uploads", test_patient_id)
    
    # Clean up prior data
    await cleanup_db(test_patient_id)
    if os.path.exists(upload_dir):
        shutil.rmtree(upload_dir)

    # 1. Start uvicorn with API_KEY configuration enforced
    env_override = os.environ.copy()
    env_override["API_KEY"] = "TEST-API-SECRET-12345"
    env_override["ALLOWED_ORIGINS"] = "http://localhost:3000,http://trusted-client.com"
    
    server_process = subprocess.Popen(
        ["uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8082"],
        stdout=None,
        stderr=None,
        env=env_override,
        text=True,
    )

    # Wait for the server port to open dynamically
    print("Waiting for server on 8082 to start and bind...")
    server_ready = False
    for attempt in range(1, 20):
        await asyncio.sleep(1.0)
        if server_process.poll() is not None:
            print("[-] Uvicorn process terminated unexpectedly.")
            sys.exit(1)
        try:
            # Query /docs directly (docs are bypassed from API key validation)
            async with httpx.AsyncClient(base_url="http://127.0.0.1:8082", timeout=1.0) as client:
                res = await client.get("/openapi.json")
                if res.status_code == 200:
                    server_ready = True
                    print(f"[+] Server is ready after {attempt} seconds.")
                    break
        except (httpx.ConnectError, httpx.ConnectTimeout):
            pass

    if not server_ready:
        print("[-] Uvicorn failed to start on 8082.")
        server_process.terminate()
        sys.exit(1)

    base_url = "http://127.0.0.1:8082"
    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
            
            # Scenario 1: Verify API Key Lock on endpoints
            print("\n--- Test 1: API Key Locking (Missing and Invalid headers) ---")
            res_locked = await client.post("/api/patient", json={})
            print(f"No Header -> Status Code: {res_locked.status_code}")
            assert res_locked.status_code == 401, "Expected 401 Unauthorized for missing API key!"
            
            res_bad_key = await client.post(
                "/api/patient", 
                json={}, 
                headers={"X-API-Key": "WRONG_SECRET"}
            )
            print(f"Wrong Header Key -> Status Code: {res_bad_key.status_code}")
            assert res_bad_key.status_code == 401, "Expected 401 Unauthorized for invalid API key!"
            print("[+] Test 1 PASSED: API key authentication locks working properly.")

            # Scenario 2: Verify Docs Whitelist (Swagger docs accessible without key)
            print("\n--- Test 2: Docs Whitelist Check ---")
            res_docs = await client.get("/docs")
            print(f"GET /docs -> Status Code: {res_docs.status_code}")
            assert res_docs.status_code == 200, "Docs endpoint should be whitelisted!"
            print("[+] Test 2 PASSED: Swagger UI is accessible without API key.")

            # Scenario 3: Verify CORS Whitelisting
            print("\n--- Test 3: CORS whitelisting checks ---")
            # OPTIONS pre-flight request for trusted origin
            headers_options = {
                "Origin": "http://trusted-client.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "X-API-Key, Content-Type",
            }
            res_cors_ok = await client.options("/api/patient", headers=headers_options)
            print(f"CORS preflight (trusted Origin) -> Status Code: {res_cors_ok.status_code}")
            print(f"Headers: {dict(res_cors_ok.headers)}")
            assert "access-control-allow-origin" in res_cors_ok.headers, "CORS headers should be present!"
            assert res_cors_ok.headers["access-control-allow-origin"] == "http://trusted-client.com", "Expected trusted origin allowed!"
            
            # OPTIONS pre-flight for untrusted origin
            headers_options_untrusted = {
                "Origin": "http://malicious-attacker.com",
                "Access-Control-Request-Method": "POST",
            }
            res_cors_bad = await client.options("/api/patient", headers=headers_options_untrusted)
            print(f"CORS preflight (untrusted Origin) -> Status Code: {res_cors_bad.status_code}")
            # Untrusted origin should NOT have Access-Control-Allow-Origin header matching its origin
            allowed_origin = res_cors_bad.headers.get("access-control-allow-origin")
            assert allowed_origin != "http://malicious-attacker.com", "Untrusted CORS origin allowed!"
            print("[+] Test 3 PASSED: CORS whitelisting works correctly.")

            # Scenario 4: Alphanumeric and hyphens constraint on patient_id, and age limit
            print("\n--- Test 4: Patient schema validator constraints (special characters in patient_id and age ceiling) ---")
            patient_special_id = {
                "patient_id": "PAT#SPECIAL_ID_123",  # Hash is invalid
                "full_name": "Security Test",
                "age": 55,
                "gender": "Male",
                "weight_kg": 75.0,
                "height_cm": 175.0,
                "activity_level": "K3",
                "amputation_level": "transtibial",
            }
            res_special_id = await client.post(
                "/api/patient", 
                json=patient_special_id, 
                headers={"X-API-Key": "TEST-API-SECRET-12345"}
            )
            print(f"Special Char patient_id -> Status Code: {res_special_id.status_code}")
            assert res_special_id.status_code == 422, "Expected 422 for invalid patient_id pattern!"

            patient_age_ceiling = {
                "patient_id": test_patient_id,
                "full_name": "Security Test Too Old",
                "age": 140,  # Ceiling is lt=120
                "gender": "Male",
                "weight_kg": 75.0,
                "height_cm": 175.0,
                "activity_level": "K3",
                "amputation_level": "transtibial",
            }
            res_age_ceiling = await client.post(
                "/api/patient", 
                json=patient_age_ceiling, 
                headers={"X-API-Key": "TEST-API-SECRET-12345"}
            )
            print(f"Age ceiling 140 -> Status Code: {res_age_ceiling.status_code}")
            assert res_age_ceiling.status_code == 422, "Expected 422 for out-of-bounds patient age!"
            print("[+] Test 4 PASSED: Schema constraints (regex pattern and lt=120) verified.")

            # Scenario 5: Register valid patient and verify file upload limits
            print("\n--- Test 5: Register valid patient and test upload limits (max 10 files) ---")
            patient_ok = {
                "patient_id": test_patient_id,
                "full_name": "Security Test OK",
                "age": 35,
                "gender": "Male",
                "weight_kg": 80.0,
                "height_cm": 180.0,
                "activity_level": "K3",
                "amputation_level": "transtibial",
            }
            res_patient_ok = await client.post(
                "/api/patient", 
                json=patient_ok, 
                headers={"X-API-Key": "TEST-API-SECRET-12345"}
            )
            assert res_patient_ok.status_code == 201, "Failed to register valid patient profile!"

            # Upload more than 10 files (we attempt 11)
            files_payload = []
            for i in range(11):
                files_payload.append(("files", (f"img_{i}.jpg", b"dummy content", "image/jpeg")))
                
            res_too_many = await client.post(
                f"/api/upload/{test_patient_id}", 
                files=files_payload, 
                headers={"X-API-Key": "TEST-API-SECRET-12345"}
            )
            print(f"Uploading 11 files -> Status Code: {res_too_many.status_code}")
            print(f"Response: {res_too_many.json()}")
            assert res_too_many.status_code == 400, "Expected 400 Bad Request for file count exceeded!"
            assert "Maximum files allowed per upload" in res_too_many.json().get("detail", ""), "Expected file count limit warning!"
            print("[+] Test 5 PASSED: Upload file count limit enforced.")

            print("\n[+] ALL SECURITY HARDENING SCENARIOS VERIFIED SUCCESSFULLY!")

    except Exception as e:
        print(f"\n[-] Security Verification Test FAILED: {e}")
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
