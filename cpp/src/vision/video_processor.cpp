#include "orion/vision/video_processor.hpp"
#include <algorithm>
#include <cmath>
#include <cstring>

namespace orion {

void VideoProcessor::bgr_to_rgb(const uint8_t* src, uint8_t* dst, int width, int height) {
    if (!src || !dst || width <= 0 || height <= 0) return;
    const size_t total_pixels = static_cast<size_t>(width) * height;
    for (size_t i = 0; i < total_pixels; ++i) {
        const size_t idx = i * 3;
        dst[idx + 0] = src[idx + 2]; // R <- B
        dst[idx + 1] = src[idx + 1]; // G <- G
        dst[idx + 2] = src[idx + 0]; // B <- R
    }
}

LetterboxResult VideoProcessor::letterbox(
    const FrameData& input,
    int target_w,
    int target_h,
    uint8_t pad_value
) {
    LetterboxResult res;
    if (input.data.empty() || input.width <= 0 || input.height <= 0) {
        return res;
    }

    const float r_w = static_cast<float>(target_w) / input.width;
    const float r_h = static_cast<float>(target_h) / input.height;
    const float r = std::min(r_w, r_h);
    res.scale = r;

    const int new_unpad_w = static_cast<int>(std::round(input.width * r));
    const int new_unpad_h = static_cast<int>(std::round(input.height * r));

    const int pad_w = (target_w - new_unpad_w) / 2;
    const int pad_h = (target_h - new_unpad_h) / 2;
    res.pad_w = pad_w;
    res.pad_h = pad_h;

    // Allocate padded target buffer initialized to pad_value (default 114)
    res.processed_frame.frame_id = input.frame_id;
    res.processed_frame.timestamp_ns = input.timestamp_ns;
    res.processed_frame.width = target_w;
    res.processed_frame.height = target_h;
    res.processed_frame.channels = input.channels;
    res.processed_frame.data.assign(static_cast<size_t>(target_w) * target_h * input.channels, pad_value);

    // Bilinear resize into destination centered region
    const float scale_x = static_cast<float>(input.width) / new_unpad_w;
    const float scale_y = static_cast<float>(input.height) / new_unpad_h;

    for (int y = 0; y < new_unpad_h; ++y) {
        const float src_y = (y + 0.5f) * scale_y - 0.5f;
        const int y0 = std::clamp(static_cast<int>(std::floor(src_y)), 0, input.height - 1);
        const int y1 = std::clamp(y0 + 1, 0, input.height - 1);
        const float dy = src_y - y0;

        uint8_t* dst_row = res.processed_frame.data.data() + ((y + pad_h) * target_w + pad_w) * input.channels;

        for (int x = 0; x < new_unpad_w; ++x) {
            const float src_x = (x + 0.5f) * scale_x - 0.5f;
            const int x0 = std::clamp(static_cast<int>(std::floor(src_x)), 0, input.width - 1);
            const int x1 = std::clamp(x0 + 1, 0, input.width - 1);
            const float dx = src_x - x0;

            for (int c = 0; c < input.channels; ++c) {
                const float p00 = input.data[(y0 * input.width + x0) * input.channels + c];
                const float p10 = input.data[(y0 * input.width + x1) * input.channels + c];
                const float p01 = input.data[(y1 * input.width + x0) * input.channels + c];
                const float p11 = input.data[(y1 * input.width + x1) * input.channels + c];

                const float val = (1.0f - dx) * (1.0f - dy) * p00 +
                                  dx * (1.0f - dy) * p10 +
                                  (1.0f - dx) * dy * p01 +
                                  dx * dy * p11;

                dst_row[x * input.channels + c] = static_cast<uint8_t>(std::clamp(std::round(val), 0.0f, 255.0f));
            }
        }
    }

    return res;
}

FrameData VideoProcessor::resize(const FrameData& input, int new_w, int new_h) {
    FrameData out;
    if (input.data.empty() || input.width <= 0 || input.height <= 0 || new_w <= 0 || new_h <= 0) {
        return out;
    }

    out.frame_id = input.frame_id;
    out.timestamp_ns = input.timestamp_ns;
    out.width = new_w;
    out.height = new_h;
    out.channels = input.channels;
    out.data.resize(static_cast<size_t>(new_w) * new_h * input.channels);

    const float scale_x = static_cast<float>(input.width) / new_w;
    const float scale_y = static_cast<float>(input.height) / new_h;

    for (int y = 0; y < new_h; ++y) {
        const float src_y = (y + 0.5f) * scale_y - 0.5f;
        const int y0 = std::clamp(static_cast<int>(std::floor(src_y)), 0, input.height - 1);
        const int y1 = std::clamp(y0 + 1, 0, input.height - 1);
        const float dy = src_y - y0;

        uint8_t* dst_row = out.data.data() + (y * new_w) * input.channels;

        for (int x = 0; x < new_w; ++x) {
            const float src_x = (x + 0.5f) * scale_x - 0.5f;
            const int x0 = std::clamp(static_cast<int>(std::floor(src_x)), 0, input.width - 1);
            const int x1 = std::clamp(x0 + 1, 0, input.width - 1);
            const float dx = src_x - x0;

            for (int c = 0; c < input.channels; ++c) {
                const float p00 = input.data[(y0 * input.width + x0) * input.channels + c];
                const float p10 = input.data[(y0 * input.width + x1) * input.channels + c];
                const float p01 = input.data[(y1 * input.width + x0) * input.channels + c];
                const float p11 = input.data[(y1 * input.width + x1) * input.channels + c];

                const float val = (1.0f - dx) * (1.0f - dy) * p00 +
                                  dx * (1.0f - dy) * p10 +
                                  (1.0f - dx) * dy * p01 +
                                  dx * dy * p11;

                dst_row[x * input.channels + c] = static_cast<uint8_t>(std::clamp(std::round(val), 0.0f, 255.0f));
            }
        }
    }
    return out;
}

std::vector<float> VideoProcessor::to_chw_tensor(const FrameData& input, bool normalize) {
    if (input.data.empty() || input.width <= 0 || input.height <= 0 || input.channels <= 0) {
        return {};
    }

    const size_t plane_size = static_cast<size_t>(input.width) * input.height;
    std::vector<float> tensor(plane_size * input.channels);
    const float norm_factor = normalize ? (1.0f / 255.0f) : 1.0f;

    for (int c = 0; c < input.channels; ++c) {
        float* plane = tensor.data() + c * plane_size;
        for (size_t i = 0; i < plane_size; ++i) {
            plane[i] = input.data[i * input.channels + c] * norm_factor;
        }
    }
    return tensor;
}

} // namespace orion
