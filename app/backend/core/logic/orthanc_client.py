import httpx
import logging
import os

ORTHANC_URL = os.getenv("ORTHANC_URL", "http://orthanc:8042")

class OrthancClient:
    def __init__(self, base_url=ORTHANC_URL):
        self.base_url = base_url

    async def fetch_series_instances(self, series_uid: str):
        """Fetches all instances in a series."""
        async with httpx.AsyncClient() as client:
            # First find the series ID in Orthanc
            resp = await client.post(f"{self.base_url}/tools/lookup", content=series_uid)
            results = resp.json()
            if not results:
                raise ValueError(f"Series {series_uid} not found in Orthanc")
            
            orthanc_series_id = results[0]["ID"]
            
            # Get instance IDs
            resp = await client.get(f"{self.base_url}/series/{orthanc_series_id}")
            instance_ids = resp.json()["Instances"]
            
            # Fetch raw DICOM for the first instance to use as reference
            resp = await client.get(f"{self.base_url}/instances/{instance_ids[0]}/file")
            return resp.content, instance_ids

    async def upload_instance(self, dicom_bytes: bytes):
        """Uploads a DICOM instance to Orthanc."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/instances", content=dicom_bytes)
            return resp.json()

    async def get_nrrd(self, orthanc_series_id: str):
        """Fetches a series as NRRD (Orthanc plugin feature)."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/series/{orthanc_series_id}/nrrd")
            return resp.content
