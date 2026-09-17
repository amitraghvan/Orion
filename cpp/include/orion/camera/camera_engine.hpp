#pragma once

#include "orion/core/frame_buffer.hpp"
#include <string>
#include <memory>
#include <thread>
#include <atomic>
#include <functional>

namespace orion {

class CameraEngine {
public:
    CameraEngine();
    ~CameraEngine();

    bool open(const std::string& source, int width = 1280, int height = 720, int fps = 30);
    void close();

    bool is_open() const;
    bool is_running() const;

    bool start();
    void stop();

    bool read_frame(FrameData& out_frame, int timeout_ms = 100);

    double get_fps() const;
    uint64_t get_frame_count() const;
    uint64_t get_dropped_frames() const;
    int get_width() const;
    int get_height() const;
    std::string get_source() const;

private:
    void capture_loop();

    std::string source_;
    int target_width_{1280};
    int target_height_{720};
    int target_fps_{30};

    std::atomic<bool> is_open_{false};
    std::atomic<bool> is_running_{false};
    std::thread worker_thread_;

    std::shared_ptr<FrameBuffer> buffer_;
    std::atomic<uint64_t> frame_counter_{0};
    std::atomic<double> current_fps_{0.0};

    struct Impl;
    std::unique_ptr<Impl> pimpl_;
};

} // namespace orion
