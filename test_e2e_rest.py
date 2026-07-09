"""End-to-end integration test to verify FastAPI endpoint pipeline execution and MongoDB storage."""

import os
import sys
import asyncio
import httpx
import shutil

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


async def run_e2e_test():
    print("=== Starting E2E REST API and Background Task Verification ===")
    
    test_patient_id = "PAT-E2E-TEST-100"
    upload_dir = os.path.join(project_root, "uploads", test_patient_id)
    
    # 1. Clean up prior data
    await cleanup_db(test_patient_id)
    if os.path.exists(upload_dir):
        shutil.rmtree(upload_dir)
        print(f"[+] Cleaned disk directory: {upload_dir}")

    # Connect to the running backend on port 8080
    base_url = "http://127.0.0.1:8080"
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        # 2. Register Patient
        print("\nStep 1: Registering patient via POST /api/patient...")
        patient_payload = {
            "patient_id": test_patient_id,
            "full_name": "E2E Test Patient",
            "age": 60,
            "gender": "Male",
            "weight_kg": 85.0,
            "height_cm": 180.0,
            "activity_level": "K3",
            "amputation_level": "transtibial",
            "clinical_history": {
                "amputation_reason": "trauma",
                "has_diabetes": False,
                "has_neuropathy": True,
                "volume_fluctuations": False,
            },
            "limb_details": {
                "shape": "conical",
                "length_cm": 16.0,
                "proximal_circumference_cm": 32.0,
                "mid_limb_circumference_cm": 26.0,
                "distal_circumference_cm": 20.0,
                "skin_condition": "healthy",
            }
        }
        res_patient = await client.post("/api/patient", json=patient_payload)
        print(f"Status Code: {res_patient.status_code}")
        print(f"Response: {res_patient.json()}")
        assert res_patient.status_code == 201, "Failed to create patient profile!"

        # 3. Upload images to trigger background task
        print("\nStep 2: Uploading images via POST /api/upload/{patient_id}...")
        dummy_file = os.path.join(project_root, "dummy_test.jpg")
        with open(dummy_file, "wb") as f:
            f.write(b"dummy image content")

        try:
            with open(dummy_file, "rb") as f_in:
                files_payload = [
                    ("files", ("dummy_test.jpg", f_in, "image/jpeg")),
                ]
                res_upload = await client.post(f"/api/upload/{test_patient_id}", files=files_payload)
            
            print(f"Status Code: {res_upload.status_code}")
            print(f"Response: {res_upload.json()}")
            assert res_upload.status_code == 202, "Failed to upload images and trigger analysis!"

        finally:
            if os.path.exists(dummy_file):
                os.remove(dummy_file)

        # 4. Poll GET /api/analysis/{patient_id} until completed
        print("\nStep 3: Polling GET /api/analysis/{patient_id} repeatedly...")
        max_polls = 40
        poll_interval = 2.0
        completed = False
        analysis_data = {}
        tested_202 = False

        for poll in range(1, max_polls + 1):
            await asyncio.sleep(poll_interval)
            res_analysis = await client.get(f"/api/analysis/{test_patient_id}")
            assert res_analysis.status_code == 200, f"Failed GET /api/analysis status code: {res_analysis.status_code}"
            
            analysis_data = res_analysis.json()
            status_val = analysis_data.get("status")
            progress_val = analysis_data.get("progress")
            error_val = analysis_data.get("error")
            
            print(f"Poll #{poll}: status='{status_val}', progress={progress_val}%, error={error_val}")
            
            # Assert _id is removed from the status API response
            assert "_id" not in analysis_data, "Error: MongoDB '_id' was not removed from status response!"

            # Test 202 response on component sub-endpoint during processing
            if status_val == "processing" and progress_val == 40.0 and not tested_202:
                res_202 = await client.get(f"/api/analysis/{test_patient_id}/geometry")
                print(f"GET /api/analysis/{test_patient_id}/geometry during processing -> status={res_202.status_code}")
                assert res_202.status_code == 202, "Error: Expected 202 Accepted status code during processing!"
                res_202_json = res_202.json()
                assert "Analysis not yet complete" in res_202_json.get("detail", ""), "Expected detail warning message!"
                assert res_202_json.get("status") == "processing", "Expected status parameter in 202 response!"
                tested_202 = True
            
            if status_val == "completed":
                completed = True
                break
            elif status_val == "failed":
                print(f"[-] Analysis pipeline failed: {error_val}")
                break

        assert completed, "E2E Test Failed: Analysis pipeline did not reach 'completed' state in time!"
        print("[+] Analysis pipeline finished successfully!")

        # 5. Verify the sub-endpoints return proper formatted data
        print("\nStep 4: Verifying component data endpoints...")
        components = {
            "geometry": "geometry",
            "clinical": "clinical",
            "socket": "socket",
            "safety": "safety",
            "final": "final_response"
        }
        for path_name, response_key in components.items():
            res_comp = await client.get(f"/api/analysis/{test_patient_id}/{path_name}")
            print(f"GET /api/analysis/{test_patient_id}/{path_name} -> status={res_comp.status_code}")
            assert res_comp.status_code == 200, f"Component sub-endpoint {path_name} returned non-200 status!"
            data_wrapper = res_comp.json()
            assert response_key in data_wrapper, f"Expected key '{response_key}' in component response wrapper!"
            data = data_wrapper[response_key]
            print(f"Data for {path_name} (key: {response_key}): {list(data.keys()) if isinstance(data, dict) else type(data)}")
            if path_name != "geometry":
                assert len(data) > 0, f"Component {path_name} data is empty!"

        print("\n[+] ALL END-TO-END REST INTEGRATION TESTS COMPLETED SUCCESSFULLY!")

    # 6. Database and directory cleanup
    await cleanup_db(test_patient_id)
    if os.path.exists(upload_dir):
        shutil.rmtree(upload_dir)


if __name__ == "__main__":
    asyncio.run(run_e2e_test())
