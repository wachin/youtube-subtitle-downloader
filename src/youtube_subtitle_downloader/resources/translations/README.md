# Translations (Qt Linguist)

The primary language of the application is **English**. Spanish is the first
planned translation.

## Workflow

1. Every user visible string must go through `tr()` (or `QCoreApplication.translate`).
2. Generate/update the source translation file:

   ```bash
   pylupdate6 src/youtube_subtitle_downloader -ts resources/translations/youtube_subtitle_downloader_es.ts
   ```

3. Translate the strings (with `linguist-qt6` or a text editor).
4. Compile to a binary catalog:

   ```bash
   lrelease resources/translations/youtube_subtitle_downloader_es.ts \
     -qm resources/translations/youtube_subtitle_downloader_es.qm
   ```

The `.qm` files are loaded automatically by `youtube_subtitle_downloader/i18n`.
Until `youtube_subtitle_downloader_es.qm` exists the application stays in English.
