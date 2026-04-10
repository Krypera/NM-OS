from __future__ import annotations

import re

from nmos_common.boot_mode import MODE_COMPAT, MODE_FLEXIBLE, MODE_OFFLINE, MODE_RECOVERY, MODE_STRICT

DEFAULT_UI_LOCALE = "en_US.UTF-8"
LANGUAGE_OPTIONS = (
    (DEFAULT_UI_LOCALE, "English"),
    ("es_ES.UTF-8", "Espa\u00f1ol"),
)

LANGUAGE_LABELS = {locale: label for locale, label in LANGUAGE_OPTIONS}

BOOT_MODE_TITLES = {
    MODE_STRICT: "Strict",
    MODE_FLEXIBLE: "Flexible",
    MODE_OFFLINE: "Offline",
    MODE_RECOVERY: "Recovery",
    MODE_COMPAT: "Hardware Compatibility",
}

TRANSLATIONS = {
    "es": {
        "NM-OS Greeter": "Bienvenida de NM-OS",
        "Prepare your session before entering the desktop.": "Prepara tu sesi\u00f3n antes de entrar al escritorio.",
        "Language": "Idioma",
        "Choose the session language.": "Elige el idioma de la sesi\u00f3n.",
        "Keyboard": "Teclado",
        "Choose the keyboard layout.": "Elige la distribuci\u00f3n del teclado.",
        "Network": "Red",
        "Persistence": "Persistencia",
        "Refresh network status": "Actualizar estado de la red",
        "Continue to desktop while network stays blocked": "Continuar al escritorio mientras la red sigue bloqueada",
        "Create": "Crear",
        "Unlock": "Desbloquear",
        "Lock": "Bloquear",
        "Repair": "Reparar",
        "Back": "Atr\u00e1s",
        "Next": "Siguiente",
        "Finish": "Finalizar",
        "Strict": "Estricto",
        "Flexible": "Flexible",
        "Offline": "Sin conexi\u00f3n",
        "Recovery": "Recuperaci\u00f3n",
        "Hardware Compatibility": "Compatibilidad de hardware",
        "Tor-first with a more relaxed onboarding flow.": "Tor primero con un flujo de inicio m\u00e1s flexible.",
        "Networking is intentionally disabled for this session.": "La red est\u00e1 desactivada intencionalmente para esta sesi\u00f3n.",
        "Recovery-first session with networking intentionally disabled.": "Sesi\u00f3n centrada en recuperaci\u00f3n con la red desactivada intencionalmente.",
        "Compatibility boot options are enabled while keeping strict network policy.": "Las opciones de compatibilidad est\u00e1n activadas mientras se mantiene una pol\u00edtica de red estricta.",
        "Tor-first strict profile is active.": "El perfil estricto con Tor primero est\u00e1 activo.",
        "Mode: {mode} - {description}": "Modo: {mode} - {description}",
        "Waiting for Tor": "Esperando a Tor",
        "Tor is ready": "Tor est\u00e1 listo",
        "Waiting for Tor bootstrap": "Esperando el arranque de Tor",
        "Waiting for Tor control": "Esperando el control de Tor",
        "Preparing network policy": "Preparando la pol\u00edtica de red",
        "Network bootstrap failed": "Fall\u00f3 el arranque de la red",
        "Unable to read network status": "No se pudo leer el estado de la red",
        "invalid status payload": "la carga del estado no es v\u00e1lida",
        "Network is disabled by boot mode ({mode}).": "La red est\u00e1 desactivada por el modo de arranque ({mode}).",
        "Network is intentionally disabled for this boot mode.": "La red est\u00e1 desactivada intencionalmente para este modo de arranque.",
        "Network status: {error}": "Estado de la red: {error}",
        "Tor connection is ready.": "La conexi\u00f3n de Tor est\u00e1 lista.",
        "Waiting for Tor to become ready.": "Esperando a que Tor est\u00e9 listo.",
        "Persistence backend unavailable: {error}": "El servicio de persistencia no est\u00e1 disponible: {error}",
        "Persistence error: {error}": "Error de persistencia: {error}",
        "Persistence operation is in progress.": "Hay una operaci\u00f3n de persistencia en curso.",
        "Persistence is unlocked and ready.": "La persistencia est\u00e1 desbloqueada y lista.",
        "Persistence exists on {device} and can be unlocked.": "La persistencia existe en {device} y se puede desbloquear.",
        "Persistence cannot be created on {device} because less than 1 GiB of free space remains.": "No se puede crear persistencia en {device} porque queda menos de 1 GiB de espacio libre.",
        "Persistence creation is disabled because NM-OS was not started from a writable USB device.": "La creaci\u00f3n de persistencia est\u00e1 desactivada porque NM-OS no se inici\u00f3 desde un USB escribible.",
        "Persistence creation is disabled because the boot USB layout cannot safely accept an appended partition.": "La creaci\u00f3n de persistencia est\u00e1 desactivada porque la estructura del USB de arranque no puede aceptar otra partici\u00f3n de forma segura.",
        "Persistence creation is disabled because the boot USB is read-only.": "La creaci\u00f3n de persistencia est\u00e1 desactivada porque el USB de arranque es de solo lectura.",
        "Persistence can be created on {device}.": "Se puede crear persistencia en {device}.",
        "Persistence already exists on {device}.": "La persistencia ya existe en {device}.",
        "Persistence state is unavailable.": "El estado de la persistencia no est\u00e1 disponible.",
        "the boot USB": "el USB de arranque",
        "Unable to save language selection: {error}": "No se pudo guardar la selecci\u00f3n de idioma: {error}",
        "Language will be applied as {language}.": "El idioma se aplicar\u00e1 como {language}.",
        "Unable to save keyboard selection: {error}": "No se pudo guardar la selecci\u00f3n del teclado: {error}",
        "Keyboard layout will be applied as {layout}.": "La distribuci\u00f3n del teclado se aplicar\u00e1 como {layout}.",
        "This boot mode is intentionally offline.": "Este modo de arranque funciona intencionalmente sin conexi\u00f3n.",
        "You can continue to desktop now, but network traffic stays blocked until Tor is ready.": "Ya puedes continuar al escritorio, pero el tr\u00e1fico de red seguir\u00e1 bloqueado hasta que Tor est\u00e9 listo.",
        "Continue without network is disabled. Wait for Tor readiness to proceed.": "Continuar sin red est\u00e1 desactivado. Espera a que Tor est\u00e9 listo para continuar.",
        "Persistence {action} is still running. Please wait.": "La acci\u00f3n de persistencia {action} sigue en curso. Espera por favor.",
        "Persistence status is refreshing. Please wait.": "Se est\u00e1 actualizando el estado de la persistencia. Espera por favor.",
        "Persistence {action} is in progress...": "La acci\u00f3n de persistencia {action} est\u00e1 en curso...",
        "Starting persistence {action}...": "Iniciando la acci\u00f3n de persistencia {action}...",
        "Persistence {action} failed: {error}": "La acci\u00f3n de persistencia {action} fall\u00f3: {error}",
        "Persistence {action} request completed.": "La acci\u00f3n de persistencia {action} se complet\u00f3.",
        "Session is not ready yet.": "La sesi\u00f3n todav\u00eda no est\u00e1 lista.",
        "Failed to save greeter state: {error}": "No se pudo guardar el estado de la bienvenida: {error}",
        "GDM session control is unavailable: {error}": "El control de sesi\u00f3n de GDM no est\u00e1 disponible: {error}",
        "Greeter state saved, but GDM session control is unavailable.": "Se guard\u00f3 el estado de la bienvenida, pero el control de sesi\u00f3n de GDM no est\u00e1 disponible.",
        "Starting the live session...": "Iniciando la sesi\u00f3n en vivo...",
        "Failed to start the live session: {error}": "No se pudo iniciar la sesi\u00f3n en vivo: {error}",
        "Live session start timed out. Login flow reset failed: {error}": "Se agot\u00f3 el tiempo para iniciar la sesi\u00f3n en vivo. No se pudo reiniciar el flujo de acceso: {error}",
        "Live session start timed out. Login flow was reset.": "Se agot\u00f3 el tiempo para iniciar la sesi\u00f3n en vivo. El flujo de acceso se reinici\u00f3.",
        "Live session start failed: {problem}": "No se pudo iniciar la sesi\u00f3n en vivo: {problem}",
        "GDM stopped the live-session login conversation.": "GDM detuvo la conversaci\u00f3n de acceso de la sesi\u00f3n en vivo.",
        "GDM reset the live-session login flow.": "GDM reinici\u00f3 el flujo de acceso de la sesi\u00f3n en vivo.",
        "GDM could not start the live session: {error}": "GDM no pudo iniciar la sesi\u00f3n en vivo: {error}",
        "Unexpected timed login request for {user_name} in {seconds} seconds while NM-OS welcome flow is active.": "Solicitud inesperada de acceso temporizado para {user_name} en {seconds} segundos mientras el flujo de bienvenida de NM-OS est\u00e1 activo.",
        "live username is missing": "falta el nombre de usuario de la sesi\u00f3n en vivo",
        "live password is missing": "falta la contrase\u00f1a de la sesi\u00f3n en vivo",
        "internal error": "error interno",
    }
}


def locale_language(locale: str | None) -> str:
    text = str(locale or "").strip()
    if not text:
        return ""
    return re.split(r"[_@.]", text, maxsplit=1)[0].lower()


def resolve_supported_locale(locale: str | None, default: str = DEFAULT_UI_LOCALE) -> str:
    text = str(locale or "").strip()
    if not text:
        return default
    for supported, _label in LANGUAGE_OPTIONS:
        if text.lower() == supported.lower():
            return supported
    language = locale_language(text)
    for supported, _label in LANGUAGE_OPTIONS:
        if locale_language(supported) == language:
            return supported
    return default


def display_language_name(locale: str | None) -> str:
    resolved = resolve_supported_locale(locale)
    return LANGUAGE_LABELS.get(resolved, resolved)


def translate(locale: str | None, source_text: str, **kwargs) -> str:
    language = locale_language(resolve_supported_locale(locale))
    template = TRANSLATIONS.get(language, {}).get(source_text, source_text)
    return template.format(**kwargs)


def boot_mode_title(mode: str) -> str:
    return BOOT_MODE_TITLES.get(str(mode or "").strip().lower(), BOOT_MODE_TITLES[MODE_STRICT])


def translate_message(locale: str | None, text: str) -> str:
    translated = translate(locale, text)
    if translated != text:
        return translated

    disabled_match = re.fullmatch(r"Network is disabled by boot mode \(([^)]+)\)\.", text)
    if disabled_match is not None:
        mode = boot_mode_title(disabled_match.group(1))
        return translate(locale, "Network is disabled by boot mode ({mode}).", mode=translate(locale, mode))

    gdm_start_match = re.fullmatch(r"GDM could not start the live session: (.+)", text)
    if gdm_start_match is not None:
        return translate(locale, "GDM could not start the live session: {error}", error=gdm_start_match.group(1))

    timed_login_match = re.fullmatch(
        r"Unexpected timed login request for (.+) in (\d+) seconds while NM-OS welcome flow is active\.",
        text,
    )
    if timed_login_match is not None:
        return translate(
            locale,
            "Unexpected timed login request for {user_name} in {seconds} seconds while NM-OS welcome flow is active.",
            user_name=timed_login_match.group(1),
            seconds=timed_login_match.group(2),
        )

    return text
