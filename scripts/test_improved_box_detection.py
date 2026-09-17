"""Test improved chromatic and object detection with face masking, strict HSV, and NMS."""

import cv2
import numpy as np


def filter_boxes(frame: np.ndarray, person_boxes: list = None):
    h_f, w_f = frame.shape[:2]
    scale_box = 640.0 / max(h_f, w_f)
    small_f = cv2.resize(frame, (int(w_f * scale_box), int(h_f * scale_box)))
    hsv = cv2.cvtColor(small_f, cv2.COLOR_BGR2HSV)

    mask_ignore = np.zeros(small_f.shape[:2], dtype=np.uint8)
    if person_boxes:
        for pb in person_boxes:
            px_min = int(pb[0] * scale_box)
            py_min = int(pb[1] * scale_box)
            px_max = int(pb[2] * scale_box)
            py_max = int((pb[1] + (pb[3] - pb[1]) * 0.45) * scale_box)
            cv2.rectangle(mask_ignore, (px_min, py_min), (px_max, py_max), 255, -1)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))

    # Yellow mask
    y_mask = cv2.inRange(hsv, (18, 120, 90), (34, 255, 255))
    y_mask = cv2.bitwise_and(y_mask, y_mask, mask=cv2.bitwise_not(mask_ignore))
    y_mask = cv2.morphologyEx(y_mask, cv2.MORPH_OPEN, kernel)
    y_mask = cv2.morphologyEx(y_mask, cv2.MORPH_CLOSE, kernel)

    # Red mask
    r_mask1 = cv2.inRange(hsv, (0, 125, 90), (8, 255, 255))
    r_mask2 = cv2.inRange(hsv, (172, 125, 90), (180, 255, 255))
    r_mask = cv2.bitwise_or(r_mask1, r_mask2)
    r_mask = cv2.bitwise_and(r_mask, r_mask, mask=cv2.bitwise_not(mask_ignore))
    r_mask = cv2.morphologyEx(r_mask, cv2.MORPH_OPEN, kernel)
    r_mask = cv2.morphologyEx(r_mask, cv2.MORPH_CLOSE, kernel)

    candidates = []

    for mask, cls_name, cls_id in [(y_mask, "yellow_box", 101), (r_mask, "red_box", 102)]:
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cnts:
            area = cv2.contourArea(c)
            if 1000 <= area <= (small_f.shape[0] * small_f.shape[1] * 0.25):
                bx, by, bw, bh = cv2.boundingRect(c)
                aspect = bw / float(bh)
                fill_ratio = area / float(bw * bh)
                if 0.45 <= aspect <= 2.2 and fill_ratio >= 0.55:
                    candidates.append(
                        {
                            "class_name": cls_name,
                            "class_id": cls_id,
                            "area": area,
                            "box": [
                                bx / scale_box,
                                by / scale_box,
                                (bx + bw) / scale_box,
                                (by + bh) / scale_box,
                            ],
                            "confidence": min(0.95, max(0.70, fill_ratio)),
                        }
                    )

    candidates.sort(key=lambda x: x["area"], reverse=True)
    kept = []
    for cand in candidates:
        b1 = cand["box"]
        overlap = False
        for k in kept:
            b2 = k["box"]
            xi1 = max(b1[0], b2[0])
            yi1 = max(b1[1], b2[1])
            xi2 = min(b1[2], b2[2])
            yi2 = min(b1[3], b2[3])
            inter = max(0, xi2 - xi1) * max(0, yi2 - yi1)
            area1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
            area2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
            iou = inter / (area1 + area2 - inter + 1e-6)
            if iou > 0.3:
                overlap = True
                break
        if not overlap:
            kept.append(cand)
            if len(kept) >= 4:
                break
    return kept


if __name__ == "__main__":
    cap = cv2.VideoCapture("/Users/amitkumar/Downloads/BAS_REAL_DATA/VALID/SP04/AP01.mp4")
    ret, frame = cap.read()
    cap.release()
    if ret:
        boxes = filter_boxes(frame)
        print("Replay frame boxes detected:", len(boxes))
        for b in boxes:
            print(
                " -",
                b["class_name"],
                "conf:",
                b["confidence"],
                "box:",
                [round(x, 1) for x in b["box"]],
            )
