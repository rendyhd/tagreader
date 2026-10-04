#include "../garage_reader.h"
#include <cassert>
#include <limits>

using garage_reader::ScanGate;
int main() {
  ScanGate gate;
  gate.connection(true, 100);
  assert(!gate.scan("wg34-1", 500, 2500, 2000)); // Boot suppressed
  gate.connection(true, 3000);
  assert(gate.ready(3000));
  assert(gate.scan("wg34-2", 3000, 2500, 2000));
  assert(!gate.scan("wg34-2", 4000, 2500, 2000));
  assert(!gate.scan("wg34-2", 6000, 2500, 2000)); // Sliding, not periodic repeat
  assert(gate.scan("wg34-2", 9000, 2500, 2000)); // Removed/re-presented
  assert(!gate.scan("wg34-3", 9100, 2500, 2000)); // Different-card rate limit
  assert(!gate.scan("wg34-3", 11200, 2500, 2000)); // Suppressed card stays observed
  assert(gate.scan("wg34-3", 14000, 2500, 2000));

  gate.connection(false, 15000);
  assert(!gate.scan("wg34-4", 16000, 2500, 2000));
  gate.connection(true, 17000);
  assert(!gate.ready(18999));
  assert(gate.ready(19000));
  assert(!gate.scan("wg34-4", 18000, 2500, 2000));
  assert(!gate.scan("wg34-4", 20000, 2500, 2000)); // No held-card replay
  assert(gate.scan("wg34-4", 23000, 2500, 2000));
  assert(!gate.scan("", 26000, 2500, 2000));

  ScanGate wrap;
  const uint32_t end = std::numeric_limits<uint32_t>::max();
  wrap.connection(true, end - 10000);
  assert(wrap.scan("wg26-1", end - 3000, 2500, 2000));
  assert(!wrap.scan("wg26-1", end - 1000, 2500, 2000));
  assert(!wrap.scan("wg26-1", 500, 2500, 2000));
  assert(wrap.scan("wg26-1", 4000, 2500, 2000));
  wrap.connection(false, end - 1000);
  wrap.connection(true, end - 500);
  assert(!wrap.ready(1000));
  assert(wrap.ready(1600));
}
