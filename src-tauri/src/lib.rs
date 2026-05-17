use std::sync::Mutex;

use tauri::Manager;
use tauri_plugin_log::{Target, TargetKind};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

// Holds the spawned sidecar so we can reap it on app exit. v0.1.0 never
// kept this handle, so the shell plugin's child (and its PyInstaller-
// extracted grandchild) outlived the app — a stale sidecar kept port
// 8765, and the next launch's sidecar lost the bind race. We keep both
// the kill handle and the raw PID: killing `CommandChild` only reaps the
// process Tauri spawned (the PyInstaller bootloader); on Windows the
// real Python lives in a child of that, so we also taskkill the tree.
struct SidecarProcess {
    child: Mutex<Option<CommandChild>>,
    pid: Mutex<Option<u32>>,
}

// Phase 6: launch the bundled `hired-sidecar` binary on app start. The
// binary is declared as an external binary in tauri.conf.json
// (`bundle.externalBin`); per-platform builds rename it with the right
// target-triple suffix before `tauri build` picks it up. We spawn it
// here on the Tokio runtime that Tauri owns and drain its stdout/stderr
// into the Tauri log (now enabled in release too — see `run()`).
//
// Returns Box<dyn Error> rather than tauri::Result because
// tauri_plugin_shell::Error does not implement From<_> for tauri::Error,
// so `?` can't auto-convert it. A boxed error accepts anything that
// implements std::error::Error, and a sidecar spawn failure at startup
// is fatal anyway — the caller just logs and the app is dead in the
// water without its backend.
fn spawn_sidecar(app: &tauri::AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let sidecar = app.shell().sidecar("hired-sidecar")?;
    let (mut rx, child) = sidecar.spawn()?;

    let pid = child.pid();
    log::info!("hired-sidecar spawned pid={pid}");

    let state = app.state::<SidecarProcess>();
    *state.child.lock().unwrap() = Some(child);
    *state.pid.lock().unwrap() = Some(pid);

    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(bytes) => {
                    log::info!("hired-sidecar: {}", String::from_utf8_lossy(&bytes));
                }
                CommandEvent::Stderr(bytes) => {
                    log::warn!("hired-sidecar: {}", String::from_utf8_lossy(&bytes));
                }
                CommandEvent::Terminated(payload) => {
                    log::error!("hired-sidecar exited: {payload:?}");
                    break;
                }
                _ => {}
            }
        }
    });

    Ok(())
}

// Reap the sidecar tree on app exit. `CommandChild::kill()` only kills
// the process we spawned (the PyInstaller onefile bootloader). On
// Windows the actual uvicorn process is a child of that bootloader and
// would orphan — so we also `taskkill /T` the PID tree. Best-effort:
// every step is allowed to fail without blocking shutdown.
fn kill_sidecar(app: &tauri::AppHandle) {
    let state = app.state::<SidecarProcess>();
    let pid = *state.pid.lock().unwrap();

    if let Some(child) = state.child.lock().unwrap().take() {
        if let Err(err) = child.kill() {
            log::warn!("failed to kill sidecar handle: {err}");
        }
    }

    #[cfg(windows)]
    if let Some(pid) = pid {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        let _ = std::process::Command::new("taskkill")
            .args(["/F", "/T", "/PID", &pid.to_string()])
            .creation_flags(CREATE_NO_WINDOW)
            .status();
        log::info!("taskkill /T issued for sidecar pid={pid}");
    }
    #[cfg(not(windows))]
    let _ = pid;
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    #[allow(unused_mut)]
    let mut builder = tauri::Builder::default();

    // Single-instance (desktop-only) must be registered first so a
    // second launch short-circuits before it spawns its own sidecar
    // (which would lose the port-8765 bind race against the live one).
    // The callback runs in the already-running instance: refocus it.
    #[cfg(desktop)]
    {
        builder = builder.plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.set_focus();
            }
        }));
    }

    builder
        // v0.1.0 registered the log plugin only under
        // `cfg!(debug_assertions)`, so the packaged build had no logging
        // at all — the sidecar lifecycle was a black box in the field.
        // Always register it now: a file in the OS log dir (a windowed
        // app has no console the user can read) plus stdout for dev.
        .plugin(
            tauri_plugin_log::Builder::default()
                .level(log::LevelFilter::Info)
                .target(Target::new(TargetKind::LogDir {
                    file_name: Some("hired".into()),
                }))
                .target(Target::new(TargetKind::Stdout))
                .build(),
        )
        .plugin(tauri_plugin_shell::init())
        .manage(SidecarProcess {
            child: Mutex::new(None),
            pid: Mutex::new(None),
        })
        .setup(|app| {
            // Don't spawn the sidecar in dev mode — the developer is
            // already running `uv run uvicorn ...` against the source
            // tree. Only the bundled production binary needs the
            // sidecar, and gating on `cfg!(debug_assertions)` keeps
            // `pnpm tauri dev` ergonomic.
            #[cfg(not(debug_assertions))]
            {
                if let Err(err) = spawn_sidecar(&app.handle().clone()) {
                    log::error!("failed to spawn hired-sidecar: {err}");
                }
            }
            #[cfg(debug_assertions)]
            {
                let _ = spawn_sidecar; // silence dead-code warning in dev
                let _ = app; // unused in dev; used by spawn_sidecar in release
            }

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while running tauri application")
        .run(|app_handle, event| {
            // Reap the sidecar when the app is on its way out so a stale
            // process can't hold port 8765 into the next launch.
            if let tauri::RunEvent::ExitRequested { .. } | tauri::RunEvent::Exit = event {
                kill_sidecar(app_handle);
            }
        });
}
