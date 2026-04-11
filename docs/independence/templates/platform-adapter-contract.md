# Platform Adapter Contract Template

## Purpose
Define distro-specific capabilities consumed by NM-OS product core.

## Capabilities
- identity mapping:
  - display manager user/group
  - tor service user/group
- command providers:
  - firewall backend
  - crypto backend
  - session settings backend
- filesystem conventions:
  - runtime dir
  - persistent settings dir
  - service/policy install paths
- installer hooks:
  - post-install bootstrap entry
  - recovery entry registration

## Contract Rules
- Product core must not hardcode distro usernames/tool paths.
- Adapter must expose capability checks and explicit error messages.
- Adapter changes must not break D-Bus contracts.

