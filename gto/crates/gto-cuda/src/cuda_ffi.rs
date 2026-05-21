/// CUDA Driver API + NVRTC FFI bindings for RTX 5080 (sm_120).
/// We use dlopen/dlsym at runtime to avoid link-time dependency on CUDA libraries.

use std::ffi::{CStr, CString, c_void};
use std::sync::OnceLock;

// ---------------------------------------------------------------------------
// Type aliases
// ---------------------------------------------------------------------------

pub type CUdevice    = i32;
pub type CUdeviceptr = u64;
pub type CUresult    = u32;
pub type CUfunction  = *mut c_void;
pub type CUmodule    = *mut c_void;
pub type CUcontext   = *mut c_void;
pub type NvrtcResult = i32;
pub type NvrtcProgram = *mut c_void;

pub const CUDA_SUCCESS: CUresult = 0;
pub const NVRTC_SUCCESS: NvrtcResult = 0;

// ---------------------------------------------------------------------------
// Function pointer table (loaded once at startup)
// ---------------------------------------------------------------------------

struct CudaLib {
    // cuda driver
    cu_init:             unsafe extern "C" fn(u32) -> CUresult,
    cu_device_get:       unsafe extern "C" fn(*mut CUdevice, i32) -> CUresult,
    cu_ctx_create:       unsafe extern "C" fn(*mut CUcontext, u32, CUdevice) -> CUresult,
    cu_mem_alloc:        unsafe extern "C" fn(*mut CUdeviceptr, usize) -> CUresult,
    cu_mem_free:         unsafe extern "C" fn(CUdeviceptr) -> CUresult,
    cu_memcpy_htod:      unsafe extern "C" fn(CUdeviceptr, *const c_void, usize) -> CUresult,
    cu_memcpy_dtoh:      unsafe extern "C" fn(*mut c_void, CUdeviceptr, usize) -> CUresult,
    cu_memcpy_dtod:      unsafe extern "C" fn(CUdeviceptr, CUdeviceptr, usize) -> CUresult,
    cu_module_load_data: unsafe extern "C" fn(*mut CUmodule, *const c_void) -> CUresult,
    cu_module_get_fn:    unsafe extern "C" fn(*mut CUfunction, CUmodule, *const i8) -> CUresult,
    cu_launch_kernel:    unsafe extern "C" fn(CUfunction, u32,u32,u32, u32,u32,u32,
                                               u32, *mut c_void, *mut *mut c_void, *mut *mut c_void) -> CUresult,
    cu_ctx_sync:         unsafe extern "C" fn() -> CUresult,
    // nvrtc
    nvrtc_create:        unsafe extern "C" fn(*mut NvrtcProgram, *const i8, *const i8,
                                               i32, *const *const i8, *const *const i8) -> NvrtcResult,
    nvrtc_compile:       unsafe extern "C" fn(NvrtcProgram, i32, *const *const i8) -> NvrtcResult,
    nvrtc_get_ptx_size:  unsafe extern "C" fn(NvrtcProgram, *mut usize) -> NvrtcResult,
    nvrtc_get_ptx:       unsafe extern "C" fn(NvrtcProgram, *mut i8) -> NvrtcResult,
    nvrtc_get_log_size:  unsafe extern "C" fn(NvrtcProgram, *mut usize) -> NvrtcResult,
    nvrtc_get_log:       unsafe extern "C" fn(NvrtcProgram, *mut i8) -> NvrtcResult,
    nvrtc_destroy:       unsafe extern "C" fn(*mut NvrtcProgram) -> NvrtcResult,
}

unsafe impl Send for CudaLib {}
unsafe impl Sync for CudaLib {}

struct CtxWrapper(CUcontext);
unsafe impl Send for CtxWrapper {}
unsafe impl Sync for CtxWrapper {}

static CUDA_LIB: OnceLock<CudaLib> = OnceLock::new();
static CUDA_CTX: OnceLock<CtxWrapper> = OnceLock::new();

fn load_sym<T>(handle: *mut c_void, name: &str) -> T {
    let cname = CString::new(name).unwrap();
    let ptr = unsafe { libc_dlsym(handle, cname.as_ptr()) };
    assert!(!ptr.is_null(), "dlsym failed for {name}");
    unsafe { std::mem::transmute_copy(&ptr) }
}

unsafe extern "C" {
    fn dlopen(path: *const i8, flags: i32) -> *mut c_void;
    fn dlsym(handle: *mut c_void, symbol: *const i8) -> *mut c_void;
}

fn libc_dlopen(path: &str) -> *mut c_void {
    let cpath = CString::new(path).unwrap();
    unsafe { dlopen(cpath.as_ptr(), 2 /* RTLD_NOW */) }
}

fn libc_dlsym(handle: *mut c_void, name: *const i8) -> *mut c_void {
    unsafe { dlsym(handle, name) }
}

fn cuda_lib() -> &'static CudaLib {
    CUDA_LIB.get_or_init(|| {
        let cuda = ["libcuda.so.1", "libcuda.so"]
            .iter().find_map(|p| {
                let h = libc_dlopen(p);
                if h.is_null() { None } else { Some(h) }
            }).expect("libcuda.so not found");

        let nvrtc_paths = [
            "/usr/local/cuda/targets/x86_64-linux/lib/libnvrtc.so.12",
            "libnvrtc.so.12",
            "libnvrtc.so",
        ];
        let nvrtc = nvrtc_paths.iter().find_map(|p| {
            let h = libc_dlopen(p);
            if h.is_null() { None } else { Some(h) }
        }).expect("libnvrtc.so not found");

        CudaLib {
            cu_init:             load_sym(cuda, "cuInit"),
            cu_device_get:       load_sym(cuda, "cuDeviceGet"),
            cu_ctx_create:       load_sym(cuda, "cuCtxCreate_v2"),
            cu_mem_alloc:        load_sym(cuda, "cuMemAlloc_v2"),
            cu_mem_free:         load_sym(cuda, "cuMemFree_v2"),
            cu_memcpy_htod:      load_sym(cuda, "cuMemcpyHtoD_v2"),
            cu_memcpy_dtoh:      load_sym(cuda, "cuMemcpyDtoH_v2"),
            cu_memcpy_dtod:      load_sym(cuda, "cuMemcpyDtoD_v2"),
            cu_module_load_data: load_sym(cuda, "cuModuleLoadData"),
            cu_module_get_fn:    load_sym(cuda, "cuModuleGetFunction"),
            cu_launch_kernel:    load_sym(cuda, "cuLaunchKernel"),
            cu_ctx_sync:         load_sym(cuda, "cuCtxSynchronize"),
            nvrtc_create:        load_sym(nvrtc, "nvrtcCreateProgram"),
            nvrtc_compile:       load_sym(nvrtc, "nvrtcCompileProgram"),
            nvrtc_get_ptx_size:  load_sym(nvrtc, "nvrtcGetPTXSize"),
            nvrtc_get_ptx:       load_sym(nvrtc, "nvrtcGetPTX"),
            nvrtc_get_log_size:  load_sym(nvrtc, "nvrtcGetProgramLogSize"),
            nvrtc_get_log:       load_sym(nvrtc, "nvrtcGetProgramLog"),
            nvrtc_destroy:       load_sym(nvrtc, "nvrtcDestroyProgram"),
        }
    })
}

fn check(res: CUresult, api: &str) {
    assert_eq!(res, CUDA_SUCCESS, "CUDA error {res} in {api}");
}

fn check_nvrtc(res: NvrtcResult, api: &str) {
    assert_eq!(res, NVRTC_SUCCESS, "NVRTC error {res} in {api}");
}

// ---------------------------------------------------------------------------
// Public CUDA helpers
// ---------------------------------------------------------------------------

pub fn init_context() -> CUcontext {
    CUDA_CTX.get_or_init(|| {
        let lib = cuda_lib();
        unsafe {
            check((lib.cu_init)(0), "cuInit");
            let mut dev: CUdevice = 0;
            check((lib.cu_device_get)(&mut dev, 0), "cuDeviceGet");
            let mut ctx: CUcontext = std::ptr::null_mut();
            check((lib.cu_ctx_create)(&mut ctx, 0, dev), "cuCtxCreate");
            CtxWrapper(ctx)
        }
    }).0
}

pub fn mem_alloc(size: usize) -> CUdeviceptr {
    init_context();
    let lib = cuda_lib();
    let mut ptr: CUdeviceptr = 0;
    unsafe { check((lib.cu_mem_alloc)(&mut ptr, size), "cuMemAlloc"); }
    ptr
}

pub fn mem_free(ptr: CUdeviceptr) {
    let lib = cuda_lib();
    unsafe { (lib.cu_mem_free)(ptr); }
}

pub fn memcpy_htod<T>(dst: CUdeviceptr, src: &[T]) {
    let lib = cuda_lib();
    let bytes = std::mem::size_of_val(src);
    unsafe {
        check((lib.cu_memcpy_htod)(dst, src.as_ptr() as *const c_void, bytes), "cuMemcpyHtoD");
    }
}

pub fn memcpy_dtoh<T>(dst: &mut [T], src: CUdeviceptr) {
    let lib = cuda_lib();
    let bytes = std::mem::size_of_val(dst);
    unsafe {
        check((lib.cu_memcpy_dtoh)(dst.as_mut_ptr() as *mut c_void, src, bytes), "cuMemcpyDtoH");
    }
}

/// Device-to-device copy (stays entirely on GPU — no PCIe round trip).
pub fn memcpy_dtod(dst: CUdeviceptr, src: CUdeviceptr, bytes: usize) {
    let lib = cuda_lib();
    unsafe {
        check((lib.cu_memcpy_dtod)(dst, src, bytes), "cuMemcpyDtoD");
    }
}

/// Device-to-device copy with byte offset on the source pointer.
pub fn memcpy_dtod_offset(dst: CUdeviceptr, src: CUdeviceptr, src_offset: usize, bytes: usize) {
    memcpy_dtod(dst, src + src_offset as u64, bytes);
}

/// Device-to-device copy with byte offset on the destination pointer.
pub fn memcpy_dtod_into(dst: CUdeviceptr, dst_offset: usize, src: CUdeviceptr, bytes: usize) {
    memcpy_dtod(dst + dst_offset as u64, src, bytes);
}

pub fn ctx_sync() {
    let lib = cuda_lib();
    unsafe { check((lib.cu_ctx_sync)(), "cuCtxSynchronize"); }
}

/// JIT-compile CUDA C source to PTX using NVRTC, then load the module.
pub fn compile_and_load(src: &str, name: &str, arch: &str) -> (CUmodule, Vec<u8>) {
    init_context();
    let lib = cuda_lib();

    let src_c   = CString::new(src).unwrap();
    let name_c  = CString::new(name).unwrap();
    let arch_s  = CString::new(format!("--gpu-architecture={arch}")).unwrap();
    let std_s   = CString::new("--std=c++14").unwrap();
    let opts    = [arch_s.as_ptr(), std_s.as_ptr()];

    let mut prog: NvrtcProgram = std::ptr::null_mut();
    unsafe {
        check_nvrtc((lib.nvrtc_create)(
            &mut prog, src_c.as_ptr(), name_c.as_ptr(),
            0, std::ptr::null(), std::ptr::null()
        ), "nvrtcCreateProgram");

        let rc = (lib.nvrtc_compile)(prog, 2, opts.as_ptr());
        if rc != NVRTC_SUCCESS {
            let mut log_sz: usize = 0;
            (lib.nvrtc_get_log_size)(prog, &mut log_sz);
            let mut log = vec![0i8; log_sz];
            (lib.nvrtc_get_log)(prog, log.as_mut_ptr());
            let log_str = CStr::from_ptr(log.as_ptr()).to_string_lossy();
            panic!("NVRTC compile error:\n{log_str}");
        }

        let mut ptx_sz: usize = 0;
        check_nvrtc((lib.nvrtc_get_ptx_size)(prog, &mut ptx_sz), "nvrtcGetPTXSize");
        let mut ptx = vec![0i8; ptx_sz];
        check_nvrtc((lib.nvrtc_get_ptx)(prog, ptx.as_mut_ptr()), "nvrtcGetPTX");
        (lib.nvrtc_destroy)(&mut prog);

        let mut module: CUmodule = std::ptr::null_mut();
        check((lib.cu_module_load_data)(&mut module, ptx.as_ptr() as *const c_void), "cuModuleLoadData");

        let ptx_bytes: Vec<u8> = ptx.iter().map(|&b| b as u8).collect();
        (module, ptx_bytes)
    }
}

pub fn get_function(module: CUmodule, name: &str) -> CUfunction {
    let lib = cuda_lib();
    let name_c = CString::new(name).unwrap();
    let mut func: CUfunction = std::ptr::null_mut();
    unsafe {
        check((lib.cu_module_get_fn)(&mut func, module, name_c.as_ptr()), "cuModuleGetFunction");
    }
    func
}

/// Launch a CUDA kernel with raw argument pointers.
pub unsafe fn launch_kernel(
    func: CUfunction,
    grid: (u32, u32, u32),
    block: (u32, u32, u32),
    args: &[*mut c_void],
) {
    let lib = cuda_lib();
    let mut arg_ptrs: Vec<*mut c_void> = args.to_vec();
    check((lib.cu_launch_kernel)(
        func,
        grid.0, grid.1, grid.2,
        block.0, block.1, block.2,
        0, std::ptr::null_mut(),
        arg_ptrs.as_mut_ptr(),
        std::ptr::null_mut(),
    ), "cuLaunchKernel");
}
