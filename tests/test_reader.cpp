#include "../movie_reader.h"
#include <cassert>
#include <iostream>

using movie_time::ReaderState;
using movie_time::ha_tag_id;

int main() {
  const std::string prefix = "https://www.home-assistant.io/tag/";
  assert(ha_tag_id("U", prefix + "movie-123") == "movie-123");
  assert(ha_tag_id("U", prefix + "Movie One") == "Movie One");
  assert(ha_tag_id("T", prefix + "movie-123").empty());
  assert(ha_tag_id("android.com:pkg", "io.homeassistant.companion.android").empty());
  assert(ha_tag_id("U", "https://example.org/" + prefix + "movie-123").empty());
  assert(ha_tag_id("U", prefix).empty());
  assert(ha_tag_id("U", prefix + std::string(128, 'a')).size() == 128);
  assert(ha_tag_id("U", prefix + std::string(129, 'a')).empty());
  assert(ha_tag_id("U", prefix + "bad\nvalue").empty());
  assert(ha_tag_id("U", prefix + "unknown").empty());
  assert(ha_tag_id("U", "https://www.home-assistant.io.evil/tag/movie").empty());
  assert(ha_tag_id("U", prefix + std::string(100000, 'a')).empty());
  // Only printable ASCII reaches HA: invalid UTF-8 and DEL fall back to UID.
  assert(ha_tag_id("U", prefix + "\xff\xfe").empty());
  assert(ha_tag_id("U", prefix + "caf\xc3\xa9").empty());
  assert(ha_tag_id("U", prefix + "bad\x7fvalue").empty());
  assert(ha_tag_id("U", prefix + "~ok~") == "~ok~");

  ReaderState r;
  assert(r.selected_id().empty());
  r.seen("01-02", "movie-a", 0);
  assert(!r.tick(299));
  assert(r.tick(300));
  assert(r.selected_id() == "movie-a");
  // Retain a tag's NDEF/HA ID if a later PN532 poll reports only its UID.
  r.seen("01-02", "01-02", 400);
  assert(!r.tick(1000));
  assert(r.selected_id() == "movie-a");
  // A case stays selected indefinitely without repeated on_tag callbacks.
  assert(!r.tick(10000000));
  assert(r.selected_id() == "movie-a");
  r.removed("01-02", 10000001);
  assert(!r.tick(10001400));
  r.seen("01-02", "movie-a", 10001401);
  assert(!r.tick(10003000));
  assert(r.selected_id() == "movie-a");
  r.removed("01-02", 10004000);
  r.removed("01-02", 10005000);  // Repeated removal must not postpone the stop.
  assert(!r.tick(10005499));
  assert(r.tick(10005500));
  assert(r.selected_id().empty());

  // PN532 reports a removal before it repeats a UID. A glitch followed by a
  // UID-only re-read within the removal delay keeps the NDEF/HA ID.
  ReaderState glitch;
  glitch.seen("04-AA", "movie-a", 0);
  assert(glitch.tick(300));
  glitch.removed("04-AA", 1000);
  glitch.seen("04-AA", "04-AA", 1250);
  assert(!glitch.tick(1400));
  assert(!glitch.tick(5000));
  assert(glitch.selected_id() == "movie-a");
  // After a completed removal, a UID-only read is all that is known.
  glitch.removed("04-AA", 6000);
  assert(glitch.tick(7500));
  assert(glitch.selected_id().empty());
  glitch.seen("04-AA", "04-AA", 8000);
  assert(glitch.tick(8300));
  assert(glitch.selected_id() == "04-AA");

  ReaderState swap;
  swap.seen("A", "movie-a", 0); swap.tick(300);
  swap.seen("B", "movie-b", 400);
  swap.removed("A", 450);  // Stale A event cannot eject B.
  assert(swap.tick(700));
  assert(swap.selected_id() == "movie-b");
  swap.seen("C", "movie-c", 800);
  swap.removed("C", 850); // Too brief to select C.
  assert(!swap.tick(1100));
  assert(swap.tick(2350));
  assert(swap.selected_id().empty());

  ReaderState brief;
  brief.seen("A", "movie-a", 0);
  brief.removed("A", 100);
  assert(!brief.tick(5000));
  assert(brief.selected_id().empty());

  ReaderState fault;
  fault.seen("A", "movie-a", 0); fault.tick(300);
  fault.fault(true, 400); fault.fault(true, 1000);
  fault.fault(false, 1200); fault.tick(3000);
  assert(fault.selected_id() == "movie-a");
  fault.fault(true, 3100); fault.fault(true, 4600);
  assert(fault.selected_id().empty());
  fault.fault(false, 5000); fault.tick(10000);
  assert(fault.selected_id().empty());
  fault.seen("A", "movie-a", 11000); fault.tick(11300);
  assert(fault.selected_id() == "movie-a");

  // The fault grace follows the configured removal delay.
  ReaderState patient;
  patient.seen("A", "movie-a", 0); patient.tick(300);
  patient.fault(true, 400, 3000); patient.fault(true, 2000, 3000);
  assert(patient.selected_id() == "movie-a");
  patient.fault(false, 2100, 3000);
  patient.fault(true, 2200, 3000); patient.fault(true, 5199, 3000);
  assert(patient.selected_id() == "movie-a");
  patient.fault(true, 5200, 3000);
  assert(patient.selected_id().empty());

  // Boot: report an empty reader only after it has polled cleanly.
  ReaderState unchecked;
  assert(!unchecked.ready(100000, 1150));
  ReaderState boot;
  boot.fault(true, 0);
  assert(!boot.ready(5000, 1150));
  boot.fault(false, 5000);
  assert(!boot.ready(6149, 1150));
  assert(boot.ready(6150, 1150));
  boot.fault(true, 6200);
  assert(boot.ready(6300, 1150));  // Latched once reported.
  // A held case found late is reported directly, never '' first.
  ReaderState late;
  late.fault(false, 0);
  late.seen("A", "movie-a", 1000);
  assert(!late.ready(1150, 1150));
  assert(!late.ready(1299, 1150));
  assert(late.tick(1300));
  assert(late.ready(1300, 1150));
  assert(late.selected_id() == "movie-a");

  ReaderState wrap;
  wrap.seen("A", "movie-a", UINT32_MAX - 200);
  assert(wrap.tick(100));
  wrap.removed("A", UINT32_MAX - 500);
  assert(!wrap.tick(998));
  assert(wrap.tick(999));

  // Stress the exact state helper used by firmware, including repeated swaps.
  ReaderState repeated;
  uint32_t now = 0;
  for (unsigned i = 0; i < 10000; ++i) {
    const auto id = "movie-" + std::to_string(i);
    repeated.seen("04-12-34", id, now);
    assert(repeated.tick(now + 300));
    assert(repeated.selected_id() == id);
    repeated.removed("04-12-34", now + 400);
    assert(repeated.tick(now + 1900));
    assert(repeated.selected_id().empty());
    now += 2000;
  }
  std::cout << "Reader parser, timing, fault recovery, boot readiness and 10000 insertion/removal cycles passed\n";
}
