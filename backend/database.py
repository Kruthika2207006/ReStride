"""Database module containing MongoDB connection initialization and helper functions."""

import logging
from typing import Optional
from pymongo.errors import PyMongoError
from motor.motor_asyncio import AsyncIOMotorClient
from backend.config import MONGO_URI, DB_NAME

# Setup logger for database operations
logger = logging.getLogger("backend.database")

# Initialize asynchronous motor client
client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]

# Expose patients and analyses collections
patients_collection = db["patients"]
analysis_collection = db["analyses"]


async def insert_patient(patient_data: dict) -> str:
    """Inserts a new patient record into the database, or upserts it if already present.

    Args:
        patient_data: Dictionary conforming to the PatientCreate schema.

    Returns:
        The patient_id string.

    Raises:
        ValueError: If patient_id is not specified in the input.
        PyMongoError: If any underlying MongoDB operations fail.
    """
    patient_id = patient_data.get("patient_id")
    if not patient_id:
        logger.error("ValueError: insert_patient called without patient_id in patient_data.")
        raise ValueError("patient_id is required in patient_data")

    try:
        # Use patient_id as the primary key document identifier (_id)
        doc = dict(patient_data)
        doc["_id"] = patient_id
        await patients_collection.replace_one({"_id": patient_id}, doc, upsert=True)
        logger.info(f"Successfully inserted/updated patient profile: {patient_id}")
        return patient_id
    except PyMongoError as e:
        logger.exception(f"MongoDB error in insert_patient for ID {patient_id}: {e}")
        raise PyMongoError(f"Database write operation failed for patient {patient_id}: {str(e)}") from e


async def get_patient(patient_id: str) -> Optional[dict]:
    """Retrieves a patient profile document by patient_id.

    Args:
        patient_id: The unique patient identifier string.

    Returns:
        The patient document dictionary if found, otherwise None.
    """
    try:
        doc = await patients_collection.find_one({"_id": patient_id})
        if doc:
            logger.info(f"Retrieved patient profile: {patient_id}")
        else:
            logger.warning(f"Patient profile not found: {patient_id}")
        return doc
    except PyMongoError as e:
        logger.exception(f"MongoDB error in get_patient for ID {patient_id}: {e}")
        return None


async def init_analysis(patient_id: str) -> bool:
    """Initializes a new analysis tracking document with status = "pending" and progress = 0.

    All other execution fields are set to None.

    Args:
        patient_id: The unique patient identifier string.

    Returns:
        True if successfully initialized, False if a database error occurred.
    """
    try:
        doc = {
            "_id": patient_id,
            "patient_id": patient_id,
            "status": "pending",
            "progress": 0.0,
            "error": None,
            "geometry": None,
            "clinical": None,
            "socket": None,
            "safety": None,
            "final_response": None,
        }
        await analysis_collection.replace_one({"_id": patient_id}, doc, upsert=True)
        logger.info(f"Successfully initialized analysis record for patient: {patient_id}")
        return True
    except PyMongoError as e:
        logger.exception(f"MongoDB error in init_analysis for patient {patient_id}: {e}")
        return False


async def update_analysis(patient_id: str, update_fields: dict) -> bool:
    """Updates selected execution fields of an existing analysis tracking document.

    Args:
        patient_id: The unique patient identifier string.
        update_fields: Dictionary containing keys and updated values to set.

    Returns:
        True if the document was successfully matched and updated, False otherwise.
    """
    try:
        result = await analysis_collection.update_one(
            {"_id": patient_id},
            {"$set": update_fields}
        )
        if result.modified_count > 0 or result.matched_count > 0:
            logger.info(f"Successfully updated analysis fields for patient: {patient_id}")
            return True
        else:
            logger.warning(f"No analysis record matched/modified for patient: {patient_id}")
            return False
    except PyMongoError as e:
        logger.exception(f"MongoDB error in update_analysis for patient {patient_id}: {e}")
        return False


async def get_analysis(patient_id: str) -> Optional[dict]:
    """Retrieves the full analysis record document for the patient.

    Args:
        patient_id: The unique patient identifier string.

    Returns:
        The analysis document dictionary if found, otherwise None.
    """
    try:
        doc = await analysis_collection.find_one({"_id": patient_id})
        if doc:
            logger.info(f"Retrieved analysis record: {patient_id}")
        else:
            logger.warning(f"Analysis record not found: {patient_id}")
        return doc
    except PyMongoError as e:
        logger.exception(f"MongoDB error in get_analysis for patient {patient_id}: {e}")
        return None
