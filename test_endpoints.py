"""REST endpoint integration test script to verify FastAPI endpoints asynchronously using httpx."""

import subprocess
import time
import os
import sys
import shutil
import asyncio
import httpx

# Ensure the project root is in the path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.database import patients_collection, analysis_collection


async def cleanup_db(patient_id):
    """Asynchronously cleans up test records from patients and analyses collections."""
    try:
        await patients_collection.delete_one({"_id": patient_id})
        await analysis_collection.delete_one({"_id": patient_id})
    except Exception as e:
        print(f"[-] Database cleanup failed: {e}")


async def main():
    print("=== Launching FastAPI Server Process ===")

    test_patient_id = "PAT-REST-TEST-99"
    upload_dir = os.path.join(project_root, "uploads", test_patient_id)

    # 1. Clear any conflicting test data from prior aborted runs
    await cleanup_db(test_patient_id)
    if os.path.exists(upload_dir):
        shutil.rmtree(upload_dir)

    # 2. Launch FastAPI with Uvicorn server in a subprocess
    server_process = subprocess.Popen(
        ["uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8080"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Wait for the server port to open
    await asyncio.sleep(3)

    if server_process.poll() is not None:
        print("[-] Uvicorn failed to start. Logs:")
        stdout, stderr = server_process.communicate()
        print(stderr)
        sys.exit(1)

    print("[+] FastAPI Server is up and running on http://127.0.0.1:8080")

    try:
        async with httpx.AsyncClient(base_url="http://127.0.0.1:8080", timeout=10.0) as client:
            # 3. Test POST /api/patient
            print("\n--- Test 1: POST /api/patient ---")
            patient_payload = {
                "patient_id": test_patient_id,
                "full_name": "REST Test Patient",
                "age": 52,
                "gender": "Female",
                "weight_kg": 68.0,
                "height_cm": 164.0,
                "activity_level": "K2",
                "amputation_level": "transtibial",
                "clinical_history": {"has_diabetes": False, "has_neuropathy": True},
                "limb_details": {"shape": "cylindrical", "length_cm": 15.0},
            }

            res1 = await client.post("/api/patient", json=patient_payload)
            print(f"Status Code: {res1.status_code}")
            print(f"Response Body: {res1.json()}")
            assert res1.status_code == 201, "Error: Expected 201 Created status code!"

            # Test Duplicate Registration Check
            print("\n--- Test 1b: Duplicate Registration Check ---")
            res1_dup = await client.post("/api/patient", json=patient_payload)
            print(f"Status Code: {res1_dup.status_code}")
            print(f"Response Body: {res1_dup.json()}")
            assert res1_dup.status_code == 400, "Error: Expected 400 duplicate error!"

            # 4. Test POST /api/upload/{patient_id}
            print("\n--- Test 2: POST /api/upload/{patient_id} ---")
            dummy_file1 = os.path.join(project_root, "dummy_view1.jpg")
            dummy_file2 = os.path.join(project_root, "dummy_view2.png")

            with open(dummy_file1, "wb") as f:
                f.write(b"dummy jpeg content bytes")
            with open(dummy_file2, "wb") as f:
                f.write(b"dummy png content bytes")

            try:
                # Open files inside a with block so they are automatically closed
                with open(dummy_file1, "rb") as f1, open(dummy_file2, "rb") as f2:
                    files_payload = [
                        ("files", ("dummy_view1.jpg", f1, "image/jpeg")),
                        ("files", ("dummy_view2.png", f2, "image/png")),
                    ]
                    res2 = await client.post(f"/api/upload/{test_patient_id}", files=files_payload)

                print(f"Status Code: {res2.status_code}")
                print(f"Response Body: {res2.json()}")
                assert res2.status_code == 202, "Error: Expected 202 Accepted status code!"

                # Verify folder and files on disk
                print(f"\n--- Checking file uploads under {upload_dir} ---")
                assert os.path.exists(upload_dir), "Error: Patient upload directory not created!"
                files_on_disk = os.listdir(upload_dir)
                print(f"[+] Files saved on disk: {files_on_disk}")
                assert len(files_on_disk) == 2, "Error: Expected 2 files saved on disk!"

                print("\n[+] ALL API ENDPOINT INTEGRATION TESTS COMPLETED SUCCESSFULLY!")

            finally:
                # Clean up dummy image files
                if os.path.exists(dummy_file1):
                    try:
                        os.remove(dummy_file1)
                    except Exception:
                        pass
                if os.path.exists(dummy_file2):
                    try:
                        os.remove(dummy_file2)
                    except Exception:
                        pass

    except Exception as e:
        print(f"\n[-] REST Endpoint Integration Test FAILED: {e}")
        sys.exit(1)

    finally:
        # 5. Shut down server and cleanup files/DB
        print("\n--- Terminating FastAPI Server Process & Cleaning Database ---")
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
