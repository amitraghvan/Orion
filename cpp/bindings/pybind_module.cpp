#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>

#include "orion/core/frame_buffer.hpp"
#include "orion/camera/camera_engine.hpp"
#include "orion/vision/video_processor.hpp"
#include "orion/tracking/tracker.hpp"
#include "orion/video/video_encoder.hpp"
#include "orion/streaming/stream_engine.hpp"

namespace py = pybind11;

PYBIND11_MODULE(orion_native, m) {
    m.doc() = "ORION Native High-Performance C++20 Vision Engine";

    // -------------------------------------------------------------------------
    // FrameData
    // -------------------------------------------------------------------------
    py::class_<orion::FrameData>(m, "FrameData")
        .def(py::init<>())
        .def_readwrite("frame_id", &orion::FrameData::frame_id)
        .def_readwrite("timestamp_ns", &orion::FrameData::timestamp_ns)
        .def_readwrite("width", &orion::FrameData::width)
        .def_readwrite("height", &orion::FrameData::height)
        .def_readwrite("channels", &orion::FrameData::channels)
        .def("to_numpy", [](const orion::FrameData& self) -> py::object {
            if (self.data.empty() || self.width <= 0 || self.height <= 0 || self.channels <= 0) {
                return py::none();
            }
            std::vector<ssize_t> shape = {self.height, self.width, self.channels};
            std::vector<ssize_t> strides = {
                static_cast<ssize_t>(self.width * self.channels * sizeof(uint8_t)),
                static_cast<ssize_t>(self.channels * sizeof(uint8_t)),
                sizeof(uint8_t)
            };
            return py::array_t<uint8_t>(shape, strides, self.data.data());
        })
        .def("from_numpy", [](orion::FrameData& self, py::array_t<uint8_t, py::array::c_style | py::array::forcecast> array, uint64_t frame_id, int64_t ts) {
            auto buf = array.request();
            if (buf.ndim != 3) {
                throw std::runtime_error("NumPy array must have 3 dimensions (height, width, channels)");
            }
            self.height = static_cast<int>(buf.shape[0]);
            self.width = static_cast<int>(buf.shape[1]);
            self.channels = static_cast<int>(buf.shape[2]);
            self.frame_id = frame_id;
            self.timestamp_ns = ts;
            const uint8_t* ptr = static_cast<const uint8_t*>(buf.ptr);
            self.data.assign(ptr, ptr + buf.size);
        });

    // -------------------------------------------------------------------------
    // CameraEngine
    // -------------------------------------------------------------------------
    py::class_<orion::CameraEngine>(m, "CameraEngine")
        .def(py::init<>())
        .def("open", &orion::CameraEngine::open, py::arg("source"), py::arg("width") = 1280, py::arg("height") = 720, py::arg("fps") = 30)
        .def("close", &orion::CameraEngine::close)
        .def("is_open", &orion::CameraEngine::is_open)
        .def("is_running", &orion::CameraEngine::is_running)
        .def("start", &orion::CameraEngine::start)
        .def("stop", &orion::CameraEngine::stop)
        .def("read_frame", [](orion::CameraEngine& self, int timeout_ms) -> std::optional<orion::FrameData> {
            orion::FrameData frame;
            if (self.read_frame(frame, timeout_ms)) {
                return frame;
            }
            return std::nullopt;
        }, py::arg("timeout_ms") = 100)
        .def("get_fps", &orion::CameraEngine::get_fps)
        .def("get_frame_count", &orion::CameraEngine::get_frame_count)
        .def("get_dropped_frames", &orion::CameraEngine::get_dropped_frames)
        .def("get_width", &orion::CameraEngine::get_width)
        .def("get_height", &orion::CameraEngine::get_height)
        .def("get_source", &orion::CameraEngine::get_source);

    // -------------------------------------------------------------------------
    // VideoProcessor
    // -------------------------------------------------------------------------
    py::class_<orion::LetterboxResult>(m, "LetterboxResult")
        .def_readonly("processed_frame", &orion::LetterboxResult::processed_frame)
        .def_readonly("scale", &orion::LetterboxResult::scale)
        .def_readonly("pad_w", &orion::LetterboxResult::pad_w)
        .def_readonly("pad_h", &orion::LetterboxResult::pad_h);

    py::class_<orion::VideoProcessor>(m, "VideoProcessor")
        .def(py::init<>())
        .def_static("letterbox", &orion::VideoProcessor::letterbox, py::arg("input"), py::arg("target_w") = 640, py::arg("target_h") = 640, py::arg("pad_value") = 114)
        .def_static("resize", &orion::VideoProcessor::resize, py::arg("input"), py::arg("new_w"), py::arg("new_h"))
        .def_static("to_chw_tensor", [](const orion::FrameData& input, bool normalize) -> py::array_t<float> {
            auto tensor = orion::VideoProcessor::to_chw_tensor(input, normalize);
            if (tensor.empty()) return py::array_t<float>();
            std::vector<ssize_t> shape = {input.channels, input.height, input.width};
            return py::array_t<float>(shape, tensor.data());
        }, py::arg("input"), py::arg("normalize") = true);

    // -------------------------------------------------------------------------
    // ObjectTracker
    // -------------------------------------------------------------------------
    py::class_<orion::TrackedBBox>(m, "TrackedBBox")
        .def(py::init<>())
        .def_readwrite("track_id", &orion::TrackedBBox::track_id)
        .def_readwrite("class_id", &orion::TrackedBBox::class_id)
        .def_readwrite("class_name", &orion::TrackedBBox::class_name)
        .def_readwrite("confidence", &orion::TrackedBBox::confidence)
        .def_readwrite("x1", &orion::TrackedBBox::x1)
        .def_readwrite("y1", &orion::TrackedBBox::y1)
        .def_readwrite("x2", &orion::TrackedBBox::x2)
        .def_readwrite("y2", &orion::TrackedBBox::y2)
        .def_readwrite("vx", &orion::TrackedBBox::vx)
        .def_readwrite("vy", &orion::TrackedBBox::vy)
        .def_readwrite("age", &orion::TrackedBBox::age)
        .def_readwrite("hits", &orion::TrackedBBox::hits);

    py::class_<orion::ObjectTracker>(m, "ObjectTracker")
        .def(py::init<float, int, int>(), py::arg("iou_threshold") = 0.3f, py::arg("max_age") = 30, py::arg("min_hits") = 3)
        .def("update", &orion::ObjectTracker::update, py::arg("detections"))
        .def("reset", &orion::ObjectTracker::reset);

    // -------------------------------------------------------------------------
    // VideoRecorder
    // -------------------------------------------------------------------------
    py::class_<orion::VideoRecorder>(m, "VideoRecorder")
        .def(py::init<>())
        .def("start_recording", &orion::VideoRecorder::start_recording, py::arg("output_path"), py::arg("width"), py::arg("height"), py::arg("fps") = 30.0)
        .def("write_frame", &orion::VideoRecorder::write_frame, py::arg("frame"))
        .def("stop_recording", &orion::VideoRecorder::stop_recording)
        .def("is_recording", &orion::VideoRecorder::is_recording)
        .def("get_recorded_frames", &orion::VideoRecorder::get_recorded_frames)
        .def("get_output_path", &orion::VideoRecorder::get_output_path);

    // -------------------------------------------------------------------------
    // StreamEngine
    // -------------------------------------------------------------------------
    py::class_<orion::StreamEngine>(m, "StreamEngine")
        .def(py::init<>())
        .def("start", &orion::StreamEngine::start, py::arg("host") = "127.0.0.1", py::arg("port") = 8080)
        .def("stop", &orion::StreamEngine::stop)
        .def("update_frame", &orion::StreamEngine::update_frame, py::arg("frame"), py::arg("quality") = 80)
        .def("is_streaming", &orion::StreamEngine::is_streaming)
        .def("get_url", &orion::StreamEngine::get_url)
        .def("get_client_count", &orion::StreamEngine::get_client_count);
}
