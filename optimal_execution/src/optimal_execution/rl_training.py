"""PPO training for execution policies (transparent, CPU-friendly).

Protocol (spec §13.5): disjoint train/validation/test scenario-seed streams;
periodic deterministic validation on a *fixed* seed set with early stopping
on the validation mean implementation shortfall (economic, not shaped);
best-checkpoint saving; per-update history rows written to CSV by the
experiments layer. Training rewards are the shaped rewards; validation and
all reported comparisons use economic IS only.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn

from .config import Config
from .environment import ExecutionEnv
from .evaluation import run_lob_episode
from .random import scenario_seeds
from .rl_policy import ActorCritic, RLPolicy, save_checkpoint
from .strategies import schedule_ac, schedule_twap

torch.set_num_threads(max(1, min(8, (torch.get_num_threads()))))


@dataclass
class TrainResult:
    checkpoint: Path
    history: list[dict[str, Any]] = field(default_factory=list)
    best_val_is_bps: float = float("nan")
    episodes_run: int = 0
    early_stopped: bool = False
    variant: str = "residual"
    seed: int = 0


def _gae(
    rewards: np.ndarray,
    values: np.ndarray,
    dones: np.ndarray,
    last_value: float,
    gamma: float,
    lam: float,
) -> tuple[np.ndarray, np.ndarray]:
    n = len(rewards)
    adv = np.zeros(n, dtype=np.float64)
    gae = 0.0
    for t in reversed(range(n)):
        next_nonterminal = 0.0 if dones[t] else 1.0
        next_v = 0.0 if dones[t] else (values[t + 1] if t + 1 < n else last_value)
        delta = rewards[t] + gamma * next_v * next_nonterminal - values[t]
        gae = delta + gamma * lam * next_nonterminal * gae
        adv[t] = gae
    returns = adv + values[:n]
    return adv, returns


def validate(
    cfg: Config,
    model: ActorCritic,
    baseline: np.ndarray,
    feature_mask: np.ndarray | None,
    n_episodes: int,
) -> float:
    """Deterministic-policy mean economic IS (bps) on the fixed val seeds."""
    policy = RLPolicy(model, deterministic=True)
    env = ExecutionEnv(cfg, baseline=baseline, feature_mask=feature_mask)
    seeds = scenario_seeds(cfg.seed, "val", n_episodes)
    vals = [run_lob_episode(env, policy, int(s))["is_bps"] for s in seeds]
    return float(np.mean(vals))


def train_ppo(
    cfg: Config,
    variant: str = "residual",
    seed: int | None = None,
    feature_mask: np.ndarray | None = None,
    episodes: int | None = None,
    out_dir: Path | str = "artifacts/checkpoints",
    tag: str | None = None,
) -> TrainResult:
    """Train one PPO policy.

    variant='residual': baseline = Almgren–Chriss schedule (hybrid strategy);
    variant='free'    : baseline = TWAP slice (schedule-free grid policy).
    """
    rl = cfg.rl
    seed = cfg.seed if seed is None else seed
    episodes = rl.training_episodes if episodes is None else episodes
    baseline = schedule_ac(cfg) if variant == "residual" else schedule_twap(cfg)
    tag = tag or f"{variant}_s{seed}"
    out = Path(out_dir)

    torch.manual_seed(seed)
    np.random.seed(seed % 2**31)
    model = ActorCritic(hidden=rl.hidden_size)
    opt = torch.optim.Adam(model.parameters(), lr=rl.learning_rate)

    env = ExecutionEnv(cfg, baseline=baseline, feature_mask=feature_mask)
    train_seeds = scenario_seeds(cfg.seed, f"train_{seed}", max(episodes, 1))

    history: list[dict[str, Any]] = []
    best_val = float("inf")
    best_path = out / f"ppo_{tag}_best.pt"
    patience_left = rl.early_stop_patience
    last_val_at = 0
    ep_count = 0
    step_count = 0
    ep_rewards: list[float] = []
    ep_is: list[float] = []
    t0 = time.time()
    early_stopped = False

    obs = env.reset(int(train_seeds[0]))
    ep_reward = 0.0

    while ep_count < episodes and not early_stopped:
        # ---- collect one rollout -------------------------------------------
        buf_obs = np.zeros((rl.rollout_steps, env._obs().shape[0]), dtype=np.float32)
        buf_act = np.zeros(rl.rollout_steps, dtype=np.int64)
        buf_logp = np.zeros(rl.rollout_steps, dtype=np.float64)
        buf_rew = np.zeros(rl.rollout_steps, dtype=np.float64)
        buf_val = np.zeros(rl.rollout_steps, dtype=np.float64)
        buf_done = np.zeros(rl.rollout_steps, dtype=bool)
        frac = min(ep_count / max(episodes, 1), 1.0)
        ent_coef = rl.entropy_coef + (rl.entropy_final - rl.entropy_coef) * frac

        t = 0
        while t < rl.rollout_steps:
            action, logp, value = model.act(obs, deterministic=False)
            buf_obs[t] = obs
            buf_act[t] = action
            buf_logp[t] = logp
            buf_val[t] = value
            obs, r, done, info = env.step(action)
            buf_rew[t] = r
            buf_done[t] = done
            ep_reward += r
            step_count += 1
            t += 1
            if done:
                ep_rewards.append(ep_reward)
                ep_is.append(info["episode"]["is_bps"])
                ep_reward = 0.0
                ep_count += 1
                obs = env.reset(int(train_seeds[ep_count % len(train_seeds)]))
                if ep_count >= episodes:
                    break

        used = t
        if used > 0 and not buf_done[used - 1]:
            _, _, last_value = model.act(obs, deterministic=True)
        else:
            last_value = 0.0
        adv, ret = _gae(
            buf_rew[:used],
            buf_val[:used],
            buf_done[:used],
            last_value=last_value,
            gamma=rl.gamma,
            lam=rl.gae_lambda,
        )
        adv_t = torch.as_tensor((adv - adv.mean()) / (adv.std() + 1e-8), dtype=torch.float32)
        ret_t = torch.as_tensor(ret, dtype=torch.float32)
        obs_t = torch.as_tensor(buf_obs[:used], dtype=torch.float32)
        act_t = torch.as_tensor(buf_act[:used])
        logp_old = torch.as_tensor(buf_logp[:used], dtype=torch.float32)

        # ---- PPO update ------------------------------------------------------
        idx = np.arange(used)
        pi_losses, v_losses, entropies = [], [], []
        for _ in range(rl.update_epochs):
            np.random.shuffle(idx)
            for start in range(0, used, rl.minibatch_size):
                mb = idx[start : start + rl.minibatch_size]
                logits, values = model(obs_t[mb])
                dist = torch.distributions.Categorical(logits=logits)
                logp = dist.log_prob(act_t[mb])
                ratio = torch.exp(logp - logp_old[mb])
                surr1 = ratio * adv_t[mb]
                surr2 = torch.clamp(ratio, 1 - rl.clip_epsilon, 1 + rl.clip_epsilon) * adv_t[mb]
                pi_loss = -torch.min(surr1, surr2).mean()
                v_loss = nn.functional.mse_loss(values, ret_t[mb])
                entropy = dist.entropy().mean()
                loss = pi_loss + rl.value_coef * v_loss - ent_coef * entropy
                opt.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), rl.max_grad_norm)
                opt.step()
                pi_losses.append(float(pi_loss.item()))
                v_losses.append(float(v_loss.item()))
                entropies.append(float(entropy.item()))

        # NaN guard: a single bad update aborts loudly rather than training on
        if not all(torch.isfinite(p).all() for p in model.parameters()):
            raise FloatingPointError(f"non-finite parameters after update (tag={tag})")

        # ---- periodic validation / early stopping ---------------------------
        crossed = (ep_count - last_val_at >= rl.eval_every_episodes) or ep_count >= episodes
        val_is = float("nan")
        if crossed and ep_count > 0:
            last_val_at = ep_count
            val_is = validate(cfg, model, baseline, feature_mask, rl.validation_episodes)
            if val_is < best_val - 1e-6:
                best_val = val_is
                patience_left = rl.early_stop_patience
                save_checkpoint(
                    model,
                    best_path,
                    {
                        "variant": variant,
                        "seed": seed,
                        "hidden": rl.hidden_size,
                        "episodes": ep_count,
                        "val_is_bps": best_val,
                        "feature_mask": None
                        if feature_mask is None
                        else list(map(float, feature_mask)),
                    },
                )
            else:
                patience_left -= 1
                if patience_left <= 0:
                    early_stopped = True

        history.append(
            {
                "episodes": ep_count,
                "steps": step_count,
                "train_reward_ma": float(np.mean(ep_rewards[-100:]))
                if ep_rewards
                else float("nan"),
                "train_is_ma_bps": float(np.mean(ep_is[-100:])) if ep_is else float("nan"),
                "val_is_bps": val_is,
                "best_val_is_bps": best_val if np.isfinite(best_val) else float("nan"),
                "pi_loss": float(np.mean(pi_losses)),
                "v_loss": float(np.mean(v_losses)),
                "entropy": float(np.mean(entropies)),
                "ent_coef": ent_coef,
                "wall_s": time.time() - t0,
            }
        )

    if not best_path.exists():
        save_checkpoint(
            model,
            best_path,
            {
                "variant": variant,
                "seed": seed,
                "hidden": rl.hidden_size,
                "episodes": ep_count,
                "val_is_bps": float("nan"),
                "feature_mask": None,
            },
        )
        best_val = validate(cfg, model, baseline, feature_mask, rl.validation_episodes)

    return TrainResult(
        checkpoint=best_path,
        history=history,
        best_val_is_bps=best_val,
        episodes_run=ep_count,
        early_stopped=early_stopped,
        variant=variant,
        seed=seed,
    )
