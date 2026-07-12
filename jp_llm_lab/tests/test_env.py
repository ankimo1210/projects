from dataclasses import asdict

from jp_llm_lab.utils.env import EnvReport, collect_env_report, recommend_setup


def _fake(vram_gb, cuda=True):
    return EnvReport(
        python_version="3.12",
        torch_version="2.x",
        cuda_version="12.8" if cuda else None,
        cuda_available=cuda,
        gpu_name="fake" if cuda else None,
        vram_gb=vram_gb,
        capability="8.0" if cuda else None,
        bf16_supported=cuda,
        sdpa_backends=["math"],
        compile_available=False,
        cpu_ram_gb=32.0,
        cpu_count=8,
        platform="test",
    )


def test_report_fields_populated():
    r = collect_env_report()
    d = asdict(r)
    for key in ["python_version", "torch_version", "cpu_ram_gb", "sdpa_backends", "cpu_count"]:
        assert d[key], key
    assert isinstance(r.cuda_available, bool)


def test_recommendation_monotone_in_vram():
    small = recommend_setup(_fake(4.0))
    large = recommend_setup(_fake(16.0))
    assert small.micro_batch["S"] <= large.micro_batch["S"]
    assert small.micro_batch["L"] < large.micro_batch["L"]
    assert large.dtype == "bf16"


def test_grad_accum_reaches_target():
    s = recommend_setup(_fake(4.0), effective_tokens_target=16384)
    for size, ctx in [("S", 256), ("M", 512), ("L", 512)]:
        eff = s.micro_batch[size] * ctx * s.grad_accum[size]
        assert eff >= 16384


def test_cpu_fallback():
    s = recommend_setup(_fake(None, cuda=False))
    assert s.device == "cpu"
    assert s.dtype == "fp32"
    assert s.model_recommendation == "S"
