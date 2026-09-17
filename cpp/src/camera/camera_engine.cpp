#include "orion/camera/camera_engine.hpp"
#include <chrono>
#include <iostream>
#include <cmath>

#ifdef USE_OPENCV
#include <opencv2/opencv.hpp>
#endif

namespace orion {

struct CameraEngine::Impl {
#ifdef USE_OPENCV
    cv::VideoCapture cap;
#endif
};

CameraEngine::CameraEngine()
    : buffer_(std::make_shared<FrameBuffer>(5)),
      pimpl_(std::make_unique<Impl>()) {}

CameraEngine::~CameraEngine() {
    stop();
    close();
}

bool CameraEngine::open(const std::string& source, int width, int height, int fps) {
    close();

    source_ = source;
    target_width_ = width > 0 ? width : 1280;
    target_height_ = height > 0 ? height : 720;
    target_fps_ = fps > 0 ? fps : 30;

#ifdef USE_OPENCV
    bool opened = false;
    // Check if source is a device index integer
    char* endptr = nullptr;
    long dev_idx = strtol(source.c_str(), &endptr, 10);
    if (*endptr == '\0' && dev_idx >= 0) {
        opened = pimpl_->cap.open(static_cast<int>(dev_idx));
    } else {
        opened = pimpl_->cap.open(source);
    }

    if (opened) {
        pimpl_->cap.set(cv::CAP_PROP_FRAME_WIDTH, target_width_);
        pimpl_->cap.set(cv::CAP_PROP_FRAME_HEIGHT, target_height_);
        pimpl_->cap.set(cv::CAP_PROP_FPS, target_fps_);
        is_open_ = true;
        return true;
    }
#endif

    is_open_ = false;
    return false;
}

void CameraEngine::close() {
    stop();
#ifdef USE_OPENCV
    if (pimpl_->cap.isOpened()) {
        pimpl_->cap.release();
    }
#endif
    is_open_ = false;
}

bool CameraEngine::is_open() const {
    return is_open_.load();
}

bool CameraEngine::is_running() const {
    return is_running_.load();
}

bool CameraEngine::start() {
    if (!is_open_) {
        return false;
    }
    if (is_running_) {
        return true;
    }

    is_running_ = true;
    worker_thread_ = std::thread(&CameraEngine::capture_loop, this);
    return true;
}

void CameraEngine::stop() {
    if (is_running_) {
        is_running_ = false;
        if (worker_thread_.joinable()) {
            worker_thread_.join();
        }
    }
}

bool CameraEngine::read_frame(FrameData& out_frame, int timeout_ms) {
    if (!buffer_) return false;
    return buffer_->pop(out_frame, timeout_ms);
}

double CameraEngine::get_fps() const {
    return current_fps_.load();
}

uint64_t CameraEngine::get_frame_count() const {
    return frame_counter_.load();
}

uint64_t CameraEngine::get_dropped_frames() const {
    if (!buffer_) return 0;
    return buffer_->dropped_frames();
}

int CameraEngine::get_width() const {
    return target_width_;
}

int CameraEngine::get_height() const {
    return target_height_;
}

std::string CameraEngine::get_source() const {
    return source_;
}

void CameraEngine::capture_loop() {
    const auto frame_interval = std::chrono::nanoseconds(1000000000 / (target_fps_ > 0 ? target_fps_ : 30));
    auto last_fps_time = std::chrono::steady_clock::now();
    uint64_t fps_frame_count = 0;

    while (is_running_) {
        auto start_time = std::chrono::steady_clock::now();
        const auto now_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::system_clock::now().time_since_epoch()
        ).count();

        FrameData frame;
        frame.frame_id = ++frame_counter_;
        frame.timestamp_ns = now_ns;
        frame.width = target_width_;
        frame.height = target_height_;
        frame.channels = 3;

#ifdef USE_OPENCV
        if (pimpl_->cap.isOpened()) {
            cv::Mat cv_frame;
            if (pimpl_->cap.read(cv_frame) && !cv_frame.empty()) {
                frame.width = cv_frame.cols;
                frame.height = cv_frame.rows;
                frame.channels = cv_frame.channels();
                frame.data.assign(cv_frame.data, cv_frame.data + (cv_frame.total() * cv_frame.elemSize()));
                buffer_->push(std::move(frame));
            } else {
                // Loop or handle disconnect
                pimpl_->cap.set(cv::CAP_PROP_POS_FRAMES, 0);
            }
        } else {
#endif
            // Pure C++ synthesized test frame for camera disconnected / test mode
            frame.data.resize(static_cast<size_t>(frame.width) * frame.height * 3, 16);
            buffer_->push(std::move(frame));
#ifdef USE_OPENCV
        }
#endif

        // Track FPS
        ++fps_frame_count;
        auto now = std::chrono::steady_clock::now();
        auto elapsed_fps = std::chrono::duration_cast<std::chrono::milliseconds>(now - last_fps_time).count();
        if (elapsed_fps >= 1000) {
            current_fps_ = (fps_frame_count * 1000.0) / elapsed_fps;
            fps_frame_count = 0;
            last_fps_time = now;
        }

        // Sleep to maintain nominal FPS rate
        auto work_time = std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now() - start_time);
        if (work_time < frame_interval) {
            std::this_thread::sleep_for(frame_interval - work_time);
        }
    }
}

} // namespace orion
