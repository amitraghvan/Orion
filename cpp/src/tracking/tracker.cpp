#include "orion/tracking/tracker.hpp"
#include <algorithm>
#include <cmath>

namespace orion {

ObjectTracker::ObjectTracker(float iou_threshold, int max_age, int min_hits)
    : iou_threshold_(iou_threshold), max_age_(max_age), min_hits_(min_hits) {}

float ObjectTracker::compute_iou(const TrackedBBox& a, const TrackedBBox& b) {
    const float x_left = std::max(a.x1, b.x1);
    const float y_top = std::max(a.y1, b.y1);
    const float x_right = std::min(a.x2, b.x2);
    const float y_bottom = std::min(a.y2, b.y2);

    if (x_right < x_left || y_bottom < y_top) {
        return 0.0f;
    }

    const float intersection_area = (x_right - x_left) * (y_bottom - y_top);
    const float area_a = (a.x2 - a.x1) * (a.y2 - a.y1);
    const float area_b = (b.x2 - b.x1) * (b.y2 - b.y1);
    const float union_area = area_a + area_b - intersection_area;

    if (union_area <= 0.0f) {
        return 0.0f;
    }

    return intersection_area / union_area;
}

std::vector<TrackedBBox> ObjectTracker::update(const std::vector<TrackedBBox>& detections) {
    // 1. Predict track locations based on velocity
    for (auto& track : tracks_) {
        track.x1 += track.vx;
        track.y1 += track.vy;
        track.x2 += track.vx;
        track.y2 += track.vy;
        track.age++;
        track.time_since_update++;
    }

    std::vector<bool> det_matched(detections.size(), false);
    std::vector<bool> trk_matched(tracks_.size(), false);

    // 2. Greedy IoU matching (matches same class only)
    for (size_t t = 0; t < tracks_.size(); ++t) {
        float best_iou = iou_threshold_;
        int best_d = -1;

        for (size_t d = 0; d < detections.size(); ++d) {
            if (det_matched[d]) continue;
            if (tracks_[t].class_id != detections[d].class_id) continue;

            float iou = compute_iou(tracks_[t], detections[d]);
            if (iou > best_iou) {
                best_iou = iou;
                best_d = static_cast<int>(d);
            }
        }

        if (best_d >= 0) {
            trk_matched[t] = true;
            det_matched[best_d] = true;

            // Update velocity
            const float new_cx = (detections[best_d].x1 + detections[best_d].x2) * 0.5f;
            const float new_cy = (detections[best_d].y1 + detections[best_d].y2) * 0.5f;
            const float old_cx = (tracks_[t].x1 + tracks_[t].x2) * 0.5f;
            const float old_cy = (tracks_[t].y1 + tracks_[t].y2) * 0.5f;

            tracks_[t].vx = (new_cx - old_cx) * 0.3f + tracks_[t].vx * 0.7f;
            tracks_[t].vy = (new_cy - old_cy) * 0.3f + tracks_[t].vy * 0.7f;

            tracks_[t].x1 = detections[best_d].x1;
            tracks_[t].y1 = detections[best_d].y1;
            tracks_[t].x2 = detections[best_d].x2;
            tracks_[t].y2 = detections[best_d].y2;
            tracks_[t].confidence = detections[best_d].confidence;
            tracks_[t].hits++;
            tracks_[t].time_since_update = 0;
        }
    }

    // 3. Create new tracks for unmatched detections
    for (size_t d = 0; d < detections.size(); ++d) {
        if (!det_matched[d]) {
            TrackedBBox new_track = detections[d];
            new_track.track_id = next_track_id_++;
            new_track.hits = 1;
            new_track.age = 1;
            new_track.time_since_update = 0;
            new_track.vx = 0.0f;
            new_track.vy = 0.0f;
            tracks_.push_back(new_track);
        }
    }

    // 4. Remove dead tracks exceeding max_age
    tracks_.erase(
        std::remove_if(
            tracks_.begin(),
            tracks_.end(),
            [this](const TrackedBBox& trk) {
                return trk.time_since_update > max_age_;
            }
        ),
        tracks_.end()
    );

    // 5. Return confirmed active tracks (hits >= min_hits or new valid tracks)
    std::vector<TrackedBBox> active_tracks;
    for (const auto& trk : tracks_) {
        if (trk.time_since_update == 0 && (trk.hits >= min_hits_ || trk.age <= 2)) {
            active_tracks.push_back(trk);
        }
    }

    return active_tracks;
}

void ObjectTracker::reset() {
    tracks_.clear();
    next_track_id_ = 1;
}

} // namespace orion
