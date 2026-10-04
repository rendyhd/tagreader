#pragma once
#include <cstdint>
#include <string>

namespace garage_reader {
// No queued scans, flash writes, or permissions stored on the outdoor reader.
class ScanGate {
 public:
  void connection(bool online, uint32_t now) {
    if (now >= 3000) boot_ready_ = true;
    if (!online) {
      online_ = false;
    } else if (!online_) {
      online_ = true;
      connected_at_ = now;
    }
  }

  bool ready(uint32_t now) const {
    return boot_ready_ && online_ && uint32_t(now - connected_at_) >= 2000;
  }

  bool scan(const std::string &tag, uint32_t now, uint32_t quiet_ms,
            uint32_t cooldown_ms) {
    const bool repeated = seen_ && tag == last_tag_ && uint32_t(now - last_seen_) < quiet_ms;
    // Observe even while offline/cooling down. A held repeating card must be
    // removed before it can trigger after reconnect, rather than replayed.
    last_tag_ = tag;
    last_seen_ = now;
    seen_ = true;
    if (!ready(now) || repeated || tag.empty()) return false;
    if (sent_ && uint32_t(now - last_sent_) < cooldown_ms) return false;
    last_sent_ = now;
    sent_ = true;
    return true;
  }

 private:
  bool boot_ready_{false}, online_{false}, seen_{false}, sent_{false};
  uint32_t connected_at_{0}, last_seen_{0}, last_sent_{0};
  std::string last_tag_;
};

inline ScanGate &gate() {
  static ScanGate instance;
  return instance;
}
}  // namespace garage_reader
