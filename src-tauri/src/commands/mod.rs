use crate::AppState;
use crate::core::problem::{
    AppSettings, BankInspectResult, BankStatus, JudgeResult, ListProblemsResult, PracticeStats,
    ProblemDetail, SubmissionRecord,
};
use crate::core::storage::StorageError;
use std::sync::atomic::Ordering;
use tauri::{AppHandle, State, Window};

#[tauri::command]
pub fn get_settings(state: State<'_, AppState>) -> Result<AppSettings, String> {
    state
        .storage
        .lock()
        .map_err(|_| "lock poisoned".to_string())?
        .get_settings()
        .map_err(map_err)
}

#[tauri::command]
pub fn set_problem_bank_path(state: State<'_, AppState>, path: String) -> Result<(), String> {
    state
        .storage
        .lock()
        .map_err(|_| "lock poisoned".to_string())?
        .set_problem_bank_path(&path)
        .map_err(map_err)
}

#[tauri::command]
pub async fn pick_problem_bank_folder(app: AppHandle) -> Result<Option<String>, String> {
    use tauri_plugin_dialog::DialogExt;

    let (tx, rx) = tokio::sync::oneshot::channel();
    app.dialog()
        .file()
        .set_title("选择题库目录")
        .pick_folder(move |path| {
            let value = path.map(|p| p.to_string());
            let _ = tx.send(value);
        });

    rx.await
        .map_err(|_| "对话框已关闭".to_string())
}

#[tauri::command]
pub fn inspect_problem_bank(state: State<'_, AppState>, path: String) -> Result<BankInspectResult, String> {
    state
        .storage
        .lock()
        .map_err(|_| "lock poisoned".to_string())?
        .inspect_problem_bank(&path)
        .map_err(map_err)
}

#[tauri::command]
pub fn get_bank_status(state: State<'_, AppState>) -> Result<BankStatus, String> {
    state
        .storage
        .lock()
        .map_err(|_| "lock poisoned".to_string())?
        .get_bank_status()
        .map_err(map_err)
}

#[tauri::command]
pub fn list_problems(state: State<'_, AppState>) -> Result<ListProblemsResult, String> {
    state
        .storage
        .lock()
        .map_err(|_| "lock poisoned".to_string())?
        .list_problems()
        .map_err(map_err)
}

#[tauri::command]
pub fn get_problem(state: State<'_, AppState>, id: String) -> Result<ProblemDetail, String> {
    state
        .storage
        .lock()
        .map_err(|_| "lock poisoned".to_string())?
        .get_problem(&id)
        .map_err(map_err)
}

async fn run_judge(
    state: &AppState,
    problem_id: &str,
    sql: &str,
) -> Result<JudgeResult, String> {
    state.judge_cancel.store(false, Ordering::Relaxed);

    let loaded = {
        let storage = state
            .storage
            .lock()
            .map_err(|_| "lock poisoned".to_string())?;
        storage.load_for_judge(problem_id).map_err(map_err)?
    };

    let cancel = state.judge_cancel.clone();
    let sql = sql.to_string();
    tauri::async_runtime::spawn_blocking(move || {
        crate::core::judge::judge(&loaded, &sql, Some(cancel))
    })
    .await
    .map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn submit_solution(
    state: State<'_, AppState>,
    problem_id: String,
    sql: String,
) -> Result<JudgeResult, String> {
    let result = run_judge(&state, &problem_id, &sql).await?;

    if result.message != "已取消" {
        state
            .storage
            .lock()
            .map_err(|_| "lock poisoned".to_string())?
            .persist_submission(&problem_id, &sql, &result)
            .map_err(map_err)?;
    }

    Ok(result)
}

#[tauri::command]
pub async fn preview_solution(
    state: State<'_, AppState>,
    problem_id: String,
    sql: String,
) -> Result<JudgeResult, String> {
    run_judge(&state, &problem_id, &sql).await
}

#[tauri::command]
pub fn cancel_judge(state: State<'_, AppState>) {
    state.judge_cancel.store(true, Ordering::Relaxed);
}

#[tauri::command]
pub fn get_submissions(
    state: State<'_, AppState>,
    problem_id: Option<String>,
) -> Result<Vec<SubmissionRecord>, String> {
    state
        .storage
        .lock()
        .map_err(|_| "lock poisoned".to_string())?
        .get_submissions(problem_id.as_deref())
        .map_err(map_err)
}

#[tauri::command]
pub fn get_practice_stats(state: State<'_, AppState>) -> Result<PracticeStats, String> {
    state
        .storage
        .lock()
        .map_err(|_| "lock poisoned".to_string())?
        .get_practice_stats()
        .map_err(map_err)
}

#[tauri::command]
pub fn reload_bank(state: State<'_, AppState>) -> Result<ListProblemsResult, String> {
    list_problems(state)
}

#[tauri::command]
pub fn window_minimize(window: Window) {
    let _ = window.minimize();
}

#[tauri::command]
pub fn window_toggle_maximize(window: Window) {
    if window.is_maximized().unwrap_or(false) {
        let _ = window.unmaximize();
    } else {
        let _ = window.maximize();
    }
}

#[tauri::command]
pub fn window_close(window: Window) {
    let _ = window.close();
}

fn map_err(err: StorageError) -> String {
    err.to_string()
}
