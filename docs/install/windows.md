# Installing Hired. on Windows

## Download

Grab the latest installer from the [Releases page](https://github.com/bene1106/hired/releases). You'll see two:

- `Hired._<version>_x64-setup.exe` — NSIS installer (recommended).
- `Hired._<version>_x64_en-US.msi` — MSI installer (for managed environments).

Pick whichever matches your IT setup. Both produce the same end state.

## First-launch warning (SmartScreen)

Hired. is **not signed** with an EV certificate. Until that changes, Windows SmartScreen will pop up the first time you run the installer:

> Microsoft Defender SmartScreen prevented an unrecognized app from starting. Running this app might put your PC at risk.

This is expected. SmartScreen flags any binary it hasn't seen before from a publisher it doesn't recognise.

### Workaround

1. In the SmartScreen dialog, click **More info**.
2. A second message appears with a **Run anyway** button — click it.
3. The installer proceeds normally.

After install, launching `Hired.exe` from the Start menu works without further prompts.

### If you don't see "Run anyway"

Some corporate AV tools strip the option entirely. Two options:

- **Right-click the installer → Properties → "Unblock" checkbox at the bottom → Apply**, then run again.
- Or work with your IT admin to allow the binary by hash.

## Where Hired. stores data

| Path                                          | What                                  |
|-----------------------------------------------|---------------------------------------|
| `%USERPROFILE%\.hired\db.sqlite`              | All user data (single source of truth) |
| Credential Manager · target `dev.hired.app`   | API keys (never written to disk)      |

Both are managed by the app; you don't need to touch them. The `Delete everything` button in Settings wipes both.

## Uninstall

1. **Settings → Apps & features → Hired. → Uninstall**.
2. Delete `%USERPROFILE%\.hired\`.
3. Open Credential Manager → Windows Credentials → look for `dev.hired.app` entries and remove them.
