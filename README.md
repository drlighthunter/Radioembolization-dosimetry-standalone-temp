# Radioembolization Dosimetry - Standalone Edition

A standalone, integrated version of the Taranis Radioembolization Dosimetry system. This repository contains the backend logic for voxel-based dosimetry, integration with Orthanc (DICOM Server), and configuration for the OHIF Viewer.

## 🚀 Overview

The system consists of:
1. **FastAPI Backend**: Handles dosimetry calculations using SimpleITK and pydicom.
2. **Orthanc Integration**: Automatically fetches studies and pushes dose maps back as RTDOSE objects.
3. **OHIF Viewer Config**: Custom configuration for the medical imaging frontend.

## 🛠️ Stack

- **Backend**: Python 3.9+, FastAPI, SimpleITK, pydicom
- **Imaging**: Orthanc (DICOM Server)
- **Frontend**: OHIF Viewer

## 📦 Local Setup (Without Docker)

### 1. Backend
```bash
cd app/backend
pip install -r requirements.txt
python main.py
```

### 2. Dependencies
This application expects an **Orthanc** server running at `localhost:8042`.

## 🐳 Containerized Deployment
You can still use the provided `docker-compose.yml` for a full stack deployment:
```bash
docker-compose up --build
```

---
Developed by [Dr. Sunil Kalmath](https://github.com/drlighthunter)
