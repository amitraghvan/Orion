#pragma once

#include <vector>
#include <string>
#include <cstdint>

namespace orion {

struct TrackedBBox {
    uint32_t track_id{0};
    int class_id{0};
    std::string class_name;
    float confidence{0.0f};
    float x1{0.0f};
    float y1{0.0f};
    float x2{0.0f};
    float y2{0.0f};
    float vx{0.0f};
    float vy{0.0f};
    int age{0};
    int hits{0};
    int time_since_update{0};
};

class ObjectTracker {
public:
    explicit ObjectTracker(float iou_threshold = 0.3f, int max_age = 30, int min_hits = 3);
    ~ObjectTracker() = default;

    std::vector<TrackedBBox> update(const std::vector<TrackedBBox>& detections);
    void reset();

private:
    float iou_threshold_{0.3f};
    int max_age_{30};
    int min_hits_{3};
    uint32_t next_track_id_{1};
    std::vector<TrackedBBox> tracks_;

    static float compute_iou(const TrackedBBox& a, const TrackedBBox& b);
};

} // namespace orion
