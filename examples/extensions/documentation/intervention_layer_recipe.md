# Codex Recipe: Intervention Layer (Explicit + Minimal)

## Goal

Implement a **clean intervention layer** that:

- supports both historical timelines and future scenarios
- separates:
  - behavior / adoption
  - effectiveness (when needed)
- maps cleanly to OpenABM parameters

Do NOT implement timeline parsing yet.

---

## Scope

Implement:

- base intervention classes
- mask intervention (2-level)
- contact reduction intervention (1-level)
- simple compiler → OpenABM-compatible parameters

Do NOT implement:

- OxCGRT parsing
- calibration
- UI
- full vaccination yet

---

## Files

Create:

extensions/scenario_api/interventions.py

---

## 1. Base class

```python
from dataclasses import dataclass

@dataclass
class Intervention:
    name: str
    start: int
    end: int

    def apply(self, context):
        raise NotImplementedError
```

---

## 2. MaskProfile (effectiveness only)

```python
@dataclass
class MaskProfile:
    name: str
    effectiveness: dict  # {"surgical": 0.5, "ffp2": 0.95, ...}
```

---

## 3. MaskAdoptionIntervention

REQUIREMENTS:
- network_mix MUST include "none"
- values MUST sum to 1.0
- mask types MUST exist in profile

```python
@dataclass
class MaskAdoptionIntervention(Intervention):
    network_mix: dict  # {network: {mask_type: fraction}}
    mask_profile: MaskProfile

    def compute_multiplier(self, network: str) -> float:
        mix = self.network_mix[network]
        eff = self.mask_profile.effectiveness

        weighted = 0.0
        for k, v in mix.items():
            if k == "none":
                continue
            weighted += v * eff[k]

        return 1.0 - weighted
```

---

## 4. ContactReductionIntervention

```python
@dataclass
class ContactReductionIntervention(Intervention):
    multipliers: dict  # {network: value}
```

Example:
{"work": 0.5, "random": 0.3}

---

## 5. InterventionSet

```python
@dataclass
class InterventionSet:
    interventions: list

    def active_at(self, t: int):
        return [
            i for i in self.interventions
            if i.start <= t < i.end
        ]
```

---

## 6. Compiler

```python
def compile_network_multipliers(interventions, t):
    multipliers = {}

    active = interventions.active_at(t)

    for i in active:
        if isinstance(i, ContactReductionIntervention):
            for net, val in i.multipliers.items():
                multipliers[net] = multipliers.get(net, 1.0) * val

        elif isinstance(i, MaskAdoptionIntervention):
            for net in i.network_mix.keys():
                m = i.compute_multiplier(net)
                multipliers[net] = multipliers.get(net, 1.0) * m

    return multipliers
```

RULE:
- multipliers combine multiplicatively

---

## 7. Validation

Implement checks:

- mask mix sums to 1.0 ± 1e-6
- mask types exist in profile
- multipliers in [0,1]

Raise ValueError on failure.

---

## 8. Notebook

Create:

extensions/notebooks/intervention_layer_test.ipynb

### Steps

A. Create mask profile

```python
MaskProfile(
    name="default",
    effectiveness={
        "surgical": 0.5,
        "ffp2": 0.95,
        "ffp3": 0.99,
    }
)
```

B. Create mask intervention

```python
network_mix={
    "work": {"none": 0.3, "surgical": 0.5, "ffp2": 0.15, "ffp3": 0.05},
    "random": {"none": 0.4, "surgical": 0.4, "ffp2": 0.15, "ffp3": 0.05},
}
```

C. Contact reduction

```python
{"work": 0.5, "random": 0.3}
```

D. Combine

```python
InterventionSet([...])
```

E. Evaluate

```python
compile_network_multipliers(set, t=120)
```

F. Plot over time

---

## 9. Success criteria

- mask + contact combine correctly
- outputs reasonable
- notebook prints and plots values

---

## 10. Design rules

Do NOT:

- hardcode percentages
- mix adoption and effectiveness
- connect to timeline yet

---

## Final note

This is the core abstraction layer.

Keep it:
- simple
- explicit
- testable
