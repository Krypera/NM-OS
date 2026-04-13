from __future__ import annotations


def resolve_unix_uid(username: str | None) -> int | None:
    name = str(username or "").strip()
    if not name:
        return None
    try:
        import pwd  # type: ignore[import-not-found]
    except ImportError:
        return None
    try:
        return int(pwd.getpwnam(name).pw_uid)
    except KeyError:
        return None


def build_write_uid_allowlist(gdm_user: str | None) -> set[int]:
    allowed = {0}
    gdm_uid = resolve_unix_uid(gdm_user)
    if gdm_uid is not None:
        allowed.add(gdm_uid)
    return allowed


def is_write_authorized(uid: int, allowed_uids: set[int]) -> bool:
    return int(uid) in allowed_uids
