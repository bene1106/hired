# Installing Hired. on Linux

## Download

Grab the latest from the [Releases page](https://github.com/bene1106/hired/releases). Two formats:

- `Hired._<version>_amd64.AppImage` — works on most distros, no install needed.
- `Hired._<version>_amd64.deb` — for Debian / Ubuntu.

## AppImage (recommended)

```bash
chmod +x Hired._<version>_amd64.AppImage
./Hired._<version>_amd64.AppImage
```

Optional: drop it under `~/Applications/` and integrate with your launcher via [AppImageLauncher](https://github.com/TheAssassin/AppImageLauncher).

### `libfuse2` requirement

AppImages need FUSE 2 to mount themselves. Most distros have it; Ubuntu 22.04+ does not by default:

```bash
sudo apt install libfuse2
```

If you can't install FUSE, extract and run instead:

```bash
./Hired._<version>_amd64.AppImage --appimage-extract
./squashfs-root/AppRun
```

## `.deb`

```bash
sudo apt install ./Hired._<version>_amd64.deb
```

The package depends on `libwebkit2gtk-4.1-0` and `libgtk-3-0`. On older releases (Ubuntu 22.04, Debian 11) the WebKit version is too old; use the AppImage instead.

## Where Hired. stores data

| Path                                | What                                  |
|-------------------------------------|---------------------------------------|
| `~/.hired/db.sqlite`                | All user data (single source of truth) |
| Secret Service (`gnome-keyring` / `kwallet`) — service `dev.hired.app` | API keys |

If you don't have a Secret Service provider running (headless server, custom WMs), `keyring` will fall back to file-encrypted storage in `~/.local/share/python_keyring/`.

## Uninstall

```bash
# AppImage: just delete the file.
rm Hired._<version>_amd64.AppImage

# .deb:
sudo apt remove hired

# In both cases, also wipe local data:
rm -rf ~/.hired/
```

To remove keychain entries, use `seahorse` (GNOME) or `kwalletmanager` and delete entries scoped to `dev.hired.app`.
