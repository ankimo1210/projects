# Source from the project root. RUNTIME_TMP may point to any writable directory.
# The feedback round sets it to its authorized audit temporary directory.
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR="${RUNTIME_TMP:-$PWD/tmp}"
export MPLCONFIGDIR="$TMPDIR/matplotlib"
export XDG_CACHE_HOME="$TMPDIR/cache"
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export PYTHONHASHSEED=0
mkdir -p "$TMPDIR" "$MPLCONFIGDIR" "$XDG_CACHE_HOME"
