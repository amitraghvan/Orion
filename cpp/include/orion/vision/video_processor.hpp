#pragma once

#include "orion/core/frame_buffer.hpp"
#include <vector>
#include <cstdint>

namespace orion {

struct LetterboxResult {
    FrameData processed_frame;
    float scale{1.0f};
    int pad_w{0};
    int pad_h{0};
};

class VideoProcessor {
public:
    VideoProcessor() = default;

    // Fast in-place or copied BGR to RGB conversion
    static void bgr_to_rgb(const uint8_t* src, uint8_t* dst, int width, int height);

    // Letterbox resizing preserving aspect ratio with constant padding
    static LetterboxResult letterbox(
        const FrameData& input,
        int target_w = 640,
        int target_h = 640,
        uint8_t pad_value = 114
    );

    // Fast bilinear resizing
    static FrameData resize(
        const FrameData& input,
        int new_w,
        int new_h
    );

    // Normalize image to float32 [0.0, 1.0] and convert to CHW format for deep learning inference
    static std::vector<float> to_chw_tensor(
        const FrameData& input,
        bool normalize = true
    );
};

} // namespace orion
