from __future__ import annotations

import re

from nmos_common.boot_mode import MODE_COMPAT, MODE_FLEXIBLE, MODE_OFFLINE, MODE_RECOVERY, MODE_STRICT


DEFAULT_UI_LOCALE = "en_US.UTF-8"
LANGUAGE_OPTIONS = (
    (DEFAULT_UI_LOCALE, "English"),
    ("es_ES.UTF-8", "Español"),
    ("tr_TR.UTF-8", "Türkçe"),
    ("de_DE.UTF-8", "Deutsch"),
    ("fr_FR.UTF-8", "Français"),
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
        "Prepare your session before entering the desktop.": "Prepara tu sesión antes de entrar al escritorio.",
        "Language": "Idioma",
        "Choose the session language.": "Elige el idioma de la sesión.",
        "Keyboard": "Teclado",
        "Choose the keyboard layout.": "Elige la distribución del teclado.",
        "Network": "Red",
        "Persistence": "Persistencia",
        "Refresh network status": "Actualizar estado de la red",
        "Continue to desktop while network stays blocked": "Continuar al escritorio mientras la red sigue bloqueada",
        "Create": "Crear",
        "Unlock": "Desbloquear",
        "Lock": "Bloquear",
        "Repair": "Reparar",
        "Back": "Atrás",
        "Next": "Siguiente",
        "Finish": "Finalizar",
        "Strict": "Estricto",
        "Flexible": "Flexible",
        "Offline": "Sin conexión",
        "Recovery": "Recuperación",
        "Hardware Compatibility": "Compatibilidad de hardware",
        "Tor-first with a more relaxed onboarding flow.": "Tor primero con un flujo de inicio más flexible.",
        "Networking is intentionally disabled for this session.": "La red está desactivada intencionalmente para esta sesión.",
        "Recovery-first session with networking intentionally disabled.": "Sesión centrada en recuperación con la red desactivada intencionalmente.",
        "Compatibility boot options are enabled while keeping strict network policy.": "Las opciones de compatibilidad están activadas mientras se mantiene una política de red estricta.",
        "Tor-first strict profile is active.": "El perfil estricto con Tor primero está activo.",
        "Mode: {mode} - {description}": "Modo: {mode} - {description}",
        "Waiting for Tor": "Esperando a Tor",
        "Tor is ready": "Tor está listo",
        "Waiting for Tor bootstrap": "Esperando el arranque de Tor",
        "Waiting for Tor control": "Esperando el control de Tor",
        "Preparing network policy": "Preparando la política de red",
        "Network bootstrap failed": "Falló el arranque de la red",
        "Unable to read network status": "No se pudo leer el estado de la red",
        "invalid status payload": "la carga del estado no es válida",
        "Network is disabled by boot mode ({mode}).": "La red está desactivada por el modo de arranque ({mode}).",
        "Network is intentionally disabled for this boot mode.": "La red está desactivada intencionalmente para este modo de arranque.",
        "Network status: {error}": "Estado de la red: {error}",
        "Tor connection is ready.": "La conexión de Tor está lista.",
        "Waiting for Tor to become ready.": "Esperando a que Tor esté listo.",
        "Persistence backend unavailable: {error}": "El servicio de persistencia no está disponible: {error}",
        "Persistence error: {error}": "Error de persistencia: {error}",
        "Persistence operation is in progress.": "Hay una operación de persistencia en curso.",
        "Persistence is unlocked and ready.": "La persistencia está desbloqueada y lista.",
        "Persistence exists on {device} and can be unlocked.": "La persistencia existe en {device} y se puede desbloquear.",
        "Persistence cannot be created on {device} because less than 1 GiB of free space remains.": "No se puede crear persistencia en {device} porque queda menos de 1 GiB de espacio libre.",
        "Persistence creation is disabled because NM-OS was not started from a writable USB device.": "La creación de persistencia está desactivada porque NM-OS no se inició desde un USB escribible.",
        "Persistence creation is disabled because the boot USB layout cannot safely accept an appended partition.": "La creación de persistencia está desactivada porque la estructura del USB de arranque no puede aceptar otra partición de forma segura.",
        "Persistence creation is disabled because the boot USB is read-only.": "La creación de persistencia está desactivada porque el USB de arranque es de solo lectura.",
        "Persistence can be created on {device}.": "Se puede crear persistencia en {device}.",
        "Persistence already exists on {device}.": "La persistencia ya existe en {device}.",
        "Persistence state is unavailable.": "El estado de la persistencia no está disponible.",
        "the boot USB": "el USB de arranque",
        "Unable to save language selection: {error}": "No se pudo guardar la selección de idioma: {error}",
        "Language will be applied as {language}.": "El idioma se aplicará como {language}.",
        "Unable to save keyboard selection: {error}": "No se pudo guardar la selección del teclado: {error}",
        "Keyboard layout will be applied as {layout}.": "La distribución del teclado se aplicará como {layout}.",
        "This boot mode is intentionally offline.": "Este modo de arranque funciona intencionalmente sin conexión.",
        "You can continue to desktop now, but network traffic stays blocked until Tor is ready.": "Ya puedes continuar al escritorio, pero el tráfico de red seguirá bloqueado hasta que Tor esté listo.",
        "Continue without network is disabled. Wait for Tor readiness to proceed.": "Continuar sin red está desactivado. Espera a que Tor esté listo para continuar.",
        "Persistence {action} is still running. Please wait.": "La acción de persistencia {action} sigue en curso. Espera por favor.",
        "Persistence status is refreshing. Please wait.": "Se está actualizando el estado de la persistencia. Espera por favor.",
        "Persistence {action} is in progress...": "La acción de persistencia {action} está en curso...",
        "Starting persistence {action}...": "Iniciando la acción de persistencia {action}...",
        "Persistence {action} failed: {error}": "La acción de persistencia {action} falló: {error}",
        "Persistence {action} request completed.": "La acción de persistencia {action} se completó.",
        "Session is not ready yet.": "La sesión todavía no está lista.",
        "Failed to save greeter state: {error}": "No se pudo guardar el estado de la bienvenida: {error}",
        "GDM session control is unavailable: {error}": "El control de sesión de GDM no está disponible: {error}",
        "Greeter state saved, but GDM session control is unavailable.": "Se guardó el estado de la bienvenida, pero el control de sesión de GDM no está disponible.",
        "Starting the live session...": "Iniciando la sesión en vivo...",
        "Failed to start the live session: {error}": "No se pudo iniciar la sesión en vivo: {error}",
        "Live session start timed out. Login flow reset failed: {error}": "Se agotó el tiempo para iniciar la sesión en vivo. No se pudo reiniciar el flujo de acceso: {error}",
        "Live session start timed out. Login flow was reset.": "Se agotó el tiempo para iniciar la sesión en vivo. El flujo de acceso se reinició.",
        "Live session start failed: {problem}": "No se pudo iniciar la sesión en vivo: {problem}",
        "GDM stopped the live-session login conversation.": "GDM detuvo la conversación de acceso de la sesión en vivo.",
        "GDM reset the live-session login flow.": "GDM reinició el flujo de acceso de la sesión en vivo.",
        "GDM could not start the live session: {error}": "GDM no pudo iniciar la sesión en vivo: {error}",
        "Unexpected timed login request for {user_name} in {seconds} seconds while NM-OS welcome flow is active.": "Solicitud inesperada de acceso temporizado para {user_name} en {seconds} segundos mientras el flujo de bienvenida de NM-OS está activo.",
        "live username is missing": "falta el nombre de usuario de la sesión en vivo",
        "live password is missing": "falta la contraseña de la sesión en vivo",
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
