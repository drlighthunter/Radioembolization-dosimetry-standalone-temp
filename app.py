import streamlit as st
import httpx
import os

st.set_page_config(page_title="Taranis Dosimetry API", page_icon="☢️", layout="wide")

st.title("Integrated Radioembolisation Dosimetry")
st.write("Upload a SPECT NRRD and a Mask NRRD to calculate absorbed liver and lung doses based on activity and lung shunt fraction.")

col1, col2 = st.columns(2)

with col1:
    spect_file = st.file_uploader("Upload SPECT NRRD", type=["nrrd"], key="spect")
    mask_file = st.file_uploader("Upload Mask NRRD", type=["nrrd"], key="mask")

with col2:
    activity_mbq = st.number_input("Activity (MBq)", min_value=100.0, max_value=10000.0, value=1500.0, step=10.0)
    lung_shunt_percent = st.number_input("Lung Shunt Fraction (%)", min_value=0.0, max_value=100.0, value=5.0, step=0.1)
    liver_label = st.number_input("Liver Label ID in Mask", min_value=1, value=1, step=1)

if st.button("Calculate Dosimetry", type="primary"):
    if not spect_file or not mask_file:
        st.error("Please upload both SPECT and Mask NRRD files.")
    else:
        with st.spinner("Processing Dosimetry Map..."):
            try:
                # We can call the backend logic directly without HTTP since we are in the same container now.
                import SimpleITK as sitk
                import tempfile
                import shutil
                from app.backend.core.logic.dosimetry import DosimetryEngine
                
                with tempfile.TemporaryDirectory() as tmpdir:
                    spect_path = os.path.join(tmpdir, "spect.nrrd")
                    mask_path = os.path.join(tmpdir, "mask.nrrd")
                    
                    with open(spect_path, "wb") as f:
                        shutil.copyfileobj(spect_file, f)
                    with open(mask_path, "wb") as f:
                        shutil.copyfileobj(mask_file, f)
                    
                    spect_img = sitk.ReadImage(spect_path)
                    mask_img = sitk.ReadImage(mask_path)
                    
                    engine = DosimetryEngine()
                    results = engine.calculate_dose(spect_img, mask_img, liver_label, activity_mbq, lung_shunt_percent)
                    
                    st.success("Dosimetry Calculated Successfully!")
                    
                    col_res1, col_res2, col_res3 = st.columns(3)
                    col_res1.metric("Mean Liver Dose (Gy)", f"{results['mean_liver_dose_gy']:.2f}")
                    col_res2.metric("Lung Dose (Gy)", f"{results['lung_dose_gy']:.2f}")
                    col_res3.metric("Liver Volume (mL)", f"{results['liver_volume_ml']:.1f}")
                    
                    st.info("The 3D dose map NRRD file is ready for download or Orthanc export (feature in development).")
            except Exception as e:
                st.error(f"Error calculating dosimetry: {str(e)}")
