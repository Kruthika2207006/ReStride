"""MongoDB integration test script to verify connection and CRUD helper functions."""

import asyncio
import os
import sys

# Add project root to path for correct importing
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.database import (
    insert_patient,
    get_patient,
    init_analysis,
    update_analysis,
    get_analysis,
    patients_collection,
    analysis_collection,
)


async def run_test():
    print("=== Starting MongoDB Connection and CRUD Helpers Test ===")

    test_patient_id = "PAT-DB-TEST-99"
    patient_payload = {
        "patient_id": test_patient_id,
        "full_name": "Test John Doe",
        "age": 45,
        "gender": "Male",
        "weight_kg": 82.5,
        "height_cm": 178.0,
        "activity_level": "K3",
        "amputation_level": "transtibial",
        "clinical_history": {"has_diabetes": True, "has_neuropathy": False},
        "limb_details": {"shape": "conical", "length_cm": 14.5},
    }

    try:
        # 1. Test insert_patient
        print(f"\n1. Inserting dummy patient with ID: {test_patient_id}")
        inserted_id = await insert_patient(patient_payload)
        print(f"[+] Successfully inserted patient ID: {inserted_id}")

        # 2. Test get_patient
        print(f"\n2. Retrieving patient profile with ID: {test_patient_id}")
        patient_doc = await get_patient(test_patient_id)
        assert patient_doc is not None, "Error: Could not retrieve patient document!"
        assert patient_doc["full_name"] == "Test John Doe", "Error: Retreived document has mismatching fields!"
        print(f"[+] Retrieved Patient Doc: {patient_doc}")

        # 3. Test init_analysis
        print(f"\n3. Initializing analysis for patient: {test_patient_id}")
        init_ok = await init_analysis(test_patient_id)
        assert init_ok is True, "Error: Failed to initialize analysis!"
        print("[+] Analysis document initialized.")

        # 4. Test update_analysis
        print(f"\n4. Updating analysis fields to processing status...")
        update_ok = await update_analysis(
            test_patient_id,
            {"status": "processing", "progress": 25.0, "geometry": {"limb_length_cm": 14.5}},
        )
        assert update_ok is True, "Error: Failed to update analysis!"
        print("[+] Analysis updated.")

        # 5. Test get_analysis
        print(f"\n5. Retrieving updated analysis document:")
        analysis_doc = await get_analysis(test_patient_id)
        assert analysis_doc is not None, "Error: Could not retrieve analysis document!"
        assert analysis_doc["status"] == "processing", "Error: Mismatching status field!"
        assert analysis_doc["progress"] == 25.0, "Error: Mismatching progress field!"
        print(f"[+] Retrieved Analysis Doc: {analysis_doc}")

        # 6. Test cleanup
        print(f"\n6. Cleaning up test records from collections...")
        p_res = await patients_collection.delete_one({"_id": test_patient_id})
        a_res = await analysis_collection.delete_one({"_id": test_patient_id})
        print(f"[+] Patient delete count: {p_res.deleted_count}")
        print(f"[+] Analysis delete count: {a_res.deleted_count}")
        print("\n[+] ALL MONGODB INTEGRATION TESTS COMPLETED SUCCESSFULLY!")

    except Exception as e:
        print(f"\n[-] Integration Test FAILED: {e}")
        # Try to clean up test documents in case of failure, ignoring secondary errors if DB is offline
        try:
            await patients_collection.delete_one({"_id": test_patient_id})
            await analysis_collection.delete_one({"_id": test_patient_id})
        except Exception:
            pass
        sys.exit(1)



if __name__ == "__main__":
    asyncio.run(run_test())
