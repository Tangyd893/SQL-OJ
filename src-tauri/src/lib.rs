mod commands;
mod core;

use std::sync::atomic::AtomicBool;
use std::sync::{Arc, Mutex};
use tauri::Manager;

pub struct AppState {
    pub storage: Mutex<core::storage::Storage>,
    pub judge_cancel: Arc<AtomicBool>,
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            let storage = core::storage::Storage::open(app.handle())?;
            app.manage(AppState {
                storage: Mutex::new(storage),
                judge_cancel: Arc::new(AtomicBool::new(false)),
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::get_settings,
            commands::set_problem_bank_path,
            commands::pick_problem_bank_folder,
            commands::inspect_problem_bank,
            commands::get_bank_status,
            commands::list_problems,
            commands::get_problem,
            commands::submit_solution,
            commands::preview_solution,
            commands::cancel_judge,
            commands::get_submissions,
            commands::get_practice_stats,
            commands::reload_bank,
            commands::window_minimize,
            commands::window_toggle_maximize,
            commands::window_close,
        ])
        .run(tauri::generate_context!())
        .expect("error while running SQL OJ");
}
