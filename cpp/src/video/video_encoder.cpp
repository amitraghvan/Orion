#include "orion/video/video_encoder.hpp"

#ifdef USE_OPENCV
#include <opencv2/opencv.hpp>
#endif

namespace orion {

struct VideoRecorder::Impl {
#ifdef USE_OPENCV
    cv::VideoWriter writer;
#endif
};

VideoRecorder::VideoRecorder()
    : pimpl_(std::make_unique<Impl>()) {}

VideoRecorder::~VideoRecorder() {
    stop_recording();
}

bool VideoRecorder::start_recording(const std::string& output_path, int width, int height, double fps) {
    stop_recording();

    output_path_ = output_path;
    width_ = width;
    height_ = height;
    fps_ = fps > 0.0 ? fps : 30.0;
    recorded_frames_ = 0;

#ifdef USE_OPENCV
    int fourcc = cv::VideoWriter::fourcc('m', 'p', '4', 'v');
    bool opened = pimpl_->writer.open(output_path_, fourcc, fps_, cv::Size(width_, height_), true);
    if (opened) {
        is_recording_ = true;
        return true;
    }
#endif

    is_recording_ = true;
    return true;
}

void VideoRecorder::write_frame(const FrameData& frame) {
    if (!is_recording_) return;

#ifdef USE_OPENCV
    if (pimpl_->writer.isOpened() && !frame.data.empty()) {
        cv::Mat mat(frame.height, frame.width, CV_8UC3, const_cast<uint8_t*>(frame.data.data()));
        pimpl_->writer.write(mat);
    }
#endif
    ++recorded_frames_;
}

void VideoRecorder::stop_recording() {
    if (is_recording_) {
#ifdef USE_OPENCV
        if (pimpl_->writer.isOpened()) {
            pimpl_->writer.release();
        }
#endif
        is_recording_ = false;
    }
}

bool VideoRecorder::is_recording() const {
    return is_recording_.load();
}

uint64_t VideoRecorder::get_recorded_frames() const {
    return recorded_frames_.load();
}

std::string VideoRecorder::get_output_path() const {
    return output_path_;
}

} // namespace orion
