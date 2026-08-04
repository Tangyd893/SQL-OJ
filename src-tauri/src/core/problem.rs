use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProblemMeta {
    pub id: String,
    pub title: String,
    #[serde(default)]
    pub difficulty: String,
    #[serde(default)]
    pub tags: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TestCase {
    pub id: String,
    #[serde(default)]
    pub seed: String,
    #[serde(default)]
    pub schema: Option<String>,
  pub expected_columns: Vec<String>,
  pub expected_rows: Vec<Vec<serde_json::Value>>,
  #[serde(default)]
  pub reference_sql: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CasesFile {
    pub cases: Vec<TestCase>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ListProblemsResult {
    pub problems: Vec<ProblemSummary>,
    pub warnings: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProblemSummary {
    pub id: String,
    pub title: String,
    pub difficulty: String,
    pub tags: Vec<String>,
    #[serde(default)]
    pub accepted: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProblemDetail {
    pub id: String,
    pub title: String,
    pub difficulty: String,
    pub tags: Vec<String>,
    pub description: String,
    pub schema_sql: String,
    pub case_count: usize,
    pub solution_sql: Option<String>,
    pub solution_explanation: Option<String>,
    pub expected_columns: Vec<String>,
    pub expected_rows: Vec<Vec<serde_json::Value>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CaseResult {
    pub case_id: String,
    pub passed: bool,
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub expected_columns: Option<Vec<String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub expected_rows: Option<Vec<Vec<serde_json::Value>>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub actual_columns: Option<Vec<String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub actual_rows: Option<Vec<Vec<serde_json::Value>>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct JudgeResult {
    pub accepted: bool,
    pub message: String,
    pub cases: Vec<CaseResult>,
    pub duration_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SubmissionRecord {
    pub id: i64,
    pub problem_id: String,
    pub sql: String,
    pub accepted: bool,
    pub message: String,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AppSettings {
    pub problem_bank_path: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BankInspectResult {
    pub valid: bool,
    pub path: String,
    pub name: Option<String>,
    pub version: Option<String>,
    pub problem_count: u32,
    pub warnings: Vec<String>,
    pub error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BankStatus {
    pub linked: bool,
    pub path: Option<String>,
    pub path_exists: bool,
    pub name: Option<String>,
    pub version: Option<String>,
    pub problem_count: u32,
    pub warnings: Vec<String>,
    pub error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct DailyActivity {
    pub date: String,
    pub submissions: u32,
    pub new_passes: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct PracticeStats {
    pub total_problems: u32,
    pub passed_problems: u32,
    pub total_submissions: u32,
    pub accepted_submissions: u32,
    pub daily: Vec<DailyActivity>,
}

#[derive(Debug, Clone)]
pub struct LoadedProblem {
    pub meta: ProblemMeta,
    pub description: String,
    pub schema_sql: String,
    pub solution_sql: Option<String>,
    pub solution_explanation: Option<String>,
    pub cases: Vec<TestCase>,
}
