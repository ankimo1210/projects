"""Shared setup cell for all generated notebooks."""

SETUP = r'''
import warnings
warnings.filterwarnings("ignore")
import json, math
from pathlib import Path
import numpy as np
import pandas as pd
import torch
import plotly.graph_objects as go
import plotly.io as pio
pio.renderers.default = "plotly_mimetype"
from jp_llm_lab.utils.io import repo_root, load_json, read_jsonl
ROOT = repo_root()
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
M2_RUN = ROOT / "experiments/runs/m2_model_m_classical_seed42"
'''
