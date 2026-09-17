#pragma once

#include <vector>
#include <mutex>
#include <condition_variable>
#include <cstdint>
#include <memory>
#include <chrono>

namespace orion {

struct FrameData {
    uint64_t frame_id{0};
    int64_t timestamp_ns{0};
    int width{0};
    int height{0};
    int channels{3};
    std::vector<uint8_t> data;

    FrameData() = default;
    FrameData(uint64_t id, int64_t ts, int w, int h, int c, const uint8_t* raw_data)
        : frame_id(id), timestamp_ns(ts), width(w), height(h), channels(c) {
        if (raw_data && w > 0 && h > 0 && c > 0) {
            data.assign(raw_data, raw_data + (w * h * c));
        }
    }
};

class FrameBuffer {
public:
    explicit FrameBuffer(size_t max_capacity = 5)
        : max_capacity_(max_capacity > 0 ? max_capacity : 5),
          dropped_frames_(0) {}

    void push(FrameData&& frame) {
        std::unique_lock<std::mutex> lock(mutex_);
        if (queue_.size() >= max_capacity_) {
            // Drop oldest frame to ensure real-time latency
            queue_.erase(queue_.begin());
            ++dropped_frames_;
        }
        queue_.push_back(std::move(frame));
        cv_.notify_one();
    }

    bool pop(FrameData& out_frame, int timeout_ms = 100) {
        std::unique_lock<std::mutex> lock(mutex_);
        if (queue_.empty()) {
            if (timeout_ms <= 0) {
                return false;
            }
            if (!cv_.wait_for(lock, std::chrono::milliseconds(timeout_ms), [this] { return !queue_.empty(); })) {
                return false;
            }
        }
        out_frame = std::move(queue_.front());
        queue_.erase(queue_.begin());
        return true;
    }

    void clear() {
        std::unique_lock<std::mutex> lock(mutex_);
        queue_.clear();
    }

    size_t size() const {
        std::unique_lock<std::mutex> lock(mutex_);
        return queue_.size();
    }

    uint64_t dropped_frames() const {
        std::unique_lock<std::mutex> lock(mutex_);
        return dropped_frames_;
    }

private:
    const size_t max_capacity_;
    mutable std::mutex mutex_;
    std::condition_variable cv_;
    std::vector<FrameData> queue_;
    uint64_t dropped_frames_{0};
};

} // namespace orion
