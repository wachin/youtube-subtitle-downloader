# Translations (Qt Linguist)

The primary language of the application is **English**. Bundled translations
(`.qm` files below) can be enabled from **Settings → General → Language**;
they apply immediately, without restarting.

## Files

| File | Purpose |
|---|---|
| `youtube_subtitle_downloader_<lang>.ts` | Qt Linguist source catalog (edit this to translate) |
| `youtube_subtitle_downloader_<lang>.qm` | Compiled catalog, loaded at runtime |

Bundled languages: `es` (Español), `de` (Deutsch), `fr` (Français),
`ja` (日本語), `ko` (한국어), `pt_BR` (Português do Brasil),
`ru` (Русский), `zh_CN` (简体中文), `zh_TW` (繁體中文).

## Workflow

1. Every user visible string must go through `tr()` (or
   `QCoreApplication.translate`) with **literal** string arguments, so
   `pylupdate6` can extract it.
2. Update the source catalog after code changes:

   ```bash
   pylupdate6 $(find src/youtube_subtitle_downloader -name '*.py') \
     -ts src/youtube_subtitle_downloader/resources/translations/youtube_subtitle_downloader_es.ts
   ```

3. Translate the new strings (with `linguist-qt6` or a text editor).
4. Compile to a binary catalog:

   ```bash
   lrelease src/youtube_subtitle_downloader/resources/translations/youtube_subtitle_downloader_es.ts \
     -qm src/youtube_subtitle_downloader/resources/translations/youtube_subtitle_downloader_es.qm
   ```

The `.qm` file is loaded automatically by `youtube_subtitle_downloader/i18n`
(`install_translator`). If the `.qm` for a language is missing, the
application stays in English.

## Adding a new language

1. Add the code to `AVAILABLE_LANGUAGES` in
   `src/youtube_subtitle_downloader/i18n/__init__.py` **and** to the
   `LANGUAGES` list in `src/youtube_subtitle_downloader/ui/settings_dialog.py`.
2. Generate and translate a new `.ts` (e.g. `youtube_subtitle_downloader_pt.ts`):

   ```bash
   pylupdate6 $(find src/youtube_subtitle_downloader -name '*.py') \
     -ts src/youtube_subtitle_downloader/resources/translations/youtube_subtitle_downloader_pt.ts
   ```

3. Compile it to `.qm` and ship it in this folder:

   ```bash
   lrelease src/youtube_subtitle_downloader/resources/translations/youtube_subtitle_downloader_pt.ts \
     -qm src/youtube_subtitle_downloader/resources/translations/youtube_subtitle_downloader_pt.qm
   ```

4. `system_language()` automatically detects the system locale, so a user
   whose system speaks the new language will get it by default.
