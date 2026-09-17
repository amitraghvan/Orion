#pragma once

#include "orion/core/frame_buffer.hpp"
#include <string>
#include <memory>
#include <atomic>
#include <thread>

namespace orion {

class VideoRecorder {
public:
    VideoRecorder();
    ~VideoRecorder();

    bool start_recording(const std::string& output_path, int width, int height, double fps = 30.0);
    void write_frame(const FrameData& frame);
    void stop_recording();

    bool is_recording() const;
    uint64_t get_recorded_frames() const;
    std::string get_output_path() const;

private:
    std::string output_path_;
    int width_{0};
    int height_{0};
    double fps_{30.0};
    std::atomic<bool> is_recording_{false};
    std::atomic<uint64_t> recorded_frames_{0};

    struct Impl;
    std::unique_ptr<Impl> pimpl_;
};

} // namespace orion
