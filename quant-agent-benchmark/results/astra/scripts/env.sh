# Source from the project root. Runtime temporary files stay within this run.
export TMPDIR="$PWD/tmp"
export XDG_CACHE_HOME="$PWD/tmp/cache"
export MPLCONFIGDIR="$PWD/tmp/matplotlib"
export PIP_CACHE_DIR="$PWD/tmp/pip"
export PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export PYTHONHASHSEED=0
export PYTHONPATH="$PWD/src"
export PATH="$PWD/.venv/bin:$PATH"
