# Windows build and installer

Build the application folder and the bilingual setup program from the repository root:

```powershell
python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --noconfirm --clean WinIsland.spec
ISCC.exe installer\WinIsland.iss
```

The installer script uses Inno Setup 6.7 or later. It offers English and Turkish, shows a localized introduction and the MIT license page, and adds a checked-by-default option to launch WinIsland when setup finishes. The selected setup language initializes the app language on a fresh install. Existing user settings are preserved on upgrades.

The executable stores settings and task data under `%APPDATA%\WinIsland`; running from source keeps the existing repository-local configuration and task data.
