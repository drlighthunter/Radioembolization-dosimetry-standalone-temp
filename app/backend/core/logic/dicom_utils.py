import pydicom
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid
import datetime
import numpy as np
import SimpleITK as sitk
import os

def create_rt_dose(dose_image: sitk.Image, reference_dataset: pydicom.dataset.Dataset) -> pydicom.dataset.Dataset:
    """
    Creates a DICOM RT Dose object from a SimpleITK image, using a reference DICOM dataset
    for patient/study metadata.
    """
    # 1. Basic Metadata
    file_meta = Dataset()
    file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.481.2' # RT Dose Storage
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.ImplementationClassUID = "1.2.826.0.1.3680043.8.498.1"
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = Dataset()
    ds.file_meta = file_meta
    ds.is_little_endian = True
    ds.is_implicit_VR = False

    # 2. Patient/Study/Series Tags from Reference
    ds.PatientName = reference_dataset.PatientName
    ds.PatientID = reference_dataset.PatientID
    ds.PatientBirthDate = reference_dataset.PatientBirthDate
    ds.PatientSex = reference_dataset.PatientSex
    
    ds.StudyInstanceUID = reference_dataset.StudyInstanceUID
    ds.SeriesInstanceUID = generate_uid()
    ds.StudyID = reference_dataset.StudyID
    ds.SeriesNumber = "1001" # Calculated Dose Series
    ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.481.2'
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    
    now = datetime.datetime.now()
    ds.ContentDate = now.strftime('%Y%m%d')
    ds.ContentTime = now.strftime('%H%M%S.%f')
    ds.InstanceCreationDate = ds.ContentDate
    ds.InstanceCreationTime = ds.ContentTime
    
    ds.Modality = 'RTDOSE'
    ds.Manufacturer = 'Taranis Dosimetry'
    ds.SeriesDescription = 'Calculated Dose Map (Gy)'

    # 3. Image Data
    dose_array = sitk.GetArrayFromImage(dose_image)
    
    # SimpleITK is (Z, Y, X), DICOM is also usually (Z, Y, X) for pixel data
    # Scaling to integers (DICOM RT Dose uses scaling factor)
    max_dose = np.max(dose_array)
    if max_dose > 0:
        scaling_factor = max_dose / 65535.0
        pixel_data = (dose_array / scaling_factor).astype(np.uint16)
    else:
        scaling_factor = 1.0
        pixel_data = dose_array.astype(np.uint16)

    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.Rows = dose_image.GetSize()[1]
    ds.Columns = dose_image.GetSize()[0]
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0 # Unsigned integer
    ds.DoseUnits = "GY"
    ds.DoseType = "PHYSICAL"
    ds.DoseSummationType = "PLAN"
    ds.DoseGridScaling = scaling_factor
    
    # 4. Geometry
    origin = dose_image.GetOrigin()
    spacing = dose_image.GetSpacing()
    
    ds.ImagePositionPatient = [origin[0], origin[1], origin[2]]
    ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0] # Assuming standard Axial for simplicity
    ds.PixelSpacing = [spacing[0], spacing[1]]
    
    # Grid Frame Offset Vector (Z offsets)
    z_offsets = [z * spacing[2] for z in range(dose_image.GetSize()[2])]
    ds.GridFrameOffsetVector = z_offsets
    ds.NumberOfFrames = dose_image.GetSize()[2]

    ds.PixelData = pixel_data.tobytes()

    return ds
