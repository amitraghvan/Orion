#pragma once

#include "orion/core/frame_buffer.hpp"
#include <string>
#include <memory>
#include <atomic>
#include <thread>
#include <mutex>
#include <vector>

namespace orion {

class StreamEngine {
public:
    StreamEngine();
    ~StreamEngine();

    bool start(const std::string& host = "127.0.0.1", int port = 8080);
    void stop();

    void update_frame(const FrameData& frame, int quality = 80);

    bool is_streaming() const;
    std::string get_url() const;
    int get_client_count() const;

private:
    void server_loop();

    std::string host_{"127.0.0.1"};
    int port_{8080};
    std::atomic<bool> is_running_{false};
    std::thread server_thread_;

    mutable std::mutex frame_mutex_;
    std::vector<uint8_t> latest_jpeg_;
    std::atomic<int> client_count_{0};

    struct Impl;
    std::unique_ptr<Impl> pimpl_;
};

} // namespace orion
