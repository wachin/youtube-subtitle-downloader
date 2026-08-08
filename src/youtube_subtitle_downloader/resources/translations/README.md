# Translations (Qt Linguist)

The primary language of the application is **English**. A complete **Spanish**
translation is bundled (`youtube_subtitle_downloader_es.qm`) and can be
enabled from **Settings → General → Language**; it applies immediately,
without restarting.

## Files

| File | Purpose |
|---|---|
| `youtube_subtitle_downloader_es.ts` | Qt Linguist source catalog (edit this to translate) |
| `youtube_subtitle_downloader_es.qm` | Compiled catalog, loaded at runtime |

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
   `src/youtube_subtitle_downloader/i18n/__init__.py`.
2. Generate and translate a new `.ts` (e.g. `youtube_subtitle_downloader_pt.ts`).
3. Compile it to `.qm` and ship it in this folder.
