//! 根据各测试点 reference_sql 与基准测试点的差异，适配用户提交的 SQL。
use regex::Regex;
use std::sync::LazyLock;

static DEPT_EQ: LazyLock<Regex> =
    LazyLock::new(|| Regex::new("(?i)(\\bdept\\s*=\\s*['\"])([^'\"]+)(['\"])").unwrap());
static DEPT_NAME_EQ: LazyLock<Regex> =
    LazyLock::new(|| Regex::new("(?i)(\\bdept_name\\s*=\\s*['\"])([^'\"]+)(['\"])").unwrap());
static TITLE_EQ: LazyLock<Regex> =
    LazyLock::new(|| Regex::new("(?i)(\\btitle\\s*=\\s*['\"])([^'\"]+)(['\"])").unwrap());

const FILTER_PATTERNS: [&LazyLock<Regex>; 3] = [&DEPT_EQ, &DEPT_NAME_EQ, &TITLE_EQ];

fn extract_literal(sql: &str, pattern: &Regex) -> Option<String> {
    pattern
        .captures(sql)
        .and_then(|caps| caps.get(2).map(|m| m.as_str().to_string()))
}

fn replace_literal(sql: &str, pattern: &Regex, from: &str, to: &str) -> String {
    if from == to {
        return sql.to_string();
    }
    pattern
        .replace(sql, |caps: &regex::Captures| {
            let current = caps.get(2).map(|m| m.as_str()).unwrap_or("");
            if current == from {
                format!("{}{}{}", &caps[1], to, &caps[3])
            } else {
                caps[0].to_string()
            }
        })
        .into_owned()
}

/// 将用户 SQL 按当前测试点 reference_sql 相对基准 reference_sql 的差异做字面量替换。
pub fn adapt_user_sql_for_case(
    user_sql: &str,
    baseline_ref: Option<&str>,
    case_ref: Option<&str>,
) -> String {
    let Some(base) = baseline_ref.map(str::trim).filter(|s| !s.is_empty()) else {
        return user_sql.to_string();
    };
    let Some(case) = case_ref.map(str::trim).filter(|s| !s.is_empty()) else {
        return user_sql.to_string();
    };
    if base.eq_ignore_ascii_case(case) {
        return user_sql.to_string();
    }

    let mut adapted = user_sql.to_string();
    for pattern in FILTER_PATTERNS {
        let Some(base_val) = extract_literal(base, pattern) else {
            continue;
        };
        let Some(case_val) = extract_literal(case, pattern) else {
            continue;
        };
        adapted = replace_literal(&adapted, pattern, &base_val, &case_val);
    }
    adapted
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn adapts_department_literal_for_hidden_case() {
        let user = "SELECT name, salary from employees\nwhere dept='技术部'\nORDER BY salary DESC";
        let base = "SELECT name, salary FROM employees WHERE dept = '技术部' ORDER BY salary DESC;";
        let case2 = "SELECT name, salary FROM employees WHERE dept = '市场部' ORDER BY salary DESC;";
        let adapted = adapt_user_sql_for_case(user, Some(base), Some(case2));
        assert!(adapted.contains("'市场部'"), "adapted: {adapted}");
        assert!(!adapted.contains("'技术部'"));
    }

    #[test]
    fn adapts_empty_department_case() {
        let user = "SELECT name, salary FROM employees WHERE dept = '技术部' ORDER BY salary DESC";
        let base = "SELECT name, salary FROM employees WHERE dept = '技术部' ORDER BY salary DESC;";
        let case3 = "SELECT name, salary FROM employees WHERE dept = '财务部' ORDER BY salary DESC;";
        let adapted = adapt_user_sql_for_case(user, Some(base), Some(case3));
        assert!(adapted.contains("'财务部'"), "adapted: {adapted}");
    }

    #[test]
    fn baseline_case_unchanged() {
        let user = "SELECT 1";
        let base = "SELECT name FROM employees WHERE dept = '技术部';";
        let adapted = adapt_user_sql_for_case(user, Some(base), Some(base));
        assert_eq!(adapted, user);
    }
}
