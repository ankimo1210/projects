#pragma once
// Parallel merge sort rung 3: buy it from the library. std::sort with the
// parallel execution policy dispatches to libstdc++'s TBB backend (link
// -ltbb). One line of user code is the entire point of this rung; the trade
// is that the thread count belongs to the library, not to you.
#include <algorithm>
#include <execution>
#include <functional>

namespace lab {

template <class RandomIt, class Compare = std::less<>>
void par_stl_sort(RandomIt first, RandomIt last, Compare comp = {}) {
    std::sort(std::execution::par, first, last, comp);
}

}  // namespace lab
