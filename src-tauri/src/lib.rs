use tauri::Manager;
use tauri_plugin_shell::process::CommandEvent;
use tauri_plugin_shell::ShellExt;

// Phase 6: launch the bundled `hired-sidecar` binary on app start. The
// binary is declared as an external binary in tauri.conf.json
// (`bundle.externalBin`); per-platform builds rename it with the right
// target-triple suffix before `tauri build` picks it up. We spawn it
// here on the Tokio runtime that Tauri owns and drain its stdout/stderr
// so the events end up in the Tauri log plugin during development.
fn spawn_sidecar(app: &tauri::AppHandle) -> tauri::Result<()> {
    let sidecar = app.shell().sidecar("hired-sidecar")?;
    let (mut rx, _child) = sidecar.spawn()?;

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
                    log::error!("hired-sidecar exited: {:?}", payload);
                    break;
                }
                _ => {}
            }
        }
    });

    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            // Don't spawn the sidecar in dev mode — the developer is
            // already running `uv run uvicorn ...` against the source
            // tree. Only the bundled production binary needs the
            // sidecar, and shipping `cfg!(debug_assertions)` here keeps
            // `pnpm tauri dev` ergonomic.
            #[cfg(not(debug_assertions))]
            {
                if let Err(err) = spawn_sidecar(&app.handle().clone()) {
                    log::error!("failed to spawn hired-sidecar: {}", err);
                }
            }
            #[cfg(debug_assertions)]
            {
                let _ = spawn_sidecar; // silence dead-code warning in dev
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
