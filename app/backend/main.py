from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os
import shutil
import uuid
import httpx
import SimpleITK as sitk
import pydicom
import io
from app.backend.core.logic.dosimetry import DosimetryEngine
from app.backend.core.logic.orthanc_client import OrthancClient
from app.backend.core.logic.dicom_utils import create_rt_dose

app = FastAPI(title="Taranis Dosimetry API")
orthanc = OrthancClient()

# Temporary storage for manual processing
UPLOAD_DIR = "/tmp/dosimetry_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class DosimetryParams(BaseModel):
    activity_mbq: float
    lung_shunt_percent: float
    conversion_factor: float = 49.67
    liver_density: float = 1.05
    lung_mass: float = 1000.0
    liver_label: int = 1

@app.get("/")
async def root():
    return {"message": "Taranis Dosimetry API is running"}

@app.post("/calculate")
async def calculate_dosimetry(
    activity_mbq: float = Form(...),
    lung_shunt_percent: float = Form(...),
    liver_label: int = Form(1),
    spect_file: UploadFile = File(...),
    mask_file: UploadFile = File(...)
):
    """Manual upload calculation endpoint."""
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(UPLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    spect_path = os.path.join(job_dir, "spect.nrrd")
    mask_path = os.path.join(job_dir, "mask.nrrd")
    
    with open(spect_path, "wb") as buffer:
        shutil.copyfileobj(spect_file.file, buffer)
    with open(mask_path, "wb") as buffer:
        shutil.copyfileobj(mask_file.file, buffer)
        
    try:
        spect_img = sitk.ReadImage(spect_path)
        mask_img = sitk.ReadImage(mask_path)
        engine = DosimetryEngine()
        results = engine.calculate_dose(spect_img, mask_img, liver_label, activity_mbq, lung_shunt_percent)
        
        output_path = os.path.join(job_dir, "dose_map.nrrd")
        sitk.WriteImage(results["dose_image"], output_path)
        
        return {
            "status": "success",
            "job_id": job_id,
            "mean_liver_dose_gy": results["mean_liver_dose_gy"],
            "lung_dose_gy": results["lung_dose_gy"],
            "liver_volume_ml": results["liver_volume_ml"]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/process-study")
async def process_study(
    study_uid: str = Form(...),
    spect_series_uid: str = Form(...),
    mask_series_uid: str = Form(...),
    activity_mbq: float = Form(...),
    lung_shunt_percent: float = Form(...)
):
    """Automated Orthanc integration endpoint."""
    try:
        async with httpx.AsyncClient() as client:
            # Lookup SPECT
            resp = await client.post(f"{orthanc.base_url}/tools/lookup", content=spect_series_uid)
            spect_orthanc_id = resp.json()[0]["ID"]
            
            # Lookup Mask
            resp = await client.post(f"{orthanc.base_url}/tools/lookup", content=mask_series_uid)
            mask_orthanc_id = resp.json()[0]["ID"]
            
            # Download NRRDs
            spect_nrrd = await orthanc.get_nrrd(spect_orthanc_id)
            mask_nrrd = await orthanc.get_nrrd(mask_orthanc_id)
            
            # Reference DICOM for tags
            ref_dicom_bytes, _ = await orthanc.fetch_series_instances(spect_series_uid)
            ref_ds = pydicom.dcmread(io.BytesIO(ref_dicom_bytes))

        spect_path = f"/tmp/{spect_series_uid}.nrrd"
        mask_path = f"/tmp/{mask_series_uid}.nrrd"
        with open(spect_path, "wb") as f: f.write(spect_nrrd)
        with open(mask_path, "wb") as f: f.write(mask_nrrd)
        
        spect_img = sitk.ReadImage(spect_path)
        mask_img = sitk.ReadImage(mask_path)

        engine = DosimetryEngine()
        results = engine.calculate_dose(spect_img, mask_img, 1, activity_mbq, lung_shunt_percent)

        rt_dose_ds = create_rt_dose(results["dose_image"], ref_ds)
        
        buffer = io.BytesIO()
        rt_dose_ds.save_as(buffer)
        await orthanc.upload_instance(buffer.getvalue())

        return {
            "status": "success",
            "message": "Dose map generated and pushed to Orthanc",
            "mean_liver_dose_gy": results["mean_liver_dose_gy"]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
