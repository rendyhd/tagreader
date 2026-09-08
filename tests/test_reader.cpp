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

  ReaderState r;
  assert(r.selected_id().empty());
  r.seen("01-02", "movie-a", 0);
  assert(!r.tick(299));
  assert(r.tick(300));
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
  std::cout << "Reader parser, timing, fault recovery and 10000 insertion/removal cycles passed\n";
}
