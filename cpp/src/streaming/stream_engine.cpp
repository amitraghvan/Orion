#include "orion/streaming/stream_engine.hpp"

#ifdef USE_OPENCV
#include <opencv2/opencv.hpp>
#endif

namespace orion {

struct StreamEngine::Impl {
    // Platform socket or HTTP structures
};

StreamEngine::StreamEngine()
    : pimpl_(std::make_unique<Impl>()) {}

StreamEngine::~StreamEngine() {
    stop();
}

bool StreamEngine::start(const std::string& host, int port) {
    stop();
    host_ = host;
    port_ = port;
    is_running_ = true;
    return true;
}

void StreamEngine::stop() {
    is_running_ = false;
    if (server_thread_.joinable()) {
        server_thread_.join();
    }
}

void StreamEngine::update_frame(const FrameData& frame, int quality) {
    if (!is_running_) return;

#ifdef USE_OPENCV
    if (!frame.data.empty()) {
        cv::Mat mat(frame.height, frame.width, CV_8UC3, const_cast<uint8_t*>(frame.data.data()));
        std::vector<uint8_t> encoded;
        std::vector<int> params = {cv::IMWRITE_JPEG_QUALITY, quality};
        if (cv::imencode(".jpg", mat, encoded, params)) {
            std::lock_guard<std::mutex> lock(frame_mutex_);
            latest_jpeg_ = std::move(encoded);
        }
    }
#else
    (void)frame;
    (void)quality;
#endif
}

bool StreamEngine::is_streaming() const {
    return is_running_.load();
}

std::string StreamEngine::get_url() const {
    return "http://" + host_ + ":" + std::to_string(port_) + "/live";
}

int StreamEngine::get_client_count() const {
    return client_count_.load();
}

} // namespace orion
