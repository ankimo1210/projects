"""Sanity check for GPU stack: CuPy, Numba CUDA, VisPy import."""

from __future__ import annotations

import sys


def check_cupy() -> bool:
    try:
        import cupy as cp
    except Exception as e:
        print(f"[FAIL] CuPy import: {e}")
        return False
    try:
        a = cp.arange(10, dtype=cp.float32)
        b = (a * 2).sum().item()
        dev = cp.cuda.runtime.getDeviceProperties(0)
        name = dev["name"].decode() if isinstance(dev["name"], bytes) else dev["name"]
        cc = f"{dev['major']}.{dev['minor']}"
        print(f"[ OK ] CuPy {cp.__version__} | device: {name} | CC {cc} | (sum 2*[0..9]={b})")
        return True
    except Exception as e:
        print(f"[FAIL] CuPy runtime: {e}")
        return False


def check_raw_kernel() -> bool:
    """Compile a trivial RawKernel to verify nvcc / nvrtc path works on this GPU."""
    try:
        import cupy as cp

        kern = cp.RawKernel(
            r"""
            extern "C" __global__
            void add_one(const float* x, float* y, int n) {
                int i = blockIdx.x * blockDim.x + threadIdx.x;
                if (i < n) y[i] = x[i] + 1.0f;
            }
            """,
            "add_one",
        )
        n = 1024
        x = cp.arange(n, dtype=cp.float32)
        y = cp.empty_like(x)
        threads = 128
        blocks = (n + threads - 1) // threads
        kern((blocks,), (threads,), (x, y, n))
        cp.cuda.runtime.deviceSynchronize()
        assert float(y[0]) == 1.0 and float(y[-1]) == float(n - 1) + 1.0
        print(f"[ OK ] CuPy RawKernel compiled & ran (y[0]=1.0, y[-1]={float(y[-1])})")
        return True
    except Exception as e:
        print(f"[FAIL] RawKernel: {e}")
        return False


def check_vispy() -> bool:
    try:
        import vispy

        print(f"[ OK ] VisPy {vispy.__version__}")
        return True
    except Exception as e:
        print(f"[FAIL] VisPy import: {e}")
        return False


def main() -> int:
    print("== nbody-gpu env check ==")
    results = [check_cupy(), check_raw_kernel(), check_vispy()]
    ok = all(results)
    print("==", "ALL OK" if ok else "FAILURES PRESENT", "==")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
