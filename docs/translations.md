# Translations

NM-OS uses English as its source language.

Spanish is the first additional UI translation, and more languages are welcome.

At the moment, translation support is focused on:

- the setup assistant UI
- setup-assistant status messages
- desktop entry labels

Build scripts and most documentation are still handled separately.

## How To Add A New Language

1. Add the locale to `LANGUAGE_OPTIONS` in `apps/nmos_common/nmos_common/i18n.py`.
2. Add a new translation table under `TRANSLATIONS` in `apps/nmos_common/nmos_common/i18n.py`.
3. Add the translated desktop entry name to both of these files:
   `config/system-overlay/usr/share/applications/nmos-greeter.desktop`
   `config/system-overlay/usr/share/gdm/greeter/applications/nmos-greeter.desktop`
4. Ensure the locale has all required keys and placeholder-safe strings by running:
   `python3 scripts/check_i18n_quality.py`
5. Update `tests/smoke/verify-greeter-i18n.sh` only if policy expectations changed.
6. Run greeter and i18n smoke checks, then open a PR.

## Contribution Workflow (PR Checklist)

1. Add/modify user-facing source strings first in English.
2. Add matching translations in `TRANSLATIONS`.
3. Keep placeholder names identical across source and translation.
4. Avoid machine-facing value translation (`tor`, `direct`, `offline`, reason codes, service names).
5. Run:
   `python3 scripts/check_i18n_quality.py`
   `bash tests/smoke/verify-greeter-i18n.sh`
6. Confirm CI smoke workflow passes before merge.

## Rules To Follow

- Keep English as the source language.
- Do not translate machine-facing values such as `tor`, `direct`, or `offline`.
- Do not translate machine-facing reason codes such as `already_exists` or `no_space`.
- Translate only user-facing strings.
- If you add a new user-facing string in the setup assistant, add it to the translation table at the same time.
- Keep string placeholders consistent (for example `{minutes}` must stay `{minutes}` in every locale).
- Keep files UTF-8 and avoid mojibake artifacts in committed text.

## Example

If you wanted to add Italian support, the high-level change would look like this:

```python
LANGUAGE_OPTIONS = (
    ("en_US.UTF-8", "English"),
    ("es_ES.UTF-8", "Español"),
    ("it_IT.UTF-8", "Italiano"),
)

TRANSLATIONS = {
    "es": {
        ...
    },
    "it": {
        "Language": "Lingua",
        "Apply settings": "Applica impostazioni",
    },
}
```

Then add:

```ini
Name[it]=Assistente di configurazione NM-OS
```

to both greeter desktop entry files.

## Notes

- It is completely fine to open a partial translation PR.
- If a string is missing, NM-OS falls back to English.
- Small fixes to wording are just as helpful as full new language packs.
