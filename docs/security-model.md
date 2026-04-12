# Security Model

NM-OS treats security as a set of visible platform choices instead of a hidden mode switch.

The current direction is to let users move between a more comfortable desktop and a stricter system without losing clarity about what changed.

## Current Layers

### Security profiles

Profiles are the top-level entry point for most people.

They should define a coherent default posture across:

- networking
- app isolation
- device trust
- logging retention
- vault behavior
- desktop comfort choices that affect distraction and friction

### Network policy

Network behavior is one of the clearest trust boundaries in NM-OS.

Current states:

- `direct`
- `tor`
- `offline`

Users should always understand which state is active and what it implies.

### App isolation

The long-term direction is a stronger application-boundary model that remains understandable from the UI.

The system should explain:

- what the default isolation level is
- what changes when it becomes stricter
- where compatibility may narrow

### Device trust

Removable devices and external hardware should have an explicit trust posture instead of silent broad access.

The system should make it clear whether devices are:

- broadly trusted
- prompt-gated
- tightly limited

### Logging posture

Diagnostics are useful, but retained traces are also part of the attack surface and privacy story.

NM-OS should expose logging as a user-visible tradeoff:

- more diagnostics
- less retained history
- strongest minimization

### Encrypted vault

The encrypted vault is a concrete example of explainable security:

- users can see whether it exists
- whether it is locked
- how auto-lock behaves
- what convenience tradeoffs come from unlock choices

## Profile Matrix

| Profile | Goal | Network | Isolation | Devices | Logging | Tradeoff |
| --- | --- | --- | --- | --- | --- | --- |
| Relaxed | Lowest friction | Direct | Standard | Shared | Balanced | Easiest to use, weakest default boundaries |
| Balanced | Default daily-use baseline | Tor-first | Focused | Prompt | Minimal | Safer defaults with moderate friction |
| Hardened | Stronger daily containment | Tor-first | Strict | Locked | Minimal | Less convenience and narrower compatibility |
| Maximum | Highest practical restriction | Offline | Strict | Locked | Sealed | Strongest posture, intentionally restrictive |

## Direction For Future Work

1. Make every security-facing setting map to a real enforcement layer.
2. Add clearer permission and policy feedback to the desktop UI.
3. Reduce hidden privilege boundaries in services and helper processes.
4. Keep stronger modes readable instead of mystical.
5. Build update, rollback, and recovery behavior into the security story.
