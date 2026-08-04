use std::collections::HashSet;
use std::path::PathBuf;

use rusqlite::{params, Connection};
use tauri::{AppHandle, Manager};

use super::bank::ProblemBank;
use super::problem::{AppSettings, BankInspectResult, BankStatus, JudgeResult, ListProblemsResult, LoadedProblem, PracticeStats, SubmissionRecord};
use super::judge;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum StorageError {
    #[error("数据库错误: {0}")]
    Db(#[from] rusqlite::Error),
    #[error("JSON 错误: {0}")]
    Json(#[from] serde_json::Error),
    #[error("IO 错误: {0}")]
    Io(#[from] std::io::Error),
    #[error("{0}")]
    Bank(#[from] super::bank::BankError),
    #[error("{0}")]
    Invalid(String),
}

pub struct Storage {
    conn: Connection,
}

impl Storage {
    pub fn open(app: &AppHandle) -> Result<Self, StorageError> {
        let dir = app
            .path()
            .app_data_dir()
            .expect("app data dir");
        std::fs::create_dir_all(&dir)?;
        let db_path = dir.join("sql-oj.db");
        let conn = Connection::open(db_path)?;
        conn.execute_batch(
            "
            CREATE TABLE IF NOT EXISTS settings (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS submissions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              problem_id TEXT NOT NULL,
              sql TEXT NOT NULL,
              accepted INTEGER NOT NULL,
              message TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            ",
        )?;
        Ok(Self { conn })
    }

    pub fn get_settings(&self) -> Result<AppSettings, StorageError> {
        let path = self.get_setting("problem_bank_path")?;
        Ok(AppSettings {
            problem_bank_path: path,
        })
    }

    pub fn set_problem_bank_path(&self, path: &str) -> Result<(), StorageError> {
        let trimmed = path.trim();
        if trimmed.is_empty() {
            return Err(StorageError::Invalid("题库路径不能为空".into()));
        }
        let bank_path = PathBuf::from(trimmed);
        let inspect = ProblemBank::inspect(bank_path.as_path());
        if !inspect.valid {
            return Err(StorageError::Invalid(
                inspect
                    .error
                    .unwrap_or_else(|| "题库目录无效".into()),
            ));
        }
        self.set_setting("problem_bank_path", trimmed)
    }

    pub fn inspect_problem_bank(&self, path: &str) -> Result<BankInspectResult, StorageError> {
        let trimmed = path.trim();
        if trimmed.is_empty() {
            return Err(StorageError::Invalid("请先输入或选择题库目录".into()));
        }
        Ok(ProblemBank::inspect(PathBuf::from(trimmed).as_path()))
    }

    pub fn get_bank_status(&self) -> Result<BankStatus, StorageError> {
        let settings = self.get_settings()?;
        match settings.problem_bank_path {
            None => Ok(ProblemBank::status_for_path(PathBuf::new().as_path(), false)),
            Some(path) => Ok(ProblemBank::status_for_path(
                PathBuf::from(&path).as_path(),
                true,
            )),
        }
    }

    pub fn list_problems(&self) -> Result<ListProblemsResult, StorageError> {
        let bank = self.open_bank()?;
        let accepted = self.accepted_problem_ids()?;
        let listed = bank.list()?;
        let mut items = listed.problems;
        for item in &mut items {
            item.accepted = accepted.contains(&item.id);
        }
        Ok(ListProblemsResult {
            problems: items,
            warnings: listed.warnings,
        })
    }

    pub fn get_problem(&self, id: &str) -> Result<super::problem::ProblemDetail, StorageError> {
        let bank = self.open_bank()?;
        let loaded = bank.load(id)?;
        let first = loaded.cases.first();
        Ok(super::problem::ProblemDetail {
            id: loaded.meta.id,
            title: loaded.meta.title,
            difficulty: loaded.meta.difficulty,
            tags: loaded.meta.tags,
            description: loaded.description,
            schema_sql: loaded.schema_sql,
            case_count: loaded.cases.len(),
            solution_sql: loaded.solution_sql,
            solution_explanation: loaded.solution_explanation,
            expected_columns: first
                .map(|c| c.expected_columns.clone())
                .unwrap_or_default(),
            expected_rows: first
                .map(|c| c.expected_rows.clone())
                .unwrap_or_default(),
        })
    }

    pub fn load_for_judge(&self, problem_id: &str) -> Result<LoadedProblem, StorageError> {
        let bank = self.open_bank()?;
        Ok(bank.load(problem_id)?)
    }

    pub fn persist_submission(
        &self,
        problem_id: &str,
        sql: &str,
        result: &JudgeResult,
    ) -> Result<(), StorageError> {
        self.save_submission(problem_id, sql, result)?;
        self.prune_submissions()?;
        Ok(())
    }

    pub fn submit(&self, problem_id: &str, sql: &str) -> Result<JudgeResult, StorageError> {
        let loaded = self.load_for_judge(problem_id)?;
        let result = judge::judge(&loaded, sql, None);
        self.persist_submission(problem_id, sql, &result)?;
        Ok(result)
    }

    pub fn get_submissions(
        &self,
        problem_id: Option<&str>,
    ) -> Result<Vec<SubmissionRecord>, StorageError> {
        let mut records = Vec::new();
        match problem_id {
            Some(id) => {
                let mut stmt = self.conn.prepare(
                    "SELECT id, problem_id, sql, accepted, message, created_at
                     FROM submissions WHERE problem_id = ?1
                     ORDER BY id DESC LIMIT 50",
                )?;
                let rows = stmt.query_map(params![id], map_submission)?;
                for row in rows {
                    records.push(row?);
                }
            }
            None => {
                let mut stmt = self.conn.prepare(
                    "SELECT id, problem_id, sql, accepted, message, created_at
                     FROM submissions
                     ORDER BY id DESC LIMIT 100",
                )?;
                let rows = stmt.query_map([], map_submission)?;
                for row in rows {
                    records.push(row?);
                }
            }
        }
        Ok(records)
    }

    pub fn get_practice_stats(&self) -> Result<PracticeStats, StorageError> {
        use super::problem::DailyActivity;
        use std::collections::HashMap;

        let total_problems = self
            .list_problems()
            .map(|r| r.problems.len() as u32)
            .unwrap_or(0);
        let passed_problems = self.accepted_problem_ids()?.len() as u32;

        let total_submissions: u32 = self
            .conn
            .query_row("SELECT COUNT(*) FROM submissions", [], |row| row.get(0))?;
        let accepted_submissions: u32 = self.conn.query_row(
            "SELECT COUNT(*) FROM submissions WHERE accepted = 1",
            [],
            |row| row.get(0),
        )?;

        let mut daily_map: HashMap<String, DailyActivity> = HashMap::new();

        let mut stmt = self.conn.prepare(
            "SELECT substr(created_at, 1, 10) AS d, COUNT(*) AS cnt
             FROM submissions
             GROUP BY d
             ORDER BY d",
        )?;
        let rows = stmt.query_map([], |row| {
            Ok((row.get::<_, String>(0)?, row.get::<_, u32>(1)?))
        })?;
        for row in rows {
            let (date, submissions) = row?;
            daily_map.insert(
                date.clone(),
                DailyActivity {
                    date,
                    submissions,
                    new_passes: 0,
                },
            );
        }

        let mut stmt = self.conn.prepare(
            "SELECT substr(MIN(created_at), 1, 10) AS d, COUNT(*) AS cnt
             FROM submissions
             WHERE accepted = 1
             GROUP BY problem_id",
        )?;
        let rows = stmt.query_map([], |row| {
            Ok((row.get::<_, String>(0)?, row.get::<_, u32>(1)?))
        })?;
        for row in rows {
            let (date, new_passes) = row?;
            daily_map
                .entry(date.clone())
                .and_modify(|a| a.new_passes += new_passes)
                .or_insert(DailyActivity {
                    date,
                    submissions: 0,
                    new_passes,
                });
        }

        let mut daily: Vec<DailyActivity> = daily_map.into_values().collect();
        daily.sort_by(|a, b| a.date.cmp(&b.date));

        Ok(PracticeStats {
            total_problems,
            passed_problems,
            total_submissions,
            accepted_submissions,
            daily,
        })
    }

    fn open_bank(&self) -> Result<ProblemBank, StorageError> {
        let settings = self.get_settings()?;
        let path = settings
            .problem_bank_path
            .ok_or(super::bank::BankError::PathNotSet)?;
        Ok(ProblemBank::open(PathBuf::from(path).as_path())?)
    }

    fn get_setting(&self, key: &str) -> Result<Option<String>, StorageError> {
        let mut stmt = self
            .conn
            .prepare("SELECT value FROM settings WHERE key = ?1")?;
        let mut rows = stmt.query(params![key])?;
        if let Some(row) = rows.next()? {
            Ok(Some(row.get(0)?))
        } else {
            Ok(None)
        }
    }

    fn set_setting(&self, key: &str, value: &str) -> Result<(), StorageError> {
        self.conn.execute(
            "INSERT INTO settings(key, value) VALUES (?1, ?2)
             ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            params![key, value],
        )?;
        Ok(())
    }

    fn save_submission(
        &self,
        problem_id: &str,
        sql: &str,
        result: &JudgeResult,
    ) -> Result<(), StorageError> {
        let created_at = chrono::Local::now().to_rfc3339();
        self.conn.execute(
            "INSERT INTO submissions(problem_id, sql, accepted, message, created_at)
             VALUES (?1, ?2, ?3, ?4, ?5)",
            params![
                problem_id,
                sql,
                result.accepted as i32,
                result.message,
                created_at
            ],
        )?;
        Ok(())
    }

    fn accepted_problem_ids(&self) -> Result<HashSet<String>, StorageError> {
        let mut stmt = self.conn.prepare(
            "SELECT DISTINCT problem_id FROM submissions WHERE accepted = 1",
        )?;
        let rows = stmt.query_map([], |row| row.get(0))?;
        let mut ids = HashSet::new();
        for row in rows {
            ids.insert(row?);
        }
        Ok(ids)
    }

    fn prune_submissions(&self) -> Result<(), StorageError> {
        const MAX_TOTAL: i64 = 2000;
        const MAX_PER_PROBLEM: i64 = 20;
        self.conn.execute(
            "DELETE FROM submissions WHERE id NOT IN (
                SELECT id FROM (
                    SELECT id FROM submissions
                    ORDER BY id DESC LIMIT ?1
                )
            )",
            params![MAX_TOTAL],
        )?;
        self.conn.execute(
            "DELETE FROM submissions WHERE id IN (
                SELECT s.id FROM submissions s
                WHERE (
                    SELECT COUNT(*) FROM submissions s2
                    WHERE s2.problem_id = s.problem_id AND s2.id >= s.id
                ) > ?1
            )",
            params![MAX_PER_PROBLEM],
        )?;
        Ok(())
    }
}

fn map_submission(row: &rusqlite::Row<'_>) -> rusqlite::Result<SubmissionRecord> {
    Ok(SubmissionRecord {
        id: row.get(0)?,
        problem_id: row.get(1)?,
        sql: row.get(2)?,
        accepted: row.get::<_, i32>(3)? != 0,
        message: row.get(4)?,
        created_at: row.get(5)?,
    })
}
