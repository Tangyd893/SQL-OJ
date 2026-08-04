use std::fs;
use std::path::{Path, PathBuf};

use serde::Deserialize;
use walkdir::WalkDir;

use super::problem::{
    BankInspectResult, BankStatus, CasesFile, LoadedProblem, ProblemMeta, ProblemSummary,
    TestCase,
};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum BankError {
    #[error("题库路径未设置")]
    PathNotSet,
    #[error("题库目录不存在: {0}")]
    NotFound(String),
    #[error("读取文件失败: {0}")]
    Io(#[from] std::io::Error),
    #[error("解析 JSON 失败: {0}")]
    Json(#[from] serde_json::Error),
    #[error("题目不存在: {0}")]
    ProblemNotFound(String),
    #[error("{0}")]
    Invalid(String),
}

#[derive(Debug, Deserialize)]
struct Manifest {
    #[allow(dead_code)]
    name: Option<String>,
    #[allow(dead_code)]
    version: Option<String>,
    problems: Option<Vec<String>>,
}

pub struct ProblemBank {
    root: PathBuf,
}

#[derive(Debug, Clone)]
pub struct BankListResult {
    pub problems: Vec<ProblemSummary>,
    pub warnings: Vec<String>,
}

impl ProblemBank {
    pub fn open(path: &Path) -> Result<Self, BankError> {
        if !path.is_dir() {
            return Err(BankError::NotFound(path.display().to_string()));
        }
        Ok(Self {
            root: path.to_path_buf(),
        })
    }

    pub fn inspect(path: &Path) -> BankInspectResult {
        let path_str = path.display().to_string();

        if !path.is_dir() {
            return invalid_inspect(
                path_str.clone(),
                format!("目录不存在: {path_str}"),
            );
        }

        let problems_dir = path.join("problems");
        if !problems_dir.is_dir() {
            return invalid_inspect(
                path_str,
                "未找到 problems/ 子目录。请选择题库根目录（应包含 manifest.json 与 problems/ 文件夹）"
                    .into(),
            );
        }

        let bank = match Self::open(path) {
            Ok(bank) => bank,
            Err(err) => return invalid_inspect(path_str, err.to_string()),
        };

        let (name, version) = bank.manifest_meta();
        let listed = match bank.list() {
            Ok(listed) => listed,
            Err(err) => {
                return BankInspectResult {
                    valid: false,
                    path: path_str,
                    name,
                    version,
                    problem_count: 0,
                    warnings: vec![],
                    error: Some(err.to_string()),
                };
            }
        };

        let count = listed.problems.len() as u32;
        if count == 0 {
            return BankInspectResult {
                valid: false,
                path: path_str,
                name,
                version,
                problem_count: 0,
                warnings: listed.warnings,
                error: Some("未加载到任何题目，请检查 problems/ 下是否有有效题目目录".into()),
            };
        }

        BankInspectResult {
            valid: true,
            path: path_str,
            name,
            version,
            problem_count: count,
            warnings: listed.warnings,
            error: None,
        }
    }

    pub fn status_for_path(path: &Path, linked: bool) -> BankStatus {
        if !linked {
            return BankStatus {
                linked: false,
                path: None,
                path_exists: false,
                name: None,
                version: None,
                problem_count: 0,
                warnings: vec![],
                error: Some("尚未链接题库".into()),
            };
        }

        let path_str = path.display().to_string();
        if !path.is_dir() {
            return BankStatus {
                linked: true,
                path: Some(path_str.clone()),
                path_exists: false,
                name: None,
                version: None,
                problem_count: 0,
                warnings: vec![],
                error: Some(format!("已保存的题库目录不存在: {path_str}")),
            };
        }

        let inspect = Self::inspect(path);
        BankStatus {
            linked: true,
            path: Some(path_str),
            path_exists: true,
            name: inspect.name,
            version: inspect.version,
            problem_count: inspect.problem_count,
            warnings: inspect.warnings,
            error: inspect.error,
        }
    }

    fn manifest_meta(&self) -> (Option<String>, Option<String>) {
        self.read_manifest()
            .ok()
            .map(|manifest| (manifest.name, manifest.version))
            .unwrap_or((None, None))
    }

    pub fn list(&self) -> Result<BankListResult, BankError> {
        let mut items = Vec::new();
        let mut warnings = Vec::new();

        if let Ok(manifest) = self.read_manifest() {
            if let Some(ids) = manifest.problems {
                for id in ids {
                    match self.load(&id) {
                        Ok(problem) => items.push(summary_from(&problem.meta)),
                        Err(err) => warnings.push(format!("题目 {id} 加载失败: {err}")),
                    }
                }
                return Ok(BankListResult {
                    problems: items,
                    warnings,
                });
            }
        }

        for entry in WalkDir::new(self.problems_dir())
            .min_depth(1)
            .max_depth(1)
            .into_iter()
            .flatten()
        {
            if !entry.file_type().is_dir() {
                continue;
            }
            let id = entry.file_name().to_string_lossy().to_string();
            match self.load(&id) {
                Ok(problem) => items.push(summary_from(&problem.meta)),
                Err(err) => warnings.push(format!("题目 {id} 加载失败: {err}")),
            }
        }

        items.sort_by(|a, b| a.id.cmp(&b.id));
        Ok(BankListResult {
            problems: items,
            warnings,
        })
    }

    pub fn load(&self, id: &str) -> Result<LoadedProblem, BankError> {
        validate_problem_id(id)?;
        let dir = self.problems_dir().join(id);
        if !dir.starts_with(&self.problems_dir()) {
            return Err(BankError::Invalid(format!("非法题目路径: {id}")));
        }
        if !dir.is_dir() {
            return Err(BankError::ProblemNotFound(id.to_string()));
        }

        let meta_path = dir.join("meta.json");
        let meta: ProblemMeta = serde_json::from_str(&fs::read_to_string(&meta_path)?)?;
        if meta.id != id {
            return Err(BankError::Invalid(format!(
                "题目 {id} 的 meta.json 中 id 不匹配"
            )));
        }

        let raw_description = read_optional_file(&dir.join("task.md"))
            .or_else(|| read_optional_file(&dir.join("description.md")))
            .unwrap_or_default();
        let (description, mut solution_explanation) = split_description(&raw_description);
        let schema_sql = fs::read_to_string(dir.join("schema.sql")).unwrap_or_default();
        let cases = load_cases(&dir)?;
        let solution_sql = read_optional_file(&dir.join("solution.sql")).or_else(|| {
            cases
                .first()
                .and_then(|c| c.reference_sql.clone())
                .filter(|s| !s.trim().is_empty())
        });
        if solution_explanation.is_none() {
            solution_explanation = read_optional_file(&dir.join("explanation.md"));
        }

        Ok(LoadedProblem {
            meta,
            description,
            schema_sql,
            solution_sql,
            solution_explanation,
            cases,
        })
    }

    fn read_manifest(&self) -> Result<Manifest, BankError> {
        let path = self.root.join("manifest.json");
        let text = fs::read_to_string(path)?;
        Ok(serde_json::from_str(&text)?)
    }

    fn problems_dir(&self) -> PathBuf {
        self.root.join("problems")
    }
}

fn validate_problem_id(id: &str) -> Result<(), BankError> {
    if id.is_empty()
        || id.contains("..")
        || id.contains('/')
        || id.contains('\\')
        || id.contains('\0')
    {
        return Err(BankError::Invalid(format!("非法题目 ID: {id}")));
    }
    Ok(())
}

fn summary_from(meta: &ProblemMeta) -> ProblemSummary {
    ProblemSummary {
        id: meta.id.clone(),
        title: meta.title.clone(),
        difficulty: meta.difficulty.clone(),
        tags: meta.tags.clone(),
        accepted: false,
    }
}

fn read_optional_file(path: &Path) -> Option<String> {
    fs::read_to_string(path).ok()
}

fn normalize_description(text: &str) -> String {
    text.replace("## 任务", "## 目标")
        .replace("##任务", "## 目标")
}

fn split_description(text: &str) -> (String, Option<String>) {
    let normalized = normalize_description(text);
    for marker in ["## 解析", "## 题解"] {
        if let Some(idx) = normalized.find(marker) {
            let description = normalized[..idx].trim_end().to_string();
            let explanation = normalized[idx..].trim().to_string();
            return (description, Some(explanation));
        }
    }
    (normalized, None)
}

fn load_cases(dir: &Path) -> Result<Vec<TestCase>, BankError> {
    let cases_path = dir.join("cases.json");
    let text = fs::read_to_string(&cases_path)?;
    let file: CasesFile = serde_json::from_str(&text)?;
    if file.cases.is_empty() {
        return Err(BankError::Invalid(format!(
            "{} 至少需要一个测试点",
            dir.display()
        )));
    }
    Ok(file.cases)
}

fn invalid_inspect(path: String, error: String) -> BankInspectResult {
    BankInspectResult {
        valid: false,
        path,
        name: None,
        version: None,
        problem_count: 0,
        warnings: vec![],
        error: Some(error),
    }
}
