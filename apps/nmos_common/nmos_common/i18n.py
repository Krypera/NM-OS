from __future__ import annotations

import re

DEFAULT_UI_LOCALE = "en_US.UTF-8"
LANGUAGE_OPTIONS = (
    (DEFAULT_UI_LOCALE, "English"),
    ("es_ES.UTF-8", "Español"),
)

LANGUAGE_LABELS = {locale: label for locale, label in LANGUAGE_OPTIONS}

NETWORK_POLICY_TITLES = {
    "tor": "Tor-first",
    "direct": "Direct network",
    "offline": "Offline",
}

TRANSLATIONS = {
    "es": {
        "NM-OS Setup": "Configuración de NM-OS",
        "Review your privacy and desktop settings before login.": "Revisa tus ajustes de privacidad y escritorio antes de iniciar sesión.",
        "Language": "Idioma",
        "Choose the interface language.": "Elige el idioma de la interfaz.",
        "Keyboard": "Teclado",
        "Choose the keyboard layout.": "Elige la distribución del teclado.",
        "Network": "Red",
        "Choose how NM-OS should treat the network.": "Elige cómo debe tratar NM-OS la red.",
        "Network policy": "Política de red",
        "Allow Brave Browser when installed": "Permitir Brave Browser cuando esté instalado",
        "Refresh network status": "Actualizar estado de la red",
        "Encrypted Vault": "Bóveda cifrada",
        "Create or unlock an encrypted vault for sensitive files.": "Crea o desbloquea una bóveda cifrada para archivos sensibles.",
        "Create": "Crear",
        "Unlock": "Desbloquear",
        "Lock": "Bloquear",
        "Repair": "Reparar",
        "Back": "Atrás",
        "Next": "Siguiente",
        "Apply settings": "Aplicar ajustes",
        "Tor-first": "Tor primero",
        "Direct network": "Red directa",
        "Offline": "Sin conexión",
        "Waiting for Tor": "Esperando a Tor",
        "Tor is ready": "Tor está listo",
        "Waiting for Tor bootstrap": "Esperando el arranque de Tor",
        "Waiting for Tor control": "Esperando el control de Tor",
        "Preparing network policy": "Preparando la política de red",
        "Network bootstrap failed": "Falló el arranque de la red",
        "Direct network access is enabled by system settings.": "El acceso directo a la red está habilitado por la configuración del sistema.",
        "Network is disabled by current settings.": "La red está desactivada por la configuración actual.",
        "Unable to read network status": "No se pudo leer el estado de la red",
        "invalid status payload": "la carga del estado no es válida",
        "Network status: {error}": "Estado de la red: {error}",
        "Networking is currently disabled.": "La red está actualmente desactivada.",
        "Direct network access is enabled.": "El acceso directo a la red está habilitado.",
        "Tor connection is ready.": "La conexión Tor está lista.",
        "Waiting for Tor to become ready.": "Esperando a que Tor esté listo.",
        "Unable to save pending settings: {error}": "No se pudieron guardar los ajustes pendientes: {error}",
        "Language will be applied as {language}.": "El idioma se aplicará como {language}.",
        "Keyboard layout will be applied as {layout}.": "La distribución del teclado se aplicará como {layout}.",
        "Network policy will be applied as {policy}.": "La política de red se aplicará como {policy}.",
        "Encrypted vault backend unavailable: {error}": "El servicio de la bóveda cifrada no está disponible: {error}",
        "Encrypted vault error: {error}": "Error de la bóveda cifrada: {error}",
        "Encrypted vault activity is in progress.": "Hay una actividad en curso en la bóveda cifrada.",
        "Encrypted vault is unlocked and ready.": "La bóveda cifrada está desbloqueada y lista.",
        "Encrypted vault exists at {path} and can be unlocked.": "La bóveda cifrada existe en {path} y se puede desbloquear.",
        "Encrypted vault cannot be created because the system disk does not have enough free space.": "No se puede crear la bóveda cifrada porque el disco del sistema no tiene suficiente espacio libre.",
        "Encrypted vault can be created at {path}.": "La bóveda cifrada se puede crear en {path}.",
        "Encrypted vault already exists at {path}.": "La bóveda cifrada ya existe en {path}.",
        "Encrypted vault state is unavailable.": "El estado de la bóveda cifrada no está disponible.",
        "the encrypted vault": "la bóveda cifrada",
        "Encrypted vault action {action} is still running. Please wait.": "La acción {action} de la bóveda cifrada sigue en curso. Espera por favor.",
        "Encrypted vault status is refreshing. Please wait.": "Se está actualizando el estado de la bóveda cifrada. Espera por favor.",
        "Encrypted vault action {action} is in progress...": "La acción {action} de la bóveda cifrada está en curso...",
        "Starting encrypted vault action {action}...": "Iniciando la acción {action} de la bóveda cifrada...",
        "Encrypted vault action {action} failed: {error}": "La acción {action} de la bóveda cifrada falló: {error}",
        "Encrypted vault action {action} completed.": "La acción {action} de la bóveda cifrada se completó.",
        "Encrypted vault activity is still running.": "La actividad de la bóveda cifrada aún continúa.",
        "Failed to save system settings: {error}": "No se pudieron guardar los ajustes del sistema: {error}",
        "Settings saved. Some privacy changes apply on the next boot.": "Los ajustes se guardaron. Algunos cambios de privacidad se aplicarán en el próximo arranque.",
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


def display_network_policy_name(policy: str | None, locale: str | None = None) -> str:
    normalized = str(policy or "").strip().lower()
    title = NETWORK_POLICY_TITLES.get(normalized, NETWORK_POLICY_TITLES["tor"])
    return translate(locale, title)


def translate_message(locale: str | None, text: str) -> str:
    translated = translate(locale, text)
    if translated != text:
        return translated

    network_policy_match = re.fullmatch(r"Direct network access is enabled by system settings\.", text)
    if network_policy_match is not None:
        return translate(locale, "Direct network access is enabled by system settings.")

    disabled_match = re.fullmatch(r"Network is disabled by current settings\.", text)
    if disabled_match is not None:
        return translate(locale, "Network is disabled by current settings.")

    return text
