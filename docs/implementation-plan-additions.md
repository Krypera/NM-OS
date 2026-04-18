# NM-OS Implementation Plan Additions

This file extends the current implementation plan with missing work needed to fully match the NM-OS vision:
"broad user freedom, selectable security depth, and a clear product identity."

## P0 - Security Boundary Tightening

1. Narrow settings write authority.
- Keep `org.nmos.Settings1.Read` open to authorized user sessions.
- Restrict `org.nmos.Settings1.Write` to explicit trusted actors only.
- Replace broad implicit trust with an explicit authorization flow (Polkit-backed policy path).

2. Document runtime trust boundary as a release gate.
- Service process, greeter process, control center, and any helper process must each have declared authority.
- Every mutating endpoint must map to one allowed caller set.

## P1 - Real User Choice Enforcement

3. Promote browser choice from UI-only to enforced runtime setting.
- Add `default_browser` into the normalized settings model.
- Enforce via a post-login helper (`xdg-settings`/desktop defaults) with clear fallback behavior.

4. Expand language support policy.
- Keep high-quality default locales.
- Add contribution-ready locale workflow with translation quality checks.
- Add encoding CI checks to prevent mojibake regression.

5. Make profile switching "instant + safe."
- Distinguish "applies now" and "requires reboot" clearly in UI.
- Add one-click rollback to previous profile snapshot.

## P1 - Behavior-First Test Upgrade

6. Add behavior tests for settings backend failure states.
- Access denied
- Backend unavailable
- Transport error
- Commit failure with partial draft state

7. Add integration test for browser-default enforcement.
- Greeter selection -> persisted setting -> post-login applied default.

8. Add state-machine test coverage for onboarding.
- Skip path
- Back/next path
- Interrupted completion path

## P2 - Product Identity and Daily Usability

9. Integrate built-in help into desktop navigation and packaging checks.
- Launcher and desktop entry must be part of structure/release verification.
- User guides should be discoverable from both Help app and Control Center.

10. Add "Explain this setting" UX pattern for every security-facing toggle.
- What changes now
- What changes after reboot
- What compatibility risk this introduces

11. Add explicit "Comfort Mode" quick profile action.
- Low-friction mode switch without hiding advanced controls.
- Preserve existing user overrides unless explicitly reset.

## P2 - Release and Recovery Foundations

12. Formalize update + rollback architecture.
- Atomic update strategy decision
- Failure recovery UX
- Signed artifact and manifest verification requirements

13. Add release gates tied to enforcement matrix.
- Any new security-facing setting must have:
- documented enforcement layer
- behavior tests
- user-visible explanation
