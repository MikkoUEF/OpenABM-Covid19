from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union
import math
import re

import numpy as np
import pandas as pd


OPENABM_AGE_BINS: List[Tuple[int, int, str]] = [
    (0, 9, "0_9"),
    (10, 19, "10_19"),
    (20, 29, "20_29"),
    (30, 39, "30_39"),
    (40, 49, "40_49"),
    (50, 59, "50_59"),
    (60, 69, "60_69"),
    (70, 79, "70_79"),
    (80, 200, "80_plus"),
]
OPENABM_AGE_BIN_LABELS: List[str] = [x[2] for x in OPENABM_AGE_BINS]


def age_to_openabm_bin_label(age: int) -> str:
    age_int = int(age)
    for lo, hi, label in OPENABM_AGE_BINS:
        if lo <= age_int <= hi:
            return label
    return "80_plus"


def household_age_histogram(household_ages: Sequence[int]) -> Dict[str, int]:
    hist = {label: 0 for label in OPENABM_AGE_BIN_LABELS}
    for age in household_ages:
        hist[age_to_openabm_bin_label(int(age))] += 1
    return hist


def split_age_7_12_uniform(count_7_12: int) -> Tuple[int, int]:
    """
    Deterministic split of age group 7-12 into OpenABM bins:
    - ages 7-9 (3 years) -> 0_9
    - ages 10-12 (3 years) -> 10_19
    """
    total = int(count_7_12)
    to_0_9 = int(math.floor(total * 0.5))
    to_10_19 = int(total - to_0_9)
    return to_0_9, to_10_19


def _collect_one_year_age_columns(row: Mapping[str, Any]) -> Dict[int, int]:
    out: Dict[int, int] = {}
    pattern = re.compile(r"^age_(\d{1,3})$")
    for key, value in row.items():
        m = pattern.match(str(key))
        if not m:
            continue
        age = int(m.group(1))
        out[age] = int(float(value)) if pd.notna(value) else 0
    return out


def harmonise_age_counts_to_openabm_bins(row: Mapping[str, Any]) -> Dict[str, int]:
    """
    Harmonise arbitrary age columns to OpenABM decade bins.

    Supported source styles:
    - one-year columns: age_0 ... age_100
    - grouped columns with names:
      age_0_6, age_7_12, age_13_17, age_18_24, age_25_34, age_35_44,
      age_45_54, age_55_64, age_65_74, age_75_84, age_85_plus
    """
    one_year = _collect_one_year_age_columns(row)
    out = {label: 0 for label in OPENABM_AGE_BIN_LABELS}
    if one_year:
        for age, count in one_year.items():
            out[age_to_openabm_bin_label(age)] += int(count)
        return out

    grouped = {
        "age_0_6": int(float(row.get("age_0_6", 0) or 0)),
        "age_7_12": int(float(row.get("age_7_12", 0) or 0)),
        "age_13_17": int(float(row.get("age_13_17", 0) or 0)),
        "age_18_24": int(float(row.get("age_18_24", 0) or 0)),
        "age_25_34": int(float(row.get("age_25_34", 0) or 0)),
        "age_35_44": int(float(row.get("age_35_44", 0) or 0)),
        "age_45_54": int(float(row.get("age_45_54", 0) or 0)),
        "age_55_64": int(float(row.get("age_55_64", 0) or 0)),
        "age_65_74": int(float(row.get("age_65_74", 0) or 0)),
        "age_75_84": int(float(row.get("age_75_84", 0) or 0)),
        "age_85_plus": int(float(row.get("age_85_plus", 0) or 0)),
    }
    if sum(grouped.values()) == 0:
        raise ValueError("Could not infer age distribution columns from row")

    split_7_12_to_0_9, split_7_12_to_10_19 = split_age_7_12_uniform(grouped["age_7_12"])
    out["0_9"] += grouped["age_0_6"] + split_7_12_to_0_9
    out["10_19"] += split_7_12_to_10_19 + grouped["age_13_17"] + int(round(grouped["age_18_24"] * (2 / 7)))
    out["20_29"] += int(round(grouped["age_18_24"] * (5 / 7))) + int(round(grouped["age_25_34"] * 0.5))
    out["30_39"] += grouped["age_25_34"] - int(round(grouped["age_25_34"] * 0.5)) + int(round(grouped["age_35_44"] * 0.5))
    out["40_49"] += grouped["age_35_44"] - int(round(grouped["age_35_44"] * 0.5)) + int(round(grouped["age_45_54"] * 0.5))
    out["50_59"] += grouped["age_45_54"] - int(round(grouped["age_45_54"] * 0.5)) + int(round(grouped["age_55_64"] * 0.5))
    out["60_69"] += grouped["age_55_64"] - int(round(grouped["age_55_64"] * 0.5)) + int(round(grouped["age_65_74"] * 0.5))
    out["70_79"] += grouped["age_65_74"] - int(round(grouped["age_65_74"] * 0.5)) + int(round(grouped["age_75_84"] * 0.5))
    out["80_plus"] += grouped["age_75_84"] - int(round(grouped["age_75_84"] * 0.5)) + grouped["age_85_plus"]
    return {k: int(max(0, v)) for k, v in out.items()}


def load_household_templates_from_table(
    path: Union[str, Path],
    household_id_col: str = "household_id",
    age_col: str = "age",
) -> List[List[int]]:
    table = pd.read_csv(path)
    if household_id_col not in table.columns or age_col not in table.columns:
        raise ValueError(f"Missing required columns: {household_id_col}, {age_col}")
    out = []
    for _, grp in table.groupby(household_id_col):
        ages = [int(float(x)) for x in grp[age_col].tolist() if pd.notna(x)]
        if ages:
            out.append(ages)
    if not out:
        raise ValueError("No valid households found in template table")
    return out


def _default_paavo_metadata_columns(frame: pd.DataFrame) -> List[str]:
    candidates = [
        "postcode_name",
        "municipality",
        "region",
        "latitude",
        "longitude",
        "lat",
        "lon",
        "x",
        "y",
    ]
    return [c for c in candidates if c in frame.columns]


def load_paavo_postcode_targets(
    path: Union[str, Path],
    postcode_col: str = "postcode",
    metadata_columns: Optional[Sequence[str]] = None,
) -> Tuple[Dict[str, Dict[str, int]], Dict[str, Dict[str, Any]], pd.DataFrame]:
    table = pd.read_csv(path)
    if postcode_col not in table.columns:
        raise ValueError(f"Missing postcode column '{postcode_col}'")
    meta_cols = list(metadata_columns) if metadata_columns is not None else _default_paavo_metadata_columns(table)

    target_counts: Dict[str, Dict[str, int]] = {}
    metadata: Dict[str, Dict[str, Any]] = {}
    rows = []
    for _, row in table.iterrows():
        postcode = str(row[postcode_col]).strip()
        if not postcode:
            continue
        counts = harmonise_age_counts_to_openabm_bins(row.to_dict())
        target_counts[postcode] = counts
        metadata[postcode] = {c: row.get(c) for c in meta_cols}
        rows.append({"postcode": postcode, **counts, **metadata[postcode]})
    if not target_counts:
        raise ValueError("No postcode targets could be loaded from PAAVO input")
    return target_counts, metadata, pd.DataFrame(rows)


@dataclass
class PopulationSynthesisConfig:
    random_seed: int = 1234
    max_iterations_per_postcode: int = 200_000
    phase1_fraction: float = 0.7
    soft_accept_prob_phase1: float = 0.03
    soft_accept_prob_phase2: float = 0.002
    overshoot_fraction_phase1: float = 0.12
    overshoot_fraction_phase2: float = 0.03
    population_tolerance: int = 6
    sse_threshold: float = 0.0
    enable_household_swap_refinement: bool = True
    swap_iterations_per_postcode: int = 20_000


@dataclass
class PostcodeSynthesisResult:
    postcode: str
    households: List[List[int]]
    current_counts: Dict[str, int]
    target_counts: Dict[str, int]
    diagnostics: Dict[str, Any] = field(default_factory=dict)


def _counts_to_array(counts: Mapping[str, int]) -> np.ndarray:
    return np.array([int(counts.get(k, 0)) for k in OPENABM_AGE_BIN_LABELS], dtype=np.int64)


def _array_to_counts(values: np.ndarray) -> Dict[str, int]:
    return {k: int(values[i]) for i, k in enumerate(OPENABM_AGE_BIN_LABELS)}


def _fit_score(current: np.ndarray, target: np.ndarray) -> float:
    diff = current - target
    return float(np.dot(diff, diff))


def _population_gap(current: np.ndarray, target: np.ndarray) -> int:
    return int(abs(int(current.sum()) - int(target.sum())))


def _allowed_overshoot(target: np.ndarray, frac: float) -> np.ndarray:
    return np.ceil(target * float(frac)).astype(np.int64) + 1


def _synthesize_one_postcode(
    postcode: str,
    target_counts: Dict[str, int],
    uk_households: List[List[int]],
    rng: np.random.Generator,
    config: PopulationSynthesisConfig,
) -> PostcodeSynthesisResult:
    target = _counts_to_array(target_counts)
    current = np.zeros_like(target)
    selected: List[List[int]] = []
    best_current = current.copy()
    best_selected: List[List[int]] = []
    best_score = _fit_score(current, target)

    max_household_size = max(len(h) for h in uk_households)
    phase1_iters = int(config.max_iterations_per_postcode * float(config.phase1_fraction))
    accepted_sampling_moves = 0
    sampling_iters_used = 0

    for it in range(config.max_iterations_per_postcode):
        sampling_iters_used = it + 1
        hh = uk_households[int(rng.integers(0, len(uk_households)))]
        hh_hist = _counts_to_array(household_age_histogram(hh))
        new_current = current + hh_hist

        phase1 = it < phase1_iters
        overshoot_frac = config.overshoot_fraction_phase1 if phase1 else config.overshoot_fraction_phase2
        overshoot_allow = _allowed_overshoot(target, overshoot_frac)
        overshoot = np.maximum(new_current - target, 0)
        if np.any(overshoot > overshoot_allow):
            continue

        score_before = _fit_score(current, target)
        score_after = _fit_score(new_current, target)
        accept = score_after <= score_before
        if not accept:
            p_soft = config.soft_accept_prob_phase1 if phase1 else config.soft_accept_prob_phase2
            accept = bool(rng.random() < p_soft)
        if not accept:
            continue

        current = new_current
        selected.append(list(hh))
        accepted_sampling_moves += 1

        current_score = _fit_score(current, target)
        current_gap = _population_gap(current, target)
        best_gap = _population_gap(best_current, target)
        if (current_gap < best_gap) or (current_gap == best_gap and current_score < best_score):
            best_current = current.copy()
            best_selected = list(selected)
            best_score = current_score

        if (
            current_gap <= max(config.population_tolerance, max_household_size)
            and current_score <= float(config.sse_threshold)
        ):
            break

    swap_attempts = 0
    swap_accepts = 0
    if config.enable_household_swap_refinement and len(selected) > 0 and int(config.swap_iterations_per_postcode) > 0:
        current = best_current.copy()
        selected = list(best_selected)
        selected_hists = [_counts_to_array(household_age_histogram(hh)) for hh in selected]
        current_gap = _population_gap(current, target)
        current_score = _fit_score(current, target)

        for _ in range(int(config.swap_iterations_per_postcode)):
            swap_attempts += 1
            idx_old = int(rng.integers(0, len(selected)))
            old_hh = selected[idx_old]
            old_hist = selected_hists[idx_old]
            new_hh = uk_households[int(rng.integers(0, len(uk_households)))]
            new_hist = _counts_to_array(household_age_histogram(new_hh))

            candidate = current - old_hist + new_hist
            cand_gap = _population_gap(candidate, target)
            cand_score = _fit_score(candidate, target)

            # Accept only moves that improve fit direction (lexicographic: population gap, then SSE).
            if (cand_gap < current_gap) or (cand_gap == current_gap and cand_score < current_score):
                current = candidate
                selected[idx_old] = list(new_hh)
                selected_hists[idx_old] = new_hist
                current_gap = cand_gap
                current_score = cand_score
                swap_accepts += 1

                if (
                    current_gap <= max(config.population_tolerance, max_household_size)
                    and current_score <= float(config.sse_threshold)
                ):
                    break

        best_current = current.copy()
        best_selected = list(selected)
        best_score = current_score

    final_counts = _array_to_counts(best_current)
    diag = {
        "sampling_iterations_used": int(sampling_iters_used),
        "accepted_sampling_moves": int(accepted_sampling_moves),
        "swap_attempts": int(swap_attempts),
        "swap_accepts": int(swap_accepts),
        "household_count": int(len(best_selected)),
        "target_population": int(target.sum()),
        "realised_population": int(best_current.sum()),
        "population_gap": int(_population_gap(best_current, target)),
        "sse": float(_fit_score(best_current, target)),
    }
    return PostcodeSynthesisResult(
        postcode=postcode,
        households=best_selected,
        current_counts=final_counts,
        target_counts={k: int(v) for k, v in target_counts.items()},
        diagnostics=diag,
    )


def build_postcode_population(
    target_counts: Dict[str, Dict[str, int]],
    uk_households: List[List[int]],
    random_seed: int = 1234,
    config: Optional[PopulationSynthesisConfig] = None,
    postcode_metadata: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    if not target_counts:
        raise ValueError("target_counts must not be empty")
    if not uk_households:
        raise ValueError("uk_households must not be empty")

    cfg = config or PopulationSynthesisConfig(random_seed=random_seed)
    rng = np.random.default_rng(int(random_seed))
    meta = postcode_metadata or {}

    results: Dict[str, PostcodeSynthesisResult] = {}
    household_rows: List[Dict[str, Any]] = []
    person_rows: List[Dict[str, Any]] = []
    postcode_validation_rows: List[Dict[str, Any]] = []

    household_idx = 0
    person_idx = 0
    for postcode in sorted(target_counts.keys()):
        res = _synthesize_one_postcode(
            postcode=postcode,
            target_counts=target_counts[postcode],
            uk_households=uk_households,
            rng=rng,
            config=cfg,
        )
        results[postcode] = res
        postcode_meta = dict(meta.get(postcode, {}))

        for hh in res.households:
            household_idx += 1
            household_id = f"H{household_idx:07d}"
            household_rows.append(
                {
                    "household_id": household_id,
                    "postcode": postcode,
                    "household_size": int(len(hh)),
                    **postcode_meta,
                }
            )
            for age in hh:
                person_idx += 1
                person_rows.append(
                    {
                        "person_id": int(person_idx),
                        "household_id": household_id,
                        "postcode": postcode,
                        "age": int(age),
                        "age_bin": age_to_openabm_bin_label(int(age)),
                        **postcode_meta,
                    }
                )

        row = {
            "postcode": postcode,
            "target_population": int(sum(res.target_counts.values())),
            "realised_population": int(sum(res.current_counts.values())),
            "population_gap": int(res.diagnostics["population_gap"]),
            "sse": float(res.diagnostics["sse"]),
            "household_count": int(res.diagnostics["household_count"]),
            "sampling_iterations_used": int(res.diagnostics.get("sampling_iterations_used", 0)),
            "accepted_sampling_moves": int(res.diagnostics.get("accepted_sampling_moves", 0)),
            "swap_attempts": int(res.diagnostics.get("swap_attempts", 0)),
            "swap_accepts": int(res.diagnostics.get("swap_accepts", 0)),
            **postcode_meta,
        }
        for label in OPENABM_AGE_BIN_LABELS:
            row[f"target_{label}"] = int(res.target_counts.get(label, 0))
            row[f"realised_{label}"] = int(res.current_counts.get(label, 0))
            row[f"abs_error_{label}"] = int(abs(row[f"realised_{label}"] - row[f"target_{label}"]))
        postcode_validation_rows.append(row)

    households_df = pd.DataFrame(household_rows)
    individuals_df = pd.DataFrame(person_rows)
    postcode_fit_df = pd.DataFrame(postcode_validation_rows).sort_values("postcode").reset_index(drop=True)

    global_summary = {
        "postcode_count": int(len(results)),
        "target_population_total": int(postcode_fit_df["target_population"].sum()),
        "realised_population_total": int(postcode_fit_df["realised_population"].sum()),
        "population_gap_total": int(abs(postcode_fit_df["realised_population"].sum() - postcode_fit_df["target_population"].sum())),
        "sse_total": float(postcode_fit_df["sse"].sum()),
        "household_count_total": int(len(households_df)),
        "person_count_total": int(len(individuals_df)),
        "random_seed": int(random_seed),
        "config": cfg,
    }
    return {
        "results_by_postcode": results,
        "households_df": households_df,
        "individuals_df": individuals_df,
        "postcode_fit_df": postcode_fit_df,
        "global_summary": global_summary,
    }
