use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, mpsc};
use std::thread;
use std::time::{Duration, Instant};

use rusqlite::{Connection, Row};
use serde_json::{json, Value};

use super::problem::{CaseResult, JudgeResult, LoadedProblem, TestCase};
use super::ddl_verify::append_verify_sql;
use super::mysql_compat::adapt_mysql_sql;
use super::sql_adapt::adapt_user_sql_for_case;
use super::sql_split::split_sql;
use thiserror::Error;

const MAX_RESULT_ROWS: usize = 10_000;
const JUDGE_TIMEOUT: Duration = Duration::from_secs(10);

#[derive(Debug, Error)]
pub enum JudgeError {
    #[error("SQL 执行错误: {0}")]
    Sql(String),
    #[error("未产生查询结果，请提交 SELECT 语句")]
    NoResult,
    #[error("结果行数超过上限 {0}")]
    TooManyRows(usize),
    #[error("{0}")]
    Forbidden(String),
    #[error("已取消")]
    Cancelled,
}

struct CaseFailure {
    message: String,
    expected_columns: Option<Vec<String>>,
    expected_rows: Option<Vec<Vec<Value>>>,
    actual_columns: Option<Vec<String>>,
    actual_rows: Option<Vec<Vec<Value>>>,
}

pub fn judge(
    problem: &LoadedProblem,
    user_sql: &str,
    cancel: Option<Arc<AtomicBool>>,
) -> JudgeResult {
    let start = Instant::now();
    let mut case_results = Vec::new();
    let mut all_passed = true;

    let baseline_ref = problem
        .cases
        .first()
        .and_then(|c| c.reference_sql.as_deref())
        .filter(|s| !s.trim().is_empty());

    for case in &problem.cases {
        if is_cancelled(cancel.as_deref(), None) {
            return JudgeResult {
                accepted: false,
                message: "已取消".to_string(),
                cases: case_results,
                duration_ms: start.elapsed().as_millis() as u64,
            };
        }
        let case_sql = adapt_user_sql_for_case(
            user_sql,
            baseline_ref,
            case.reference_sql.as_deref(),
        );
        let result = run_case(
            &problem.meta.id,
            &problem.schema_sql,
            case,
            &case_sql,
            cancel.clone(),
        );
        if !result.passed && result.message == "已取消" {
            case_results.push(result);
            return JudgeResult {
                accepted: false,
                message: "已取消".to_string(),
                cases: case_results,
                duration_ms: start.elapsed().as_millis() as u64,
            };
        }
        if !result.passed {
            all_passed = false;
        }
        case_results.push(result);
    }

    let duration_ms = start.elapsed().as_millis() as u64;
    JudgeResult {
        accepted: all_passed,
        message: if all_passed {
            "Accepted".to_string()
        } else {
            "Wrong Answer".to_string()
        },
        cases: case_results,
        duration_ms,
    }
}

fn is_cancelled(global: Option<&AtomicBool>, local: Option<&AtomicBool>) -> bool {
    global.is_some_and(|flag| flag.load(Ordering::Relaxed))
        || local.is_some_and(|flag| flag.load(Ordering::Relaxed))
}

fn run_case(
    problem_id: &str,
    problem_schema: &str,
    case: &TestCase,
    user_sql: &str,
    global_cancel: Option<Arc<AtomicBool>>,
) -> CaseResult {
    let case_id = case.id.clone();
    let expected_cols = case.expected_columns.clone();
    let expected_rows = case.expected_rows.clone();
    let schema_sql = problem_schema.to_string();
    let case = case.clone();
    let user_sql = user_sql.to_string();
    let case_abort = Arc::new(AtomicBool::new(false));

    let (tx, rx) = mpsc::channel();
    let worker_global = global_cancel.clone();
    let worker_abort = case_abort.clone();
    let problem_id = problem_id.to_string();
    thread::spawn(move || {
        let result = evaluate_case(
            &problem_id,
            &schema_sql,
            &case,
            &user_sql,
            worker_global.as_deref(),
            Some(worker_abort.as_ref()),
        );
        let _ = tx.send(result);
    });

    match rx.recv_timeout(JUDGE_TIMEOUT) {
        Ok(Ok((actual_columns, actual_rows))) => CaseResult {
            case_id,
            passed: true,
            message: "通过".to_string(),
            expected_columns: Some(expected_cols),
            expected_rows: Some(expected_rows),
            actual_columns: Some(actual_columns),
            actual_rows: Some(actual_rows),
        },
        Ok(Err(failure)) => CaseResult {
            case_id,
            passed: false,
            message: failure.message,
            expected_columns: failure
                .expected_columns
                .or_else(|| Some(expected_cols)),
            expected_rows: failure.expected_rows.or_else(|| Some(expected_rows)),
            actual_columns: failure.actual_columns,
            actual_rows: failure.actual_rows,
        },
        Err(mpsc::RecvTimeoutError::Timeout) => {
            case_abort.store(true, Ordering::Relaxed);
            CaseResult {
                case_id,
                passed: false,
                message: format!("判题超时（{}s）", JUDGE_TIMEOUT.as_secs()),
                expected_columns: Some(expected_cols),
                expected_rows: Some(expected_rows),
                actual_columns: None,
                actual_rows: None,
            }
        }
        Err(mpsc::RecvTimeoutError::Disconnected) => CaseResult {
            case_id,
            passed: false,
            message: "判题线程异常退出".to_string(),
            expected_columns: Some(expected_cols),
            expected_rows: Some(expected_rows),
            actual_columns: None,
            actual_rows: None,
        },
    }
}

fn evaluate_case(
    problem_id: &str,
    problem_schema: &str,
    case: &TestCase,
    user_sql: &str,
    global_cancel: Option<&AtomicBool>,
    local_cancel: Option<&AtomicBool>,
) -> Result<(Vec<String>, Vec<Vec<Value>>), CaseFailure> {
    if is_cancelled(global_cancel, local_cancel) {
        return Err(cancelled_failure());
    }

    let conn = Connection::open_in_memory().map_err(|e| CaseFailure {
        message: e.to_string(),
        expected_columns: None,
        expected_rows: None,
        actual_columns: None,
        actual_rows: None,
    })?;

    if let Some(case_schema) = case.schema.as_deref().filter(|s| !s.trim().is_empty()) {
        execute_script(&conn, case_schema, global_cancel, local_cancel).map_err(case_error)?;
    } else {
        execute_script(&conn, problem_schema, global_cancel, local_cancel).map_err(case_error)?;
        if !case.seed.trim().is_empty() {
            execute_script(&conn, &case.seed, global_cancel, local_cancel).map_err(case_error)?;
        }
    }

    if is_cancelled(global_cancel, local_cancel) {
        return Err(cancelled_failure());
    }

    let prepared_sql = append_verify_sql(problem_id, case, problem_schema, user_sql);

    let (actual_columns, actual_rows) = execute_user_query(
        &conn,
        &prepared_sql,
        global_cancel,
        local_cancel,
    )
    .map_err(|e| CaseFailure {
            message: match &e {
                JudgeError::Sql(msg) => msg.clone(),
                JudgeError::NoResult => {
                    "未产生查询结果。DML 题目请在更新/插入后追加 SELECT 验证语句。".to_string()
                }
                JudgeError::TooManyRows(max) => format!("结果行数超过上限 {max}"),
                JudgeError::Forbidden(msg) => msg.clone(),
                JudgeError::Cancelled => "已取消".to_string(),
            },
            expected_columns: None,
            expected_rows: None,
            actual_columns: None,
            actual_rows: None,
        })?;

    if case.expected_rows.is_empty() {
        if actual_rows.is_empty() {
            return Ok((actual_columns, actual_rows));
        }
        return Err(CaseFailure {
            message: format!("期望空结果，实际 {} 行", actual_rows.len()),
            expected_columns: Some(case.expected_columns.clone()),
            expected_rows: Some(case.expected_rows.clone()),
            actual_columns: Some(actual_columns),
            actual_rows: Some(actual_rows),
        });
    }

    if !columns_match(&actual_columns, &case.expected_columns) {
        return Err(CaseFailure {
            message: format!(
                "列不匹配，期望 {:?}，实际 {:?}",
                case.expected_columns, actual_columns
            ),
            expected_columns: Some(case.expected_columns.clone()),
            expected_rows: Some(case.expected_rows.clone()),
            actual_columns: Some(actual_columns.clone()),
            actual_rows: Some(actual_rows.clone()),
        });
    }

    if !rows_match(&actual_rows, &case.expected_rows) {
        return Err(CaseFailure {
            message: format!(
                "结果不匹配，期望 {} 行，实际 {} 行",
                case.expected_rows.len(),
                actual_rows.len()
            ),
            expected_columns: Some(case.expected_columns.clone()),
            expected_rows: Some(case.expected_rows.clone()),
            actual_columns: Some(actual_columns),
            actual_rows: Some(actual_rows),
        });
    }

    Ok((actual_columns, actual_rows))
}

fn cancelled_failure() -> CaseFailure {
    CaseFailure {
        message: "已取消".to_string(),
        expected_columns: None,
        expected_rows: None,
        actual_columns: None,
        actual_rows: None,
    }
}

fn case_error(err: JudgeError) -> CaseFailure {
    CaseFailure {
        message: match err {
            JudgeError::Sql(msg) => msg,
            JudgeError::NoResult => "未产生查询结果".to_string(),
            JudgeError::TooManyRows(max) => format!("结果行数超过上限 {max}"),
            JudgeError::Forbidden(msg) => msg,
            JudgeError::Cancelled => "已取消".to_string(),
        },
        expected_columns: None,
        expected_rows: None,
        actual_columns: None,
        actual_rows: None,
    }
}

fn forbidden_reason(sql: &str) -> Option<String> {
    let upper = sql.trim_start().to_ascii_uppercase();
    if upper.starts_with("ATTACH") {
        return Some("不允许 ATTACH DATABASE".to_string());
    }
    if upper.starts_with("DETACH") {
        return Some("不允许 DETACH DATABASE".to_string());
    }
    if upper.starts_with("PRAGMA") {
        return Some("不允许 PRAGMA".to_string());
    }
    if upper.contains("READFILE(") {
        return Some("不允许 readfile()".to_string());
    }
    None
}

fn execute_script(
    conn: &Connection,
    script: &str,
    global_cancel: Option<&AtomicBool>,
    local_cancel: Option<&AtomicBool>,
) -> Result<(), JudgeError> {
    let adapted = adapt_mysql_sql(script);
    for stmt in split_sql(&adapted) {
        if is_cancelled(global_cancel, local_cancel) {
            return Err(JudgeError::Cancelled);
        }
        if stmt.is_empty() {
            continue;
        }
        if let Some(reason) = forbidden_reason(&stmt) {
            return Err(JudgeError::Forbidden(reason));
        }
        conn.execute_batch(&stmt)
            .map_err(|e| JudgeError::Sql(format!("{e} (语句: {stmt})")))?;
    }
    Ok(())
}

fn normalize_user_sql(sql: &str) -> String {
    sql.replace("\r\n", "\n").trim().to_string()
}

fn execute_user_query(
    conn: &Connection,
    user_sql: &str,
    global_cancel: Option<&AtomicBool>,
    local_cancel: Option<&AtomicBool>,
) -> Result<(Vec<String>, Vec<Vec<Value>>), JudgeError> {
    let user_sql = normalize_user_sql(user_sql);
    let adapted = adapt_mysql_sql(&user_sql);
    let statements: Vec<String> = split_sql(&adapted).into_iter().filter(|s| !s.is_empty()).collect();
    if statements.is_empty() {
        return Err(JudgeError::NoResult);
    }

    let mut last_result: Option<(Vec<String>, Vec<Vec<Value>>)> = None;

    for stmt in statements {
        if is_cancelled(global_cancel, local_cancel) {
            return Err(JudgeError::Cancelled);
        }
        if let Some(reason) = forbidden_reason(&stmt) {
            return Err(JudgeError::Forbidden(reason));
        }
        let trimmed = stmt.trim_start();
        if is_select_like(trimmed) {
            last_result = Some(read_query(
                conn,
                &stmt,
                global_cancel,
                local_cancel,
            )?);
        } else {
            conn.execute_batch(&stmt)
                .map_err(|e| JudgeError::Sql(e.to_string()))?;
        }
    }

    last_result.ok_or(JudgeError::NoResult)
}

fn read_query(
    conn: &Connection,
    sql: &str,
    global_cancel: Option<&AtomicBool>,
    local_cancel: Option<&AtomicBool>,
) -> Result<(Vec<String>, Vec<Vec<Value>>), JudgeError> {
    let mut stmt = conn
        .prepare(sql)
        .map_err(|e| JudgeError::Sql(e.to_string()))?;
    let columns: Vec<String> = stmt
        .column_names()
        .into_iter()
        .map(|s| s.to_string())
        .collect();
    let mut rows = Vec::new();
    let mut query = stmt
        .query([])
        .map_err(|e| JudgeError::Sql(e.to_string()))?;
    while let Some(row) = query.next().map_err(|e| JudgeError::Sql(e.to_string()))? {
        if is_cancelled(global_cancel, local_cancel) {
            return Err(JudgeError::Cancelled);
        }
        rows.push(row_to_values(row)?);
        if rows.len() > MAX_RESULT_ROWS {
            return Err(JudgeError::TooManyRows(MAX_RESULT_ROWS));
        }
    }
    Ok((columns, rows))
}

fn row_to_values(row: &Row<'_>) -> Result<Vec<Value>, JudgeError> {
    let count = row.as_ref().column_count();
    let mut values = Vec::with_capacity(count);
    for i in 0..count {
        values.push(read_value(row, i)?);
    }
    Ok(values)
}

fn read_value(row: &Row<'_>, idx: usize) -> Result<Value, JudgeError> {
    let value: rusqlite::types::Value = row.get(idx).map_err(|e| JudgeError::Sql(e.to_string()))?;
    Ok(match value {
        rusqlite::types::Value::Null => Value::Null,
        rusqlite::types::Value::Integer(v) => json!(v),
        rusqlite::types::Value::Real(v) => json!(v),
        rusqlite::types::Value::Text(v) => Value::String(v),
        rusqlite::types::Value::Blob(v) => Value::String(format!("<blob {} bytes>", v.len())),
    })
}

fn columns_match(actual: &[String], expected: &[String]) -> bool {
    if actual.len() != expected.len() {
        return false;
    }
    actual
        .iter()
        .zip(expected.iter())
        .all(|(a, e)| a.eq_ignore_ascii_case(e))
}

fn rows_match(actual: &[Vec<Value>], expected: &[Vec<Value>]) -> bool {
    if actual.len() != expected.len() {
        return false;
    }
    actual
        .iter()
        .zip(expected.iter())
        .all(|(a, e)| row_values_match(a, e))
}

fn row_values_match(actual: &[Value], expected: &[Value]) -> bool {
    if actual.len() != expected.len() {
        return false;
    }
    actual
        .iter()
        .zip(expected.iter())
        .all(|(a, e)| values_equal(a, e))
}

fn values_equal(actual: &Value, expected: &Value) -> bool {
    match (actual, expected) {
        (Value::Null, Value::Null) => true,
        (Value::String(a), Value::String(e)) => a.trim() == e.trim(),
        (Value::Number(a), Value::Number(e)) => {
            if let (Some(aa), Some(ee)) = (a.as_f64(), e.as_f64()) {
                (aa - ee).abs() < 1e-9
            } else {
                a == e
            }
        }
        (Value::String(a), Value::Number(e)) => string_number_equal(a, e),
        (Value::Number(a), Value::String(e)) => string_number_equal(e, a),
        _ => actual == expected,
    }
}

fn string_number_equal(text: &str, number: &serde_json::Number) -> bool {
    if let Ok(parsed) = text.trim().parse::<f64>() {
        if let Some(expected) = number.as_f64() {
            return (parsed - expected).abs() < 1e-9;
        }
    }
    false
}

fn is_select_like(sql: &str) -> bool {
    let upper = sql.to_ascii_uppercase();
    upper.starts_with("SELECT") || upper.starts_with("WITH") || upper.starts_with("EXPLAIN")
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::core::problem::{ProblemMeta, TestCase};

    fn sample_problem() -> LoadedProblem {
        LoadedProblem {
            meta: ProblemMeta {
                id: "demo".into(),
                title: "demo".into(),
                difficulty: "easy".into(),
                tags: vec![],
            },
            description: String::new(),
            schema_sql: "CREATE TABLE t(id INTEGER, name TEXT);".into(),
            solution_sql: None,
            solution_explanation: None,
            cases: vec![TestCase {
                id: "1".into(),
                seed: "INSERT INTO t VALUES (1, 'Alice');".into(),
                schema: None,
                expected_columns: vec!["id".into(), "name".into()],
                expected_rows: vec![vec![json!(1), json!("Alice")]],
                reference_sql: None,
            }],
        }
    }

    #[test]
    fn accepts_correct_select() {
        let result = judge(&sample_problem(), "SELECT id, name FROM t;", None);
        assert!(result.accepted);
    }

    #[test]
    fn rejects_wrong_answer() {
        let result = judge(&sample_problem(), "SELECT name, id FROM t;", None);
        assert!(!result.accepted);
    }

    #[test]
    fn rejects_attach() {
        let result = judge(
            &sample_problem(),
            "ATTACH DATABASE '/tmp/x.db' AS x; SELECT 1;",
            None,
        );
        assert!(!result.accepted);
        assert!(result.cases[0].message.contains("ATTACH"));
    }

    #[test]
    fn accepts_multiline_select() {
        let result = judge(
            &sample_problem(),
            "SELECT id,\n  name\nFROM t",
            None,
        );
        assert!(result.accepted);
    }

    #[test]
    fn accepts_multiline_select_without_semicolon() {
        let result = judge(
            &sample_problem(),
            "select id,\n  name\nfrom t",
            None,
        );
        assert!(result.accepted);
    }

    #[test]
    fn accepts_wrapped_department_query_all_cases() {
        let problem = LoadedProblem {
            meta: ProblemMeta {
                id: "0001".into(),
                title: "select where".into(),
                difficulty: "easy".into(),
                tags: vec![],
            },
            description: String::new(),
            schema_sql: "CREATE TABLE employees(id INTEGER, name TEXT, dept TEXT, salary REAL);"
                .into(),
            solution_sql: None,
            solution_explanation: None,
            cases: vec![
                TestCase {
                    id: "1".into(),
                    seed: "INSERT INTO employees VALUES (1,'张三','技术部',15000),(2,'李四','技术部',20000),(5,'钱七','技术部',20000);"
                        .into(),
                    schema: None,
                    expected_columns: vec!["name".into(), "salary".into()],
                    expected_rows: vec![
                        vec![json!("李四"), json!(20000.0)],
                        vec![json!("钱七"), json!(20000.0)],
                        vec![json!("张三"), json!(15000.0)],
                    ],
                    reference_sql: Some(
                        "SELECT name, salary FROM employees WHERE dept = '技术部' ORDER BY salary DESC;"
                            .into(),
                    ),
                },
                TestCase {
                    id: "2".into(),
                    seed: String::new(),
                    schema: Some(
                        "CREATE TABLE employees(id INTEGER,name TEXT,dept TEXT,salary REAL);\
                         INSERT INTO employees VALUES (3,'王五','市场部',12000),(4,'赵六','市场部',18000);"
                            .into(),
                    ),
                    expected_columns: vec!["name".into(), "salary".into()],
                    expected_rows: vec![
                        vec![json!("赵六"), json!(18000.0)],
                        vec![json!("王五"), json!(12000.0)],
                    ],
                    reference_sql: Some(
                        "SELECT name, salary FROM employees WHERE dept = '市场部' ORDER BY salary DESC;"
                            .into(),
                    ),
                },
                TestCase {
                    id: "3".into(),
                    seed: String::new(),
                    schema: Some(
                        "CREATE TABLE employees(id INTEGER,name TEXT,dept TEXT,salary REAL);\
                         INSERT INTO employees VALUES (1,'张三','技术部',15000);"
                            .into(),
                    ),
                    expected_columns: vec!["name".into(), "salary".into()],
                    expected_rows: vec![],
                    reference_sql: Some(
                        "SELECT name, salary FROM employees WHERE dept = '财务部' ORDER BY salary DESC;"
                            .into(),
                    ),
                },
            ],
        };
        let sql = "SELECT name, salary from employees\nwhere dept='技术部'\nORDER BY salary DESC";
        let result = judge(&problem, sql, None);
        assert!(result.accepted, "{:?}", result.cases);
    }

    #[test]
    fn accepts_wrapped_department_query() {
        let problem = LoadedProblem {
            meta: ProblemMeta {
                id: "0001".into(),
                title: "select where".into(),
                difficulty: "easy".into(),
                tags: vec![],
            },
            description: String::new(),
            schema_sql: "CREATE TABLE employees(id INTEGER, name TEXT, dept TEXT, salary REAL);"
                .into(),
            solution_sql: None,
            solution_explanation: None,
            cases: vec![TestCase {
                id: "1".into(),
                seed: "INSERT INTO employees VALUES (1,'张三','技术部',15000),(2,'李四','技术部',20000);"
                    .into(),
                schema: None,
                expected_columns: vec!["name".into(), "salary".into()],
                expected_rows: vec![
                    vec![json!("李四"), json!(20000.0)],
                    vec![json!("张三"), json!(15000.0)],
                ],
                reference_sql: None,
            }],
        };
        let sql = "SELECT name, salary from employees\nwhere dept='技术部'\nORDER BY salary DESC";
        let result = judge(&problem, sql, None);
        assert!(result.accepted, "{}", result.message);
    }

    #[test]
    fn respects_cancel_flag() {
        let cancel = Arc::new(AtomicBool::new(true));
        let result = judge(&sample_problem(), "SELECT id, name FROM t;", Some(cancel));
        assert_eq!(result.message, "已取消");
        assert!(result.cases.is_empty());
    }
}
