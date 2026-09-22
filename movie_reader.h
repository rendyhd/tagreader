#pragma once

#include <cstdint>
#include <string>

namespace movie_time {

// Keep IDs small and reject control characters before publishing them to HA.
inline bool valid_id(const std::string &value) {
  if (value.empty() || value.size() > 128)
    return false;
  for (unsigned char c : value)
    if (c < 0x20 || c == 0x7f)
      return false;
  return value != "unknown" && value != "unavailable";
}

inline std::string ha_tag_id(const std::string &type, const std::string &payload) {
  static const std::string prefix = "https://www.home-assistant.io/tag/";
  if (type != "U" || payload.size() > prefix.size() + 128 ||
      payload.compare(0, prefix.size(), prefix) != 0)
    return {};
  const auto id = payload.substr(prefix.size());
  return valid_id(id) ? id : std::string{};
}

// PN532 reports transitions, not a callback for every successful poll. A timer
// based on the last on_tag callback would incorrectly eject a held case.
class ReaderState {
 public:
  void seen(const std::string &uid, const std::string &id, uint32_t now) {
    if (!valid_id(uid) || !valid_id(id))
      return;
    // Some PN532 reads expose only the UID after an earlier read exposed the
    // tag's NDEF/HA ID.  Keep that richer ID while the same physical tag is
    // still present, otherwise HA would alternate between two movie IDs.
    if (uid == observed_uid_ && id == uid && observed_id_ != uid)
      return;
    if (uid == observed_uid_ && id == observed_id_)
      return;
    observed_uid_ = uid;
    observed_id_ = id;
    changed_at_ = now;
  }

  void removed(const std::string &uid, uint32_t now) {
    // A delayed removal for A must not remove a newly inserted B.
    if (uid == observed_uid_)
      missing(now);
  }

  void missing(uint32_t now) {
    if (observed_uid_.empty())
      return;
    observed_uid_.clear();
    observed_id_.clear();
    changed_at_ = now;
  }

  void fault(bool failed, uint32_t now, uint32_t grace_ms = 1500) {
    if (!failed) {
      fault_pending_ = false;
      return;
    }
    if (!fault_pending_) {
      fault_pending_ = true;
      fault_since_ = now;
    }
    if (static_cast<uint32_t>(now - fault_since_) >= grace_ms) {
      observed_uid_.clear();
      observed_id_.clear();
      selected_uid_.clear();
      selected_id_.clear();
    }
    // PN532 may suppress the same UID after communication recovers. Reinsert
    // the case after a sustained hardware fault; never restore stale selection.
  }

  bool tick(uint32_t now, uint32_t insertion_ms = 300, uint32_t removal_ms = 1500) {
    if (observed_uid_ == selected_uid_ && observed_id_ == selected_id_)
      return false;
    const auto wait = observed_uid_.empty() ? removal_ms : insertion_ms;
    // Unsigned subtraction also works across the millis() rollover.
    if (static_cast<uint32_t>(now - changed_at_) < wait)
      return false;
    selected_uid_ = observed_uid_;
    selected_id_ = observed_id_;
    return true;
  }

  const std::string &selected_id() const { return selected_id_; }
  const std::string &selected_uid() const { return selected_uid_; }

 private:
  std::string observed_uid_;
  std::string observed_id_;
  std::string selected_uid_;
  std::string selected_id_;
  uint32_t changed_at_{0};
  uint32_t fault_since_{0};
  bool fault_pending_{false};
};

inline ReaderState &reader() {
  static ReaderState instance;
  return instance;
}
}  // namespace movie_time
