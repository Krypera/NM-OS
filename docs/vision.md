# Product Direction

NM-OS is meant to be a configurable desktop operating system experience, not just a themed Linux install.

The goal is to let one person choose a calm, readable, low-friction system and let another person harden the same platform into a stricter environment with clearer trust boundaries and less convenience.

## Core Principles

### Explainable security

Security features should not feel like hidden magic.

Users should be able to see:

- what a profile changes
- why the system suggests a setting
- what tradeoff comes with a stronger default
- which changes apply immediately and which wait until reboot

### Choice without chaos

NM-OS should not force a single correct way to use the system.

Instead it should offer:

- clear defaults
- a small number of understandable profiles
- stronger overrides for people who need them
- language that describes consequences instead of jargon-heavy fear

### Progressive hardening

The system should be safe to start with, but it should also be able to grow with the user.

That means:

- comfortable defaults for new users
- stricter network, isolation, and device policies for advanced users
- a path from everyday desktop use to high-sensitivity use without switching ecosystems

### Visible trust boundaries

Whenever NM-OS restricts something, the boundary should be visible and understandable.

Examples:

- network policy should say whether the system is direct, Tor-first, or offline
- device policy should say how removable hardware is trusted
- app isolation should describe what gets broader or tighter access
- logging policy should explain what is kept and what is intentionally reduced

### Independence through layers

NM-OS does not need to begin as a new kernel or a from-scratch distribution to become a real operating system project.

Its identity comes from:

- its own policy model
- its own installer and update behavior
- its own security and recovery UX
- its own trust boundaries
- its own system defaults and platform decisions

Over time, the project can move more of those layers under NM-OS control.

## What NM-OS Should Not Become

- a skin over another system with no behavioral identity
- a security product that only experts can understand
- a locked-down environment that hides the cost of each restriction
- a convenience-focused desktop that uses security branding without real enforcement

## Near-Term Product Priorities

1. Keep profiles readable and explainable.
2. Tie profile language to real enforcement layers.
3. Make the greeter and control center describe tradeoffs clearly.
4. Treat installer, recovery, and updates as part of the platform identity.
5. Tighten service and policy boundaries as the architecture matures.
