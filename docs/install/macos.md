# Installing Hired. on macOS

## Download

Grab the latest `Hired._<version>_aarch64.dmg` from the [Releases page](https://github.com/bene1106/hired/releases). Apple Silicon (M-series) only; Intel Macs are not currently shipped.

## First-launch warning ("can't be opened")

Hired. is **not signed** with an Apple Developer ID. Until that changes, macOS Gatekeeper will block the first launch with one of these messages:

> "Hired." cannot be opened because the developer cannot be verified.

> "Hired." is damaged and can't be opened.

This is expected. The app is fine; macOS just doesn't recognise the (non-existent) signature.

### Workaround

1. Mount the `.dmg` and drag `Hired.` into `/Applications` as usual.
2. **Right-click** (or Control-click) `Hired.app` in `/Applications` → **Open**.
3. The dialog now offers an **Open** button. Click it.
4. macOS remembers your decision; subsequent launches work normally (double-click, Spotlight, Dock).

If macOS only offers a **Cancel** button (newer Sequoia behaviour), the alternative is **System Settings → Privacy & Security → "Hired. was blocked" → Open Anyway**.

### If the "damaged" message persists

Some macOS versions strip the quarantine attribute incorrectly when the DMG hits a non-APFS volume. From a terminal:

```bash
xattr -dr com.apple.quarantine /Applications/Hired.app
```

Then retry the right-click → Open dance.

## Where Hired. stores data

| Path                                    | What                                  |
|-----------------------------------------|---------------------------------------|
| `~/.hired/db.sqlite`                    | All user data (single source of truth) |
| Keychain Access · service `dev.hired.app` | API keys (never written to disk)     |

Both are managed by the app; you don't need to touch them. The `Delete everything` button in Settings wipes both.

## Uninstall

1. Drag `/Applications/Hired.app` to the Trash.
2. Remove `~/.hired/`.
3. Open Keychain Access → search `dev.hired.app` → delete the entry.
