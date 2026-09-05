# Research Template: Computer Vision & Object Detection

## 1. Title & Abstract
- **Title**: [Title of Computer Vision Study]
- **Authors / Research Fellows**: [Names and Affiliations]
- **Date**: [YYYY-MM-DD]
- **Abstract**: [High-level summary of model architecture, target classes, and objectives]

## 2. Problem Formulation
- Detection challenges in orbital microgravity (variable illumination, floating objects, occlusions).
- Target classes and ontology definitions.

## 3. Architecture & Baselines
- Evaluated architectures (e.g. YOLO11, RT-DETR, Co-DETR).
- Input resolution, backbone, neck, and head configurations.

## 4. Evaluation Metrics & Flight Constraints
- Target mAP50 and mAP50-95.
- Latency budget on NVIDIA Jetson AGX Orin (target: <= 20ms per frame).
- FP16 vs INT8 quantization tolerance.
