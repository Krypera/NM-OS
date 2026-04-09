from __future__ import annotations

from pathlib import Path

LIVE_RUNTIME_USERNAME_CONFIG = Path("/etc/live/config.d/username.conf")
LIVE_DEFAULTS_CONFIG = Path("/etc/nmos/live-user.conf")


def read_assignment_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    data: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def load_gdm():
    import gi

    gi.require_version("Gdm", "1.0")
    from gi.repository import Gdm

    return Gdm


def live_username(
    default: str = "nmos",
    *,
    defaults_config: Path = LIVE_DEFAULTS_CONFIG,
    runtime_config: Path = LIVE_RUNTIME_USERNAME_CONFIG,
) -> str:
    defaults = read_assignment_file(defaults_config)
    configured_default = defaults.get("LIVE_USERNAME") or default

    runtime_values = read_assignment_file(runtime_config)
    value = runtime_values.get("LIVE_USERNAME")
    return value or configured_default


def live_password(default: str = "live", *, defaults_config: Path = LIVE_DEFAULTS_CONFIG) -> str:
    defaults = read_assignment_file(defaults_config)
    value = defaults.get("LIVE_PASSWORD")
    return value or default


def live_credentials(
    default_username: str = "nmos",
    default_password: str = "live",
    *,
    defaults_config: Path = LIVE_DEFAULTS_CONFIG,
    runtime_config: Path = LIVE_RUNTIME_USERNAME_CONFIG,
) -> tuple[str, str]:
    return (
        live_username(default_username, defaults_config=defaults_config, runtime_config=runtime_config),
        live_password(default_password, defaults_config=defaults_config),
    )


class GdmLoginClient:
    def __init__(self, session_opened_cb=None, problem_cb=None) -> None:
        self.session_opened_cb = session_opened_cb
        self.problem_cb = problem_cb
        self.username, self.password = live_credentials()
        self.last_problem = ""
        self.verification_complete = False
        self.session_opened = False

        Gdm = load_gdm()
        client = Gdm.Client()
        self.greeter = client.get_greeter_sync(None)
        self.user_verifier = client.get_user_verifier_sync(None)
        self.greeter.connect("session-opened", self._on_session_opened)
        self.greeter.connect("timed-login-requested", self._on_timed_login_requested)
        self.user_verifier.connect("info", self._on_info)
        self.user_verifier.connect("problem", self._on_problem)
        self.user_verifier.connect("info_query", self._on_info_query)
        self.user_verifier.connect("secret_info_query", self._on_secret_info_query)
        self.user_verifier.connect("conversation-stopped", self._on_conversation_stopped)
        self.user_verifier.connect("reset", self._on_reset)
        self.user_verifier.connect("verification-complete", self._on_verification_complete)

    def _report_problem(self, message: str) -> None:
        if not message:
            return
        self.last_problem = str(message)
        if self.problem_cb is not None:
            self.problem_cb(self.last_problem)

    def _on_info(self, _client, _service_name, _info: str) -> None:
        return

    def _on_problem(self, _client, _service_name, problem: str) -> None:
        self._report_problem(str(problem))

    def _on_info_query(self, _client, service_name: str, _question: str) -> None:
        # Some PAM stacks can still issue an info query even when we began
        # verification with a preselected username.
        self.user_verifier.call_answer_query(service_name, self.username, None, None, None)

    def _on_secret_info_query(self, _client, service_name: str, _secret_question: str) -> None:
        self.user_verifier.call_answer_query(service_name, self.password, None, None, None)

    def _on_conversation_stopped(self, _client, _service_name: str) -> None:
        if not self.session_opened and not self.verification_complete:
            self._report_problem("GDM stopped the live-session login conversation.")

    def _on_reset(self, *_args) -> None:
        if not self.session_opened and not self.verification_complete:
            self._report_problem("GDM reset the live-session login flow.")

    def _on_verification_complete(self, *_args) -> None:
        self.verification_complete = True

    def _on_session_opened(self, _client, service_name: str, _unused) -> None:
        self.session_opened = True
        try:
            self.greeter.call_start_session_when_ready_sync(service_name, True, None)
        except Exception as exc:
            self.session_opened = False
            self._report_problem(f"GDM could not start the live session: {exc}")
            return
        if self.session_opened_cb is not None:
            self.session_opened_cb()

    def _on_timed_login_requested(self, _client, user_name: str, seconds: int) -> None:
        self._report_problem(
            f"Unexpected timed login request for {user_name} in {seconds} seconds while NM-OS welcome flow is active."
        )

    def start_session(self) -> None:
        if not self.username:
            raise RuntimeError("live username is missing")
        if not self.password:
            raise RuntimeError("live password is missing")
        self.last_problem = ""
        self.verification_complete = False
        self.session_opened = False
        self.user_verifier.call_begin_verification_for_user_sync(
            "gdm-password",
            self.username,
            None,
        )
