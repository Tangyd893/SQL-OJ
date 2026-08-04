//! MySQL → SQLite compatibility layer for the judge sandbox.

use regex::Regex;
use std::sync::LazyLock;

static RE_LINE_COMMENT: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"--[^\n]*").unwrap());
static RE_BLOCK_COMMENT: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"/\*.*?\*/").unwrap());

pub fn strip_sql_comments(sql: &str) -> String {
    let s = RE_BLOCK_COMMENT.replace_all(sql, "");
    RE_LINE_COMMENT.replace_all(&s, "").into_owned()
}

fn mysql_fmt_to_sqlite(fmt: &str) -> String {
    fmt.replace("%i", "%M").replace("%s", "%S")
}

pub fn adapt_mysql_ddl(sql: &str) -> String {
    let mut out = sql.to_string();
    let rules: &[(&str, &str)] = &[
        (r"(?i)\bUNSIGNED\b", ""),
        (r"(?i)\bINT\b", "INTEGER"),
        (r"(?i)\bBIGINT\b", "INTEGER"),
        (r"(?i)\bVARCHAR\s*\(\s*\d+\s*\)", "TEXT"),
        (r"(?i)\bDECIMAL\s*\(\s*\d+\s*,\s*\d+\s*\)", "REAL"),
        (r"(?i)\bDOUBLE\b", "REAL"),
        (r"\bDATETIME\b", "TEXT"),
        (r"(?i)\bAUTO_INCREMENT\b", ""),
        (
            r"(?i)\bUNIQUE\s+KEY\s+(\w+)\s*\(([^)]+)\)",
            "CONSTRAINT $1 UNIQUE ($2)",
        ),
        (r"(?i)ENGINE\s*=\s*\w+\b", ""),
        (r"(?i)DEFAULT\s+CHARSET\s*=\s*\w+\b", ""),
        (r"(?i)COLLATE\s+\w+[^,\n;]*", ""),
        (r"(?i)COMMENT\s*(?:=\s*)?'[^']*'", ""),
        (r",\s*\)", ")"),
        (r"(?i)DEFAULT\s+datetime\('now'\)", "DEFAULT CURRENT_TIMESTAMP"),
    ];
    for (pat, rep) in rules {
        let re = Regex::new(pat).unwrap();
        out = re.replace_all(&out, *rep).into_owned();
    }
    out.trim().to_string()
}

fn adapt_create_table(stmt: &str) -> (String, Vec<String>) {
    let re_table = Regex::new(r"(?is)CREATE\s+TABLE\s+(\w+)").unwrap();
    let Some(caps) = re_table.captures(stmt) else {
        return (stmt.to_string(), Vec::new());
    };
    let table = caps[1].to_string();
    let re_key = Regex::new(r"(?is),\s*KEY\s+(\w+)\s*\(([^)]+)\)").unwrap();
    let mut indexes = Vec::new();
    let body = re_key
        .replace_all(stmt, |caps: &regex::Captures| {
            indexes.push(format!(
                "CREATE INDEX {} ON {}({})",
                &caps[1], table, &caps[2]
            ));
            String::new()
        })
        .into_owned();
    (body, indexes)
}

fn adapt_statement(stmt: &str) -> (String, Vec<String>) {
    let mut extra_indexes = Vec::new();
    let mut input = stmt.to_string();
    if Regex::new(r"(?is)^CREATE\s+TABLE")
        .unwrap()
        .is_match(stmt)
    {
        let (body, idx) = adapt_create_table(stmt);
        input = body;
        extra_indexes = idx;
    }

    let mut out = input;

    let rules: &[(&str, &str)] = &[
        (r"(?i)\bINSERT\s+IGNORE\b", "INSERT OR IGNORE"),
        (r"(?i)\bNOW\s*\(\s*\)", "datetime('now')"),
        (r"(?i)VALUES\s*\(\s*(\w+)\s*\)", "excluded.$1"),
    ];
    for (pat, rep) in rules {
        let re = Regex::new(pat).unwrap();
        out = re.replace_all(&out, *rep).into_owned();
    }

    let re = Regex::new(r"(?is)DATE_FORMAT\s*\(\s*([^,]+?)\s*,\s*'([^']+)'\s*\)").unwrap();
    out = re
        .replace_all(&out, |caps: &regex::Captures| {
            format!(
                "strftime('{}', {})",
                mysql_fmt_to_sqlite(&caps[2]),
                &caps[1]
            )
        })
        .into_owned();

    for (pat, rep) in [
        (
            r"(?is)\bYEAR\s*\(\s*([^)]+?)\s*\)",
            "CAST(strftime('%Y', $1) AS INTEGER)",
        ),
        (
            r"(?is)\bDATEDIFF\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)",
            "CAST((julianday($1) - julianday($2)) AS INTEGER)",
        ),
        (
            r"(?is)DATE_ADD\s*\(\s*([^,]+?)\s*,\s*INTERVAL\s+(.+?)\s+DAY\s*\)",
            "date($1, '+' || $2 || ' day')",
        ),
        (
            r"(?is)DATE_SUB\s*\(\s*([^,]+?)\s*,\s*INTERVAL\s+(.+?)\s+DAY\s*\)",
            "date($1, '-' || $2 || ' day')",
        ),
        (
            r"(?is)(\w+(?:\.\w+)?)\s*-\s*INTERVAL\s+(.+?)\s+DAY",
            "date($1, '-' || $2 || ' day')",
        ),
        (
            r"(?is)TIMESTAMPDIFF\s*\(\s*MINUTE\s*,\s*([^,]+?)\s*,\s*([^)]+?)\s*\)",
            "CAST((strftime('%s', $2) - strftime('%s', $1)) / 60 AS INTEGER)",
        ),
        (
            r"(?is)GROUP_CONCAT\s*\(\s*(.+?)\s+ORDER\s+BY\s+.+?\s+SEPARATOR\s+'([^']*)'\s*\)",
            "GROUP_CONCAT($1, '$2')",
        ),
        (
            r"(?is)>\s*ALL\s*\(\s*SELECT\s+(\w+)\s+FROM\s+([^)]+?)\)",
            "> (SELECT MAX($1) FROM $2)",
        ),
    ] {
        let re = Regex::new(pat).unwrap();
        out = re.replace_all(&out, rep).into_owned();
    }

    let re_field = Regex::new(r"(?is)\bFIELD\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)").unwrap();
    out = re_field
        .replace_all(&out, |caps: &regex::Captures| {
            let col = caps[1].trim();
            let vals: Vec<&str> = caps[2]
                .split(',')
                .map(|v| v.trim().trim_matches(['\'', '"']))
                .collect();
            let mut parts = String::from("(CASE ");
            for (i, v) in vals.iter().enumerate() {
                parts.push_str(&format!("WHEN {col} = '{v}' THEN {} ", i + 1));
            }
            parts.push_str("ELSE 0 END)");
            parts
        })
        .into_owned();

    out = rewrite_on_duplicate_key(&out);
    out = rewrite_update_join(&out);
    out = rewrite_delete_join(&out);
    out = wrap_compound_order_by(&out);

    (out.trim().to_string(), extra_indexes)
}

fn rewrite_insert_select_upsert(
    head: &str,
    tail: &str,
    table: &str,
    pk: &str,
    insert_cols: &[String],
) -> String {
    let source = Regex::new(r"(?is)FROM\s+(\w+)")
        .unwrap()
        .captures(head)
        .map(|c| c[1].to_string())
        .unwrap_or_else(|| "src".to_string());

    let select_exprs: Vec<String> = Regex::new(r"(?is)SELECT\s+(.+?)\s+FROM\s+")
        .unwrap()
        .captures(head)
        .map(|c| {
            c[1]
                .split(',')
                .map(|s| s.trim().to_string())
                .collect()
        })
        .unwrap_or_default();

    let insert_stmt = format!("{head} WHERE {pk} NOT IN (SELECT {pk} FROM {table})");
    let mut assigns = Vec::new();
    for part in tail.split(',') {
        let mut expr = part.trim().to_string();
        for (ins_col, sel_expr) in insert_cols.iter().zip(select_exprs.iter()) {
            let base = sel_expr.rsplit('.').next().unwrap_or(sel_expr).trim();
            let sub = format!(
                "(SELECT {sel_expr} FROM {source} AS s WHERE s.{pk} = {table}.{pk})"
            );
            if let Ok(re) = Regex::new(&format!(r"(?i)\bexcluded\.{ins_col}\b")) {
                expr = re.replace_all(&expr, sub.as_str()).into_owned();
            }
            if let Ok(re) = Regex::new(&format!(r"(?i)\bnew\.{base}\b")) {
                expr = re.replace_all(&expr, sub.as_str()).into_owned();
            }
        }
        assigns.push(expr);
    }
    let update_stmt = format!(
        "UPDATE {table} SET {} WHERE {pk} IN (SELECT {pk} FROM {source})",
        assigns.join(", ")
    );
    format!("{insert_stmt}; {update_stmt}")
}

fn rewrite_on_duplicate_key(sql: &str) -> String {
    let upper = sql.to_ascii_uppercase();
    let Some(idx) = upper.find("ON DUPLICATE KEY UPDATE") else {
        return sql.to_string();
    };
    let mut head = sql[..idx].trim().to_string();
    let mut tail = sql[idx + "ON DUPLICATE KEY UPDATE".len()..]
        .trim()
        .trim_end_matches(';')
        .to_string();
    let re = Regex::new(r"(?is)INSERT\s+INTO\s+(\w+)\s*\(([^)]+)\)").unwrap();
    let Some(caps) = re.captures(&head) else {
        return sql.to_string();
    };
    let table = caps[1].to_string();
    let pk = caps[2].split(',').next().unwrap_or("id").trim().to_string();
    let insert_cols: Vec<String> = caps[2]
        .split(',')
        .map(|s| s.trim().to_string())
        .collect();
    drop(caps);

    if Regex::new(r"(?is)SELECT\s+.+?\s+FROM\s+")
        .unwrap()
        .is_match(&head)
    {
        if let Some(sel) = Regex::new(r"(?is)SELECT\s+(.+?)\s+FROM\s+")
            .unwrap()
            .captures(&head)
        {
            let select_exprs: Vec<&str> = sel[1].split(',').map(|s| s.trim()).collect();
            for (ins_col, expr) in insert_cols.iter().zip(select_exprs.iter()) {
                let base = expr.rsplit('.').next().unwrap_or(expr).trim();
                if let Ok(re) = Regex::new(&format!(r"(?i)\bnew\.{base}\b")) {
                    tail = re
                        .replace_all(&tail, format!("excluded.{ins_col}"))
                        .into_owned();
                }
            }
        }
        head = Regex::new(r"(?is)\s+AS\s+new\b")
            .unwrap()
            .replace_all(&head, "")
            .into_owned();
        return rewrite_insert_select_upsert(&head, &tail, &table, &pk, &insert_cols);
    }

    let re_vals = Regex::new(r"(?i)VALUES\s*\(\s*(\w+)\s*\)").unwrap();
    tail = re_vals.replace_all(&tail, "excluded.$1").into_owned();
    format!("{head} ON CONFLICT({pk}) DO UPDATE SET {tail}")
}

fn rewrite_update_join(sql: &str) -> String {
    let re = Regex::new(
        r"(?is)^UPDATE\s+(\w+)\s+(\w+)\s+(?:INNER\s+)?JOIN\s+(\w+)\s+(\w+)\s+ON\s+(.+?)\s+SET\s+(.+)$",
    )
    .unwrap();
    re.replace(sql, |caps: &regex::Captures| {
        let table = &caps[1];
        let alias = &caps[2];
        let join_table = &caps[3];
        let join_alias = &caps[4];
        let on_clause = caps[5].replace(&format!("{alias}."), &format!("{table}."));
        let set_clause = Regex::new(&format!(r"(?i)\b{alias}\."))
            .unwrap()
            .replace_all(&caps[6], "")
            .into_owned();
        format!(
            "UPDATE {table} SET {set_clause} FROM {join_table} {join_alias} WHERE {on_clause}"
        )
    })
    .into_owned()
}

fn rewrite_delete_join(sql: &str) -> String {
    let re = Regex::new(r"(?is)^DELETE\s+(\w+)\s+FROM\s+(\w+)\s+(\w+)\s+(JOIN.+)$").unwrap();
    re.replace(sql, |caps: &regex::Captures| {
        let alias = &caps[1];
        let table = &caps[2];
        let alias_repeat = &caps[3];
        if alias != alias_repeat {
            return caps.get(0).unwrap().as_str().to_string();
        }
        format!(
            "DELETE FROM {table} WHERE id IN (SELECT {alias}.id FROM {table} {alias} {})",
            &caps[4]
        )
    })
    .into_owned()
}

fn wrap_compound_order_by(sql: &str) -> String {
    if !Regex::new(r"(?i)\bUNION\b").unwrap().is_match(sql) {
        return sql.to_string();
    }
    if Regex::new(r"(?is)^\s*SELECT\s+\*\s+FROM\s+\(")
        .unwrap()
        .is_match(sql)
    {
        return sql.to_string();
    }
    let lower = sql.to_ascii_lowercase();
    if let Some(pos) = lower.rfind("order by") {
        let (body, rest) = sql.split_at(pos);
        let order = rest[8..].trim();
        return format!("SELECT * FROM ({}) AS _sub ORDER BY {}", body.trim(), order);
    }
    sql.to_string()
}

pub fn adapt_mysql_query(sql: &str) -> String {
    let cleaned = strip_sql_comments(sql);
    let ddl_adapted = adapt_mysql_ddl(&cleaned);
    let mut parts = Vec::new();
    for part in ddl_adapted.split(';') {
        let trimmed = part.trim();
        if trimmed.is_empty() {
            continue;
        }
        if Regex::new(r"(?is)^(CREATE\s+DATABASE|USE\s+\w+)\b")
            .unwrap()
            .is_match(trimmed)
        {
            continue;
        }
        let (stmt, indexes) = adapt_statement(trimmed);
        if !stmt.is_empty() {
            parts.push(stmt);
        }
        parts.extend(indexes);
    }
    parts.join("; ")
}

pub fn adapt_mysql_sql(sql: &str) -> String {
    adapt_mysql_query(sql)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn converts_date_format() {
        let sql = "SELECT DATE_FORMAT(d, '%Y-%m') FROM t";
        assert!(adapt_mysql_sql(sql).contains("strftime"));
    }

    #[test]
    fn converts_insert_ignore() {
        assert!(adapt_mysql_sql("INSERT IGNORE INTO t VALUES (1)")
            .contains("INSERT OR IGNORE"));
    }

    #[test]
    fn strips_line_comments() {
        let sql = "-- comment\nSELECT 1";
        assert_eq!(adapt_mysql_sql(sql), "SELECT 1");
    }

    #[test]
    fn converts_date_sub_with_window() {
        let sql = "SELECT DATE_SUB(login_date, INTERVAL ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY login_date) DAY)";
        let out = adapt_mysql_sql(sql);
        assert!(out.contains("date(login_date"));
        assert!(!out.contains("DATE_SUB"));
    }

    #[test]
    fn converts_update_join() {
        let sql = "UPDATE employees e INNER JOIN dept_budgets d ON e.dept_id = d.dept_id SET e.salary = ROUND(e.salary * (1 + d.salary_ratio), 2)";
        let out = adapt_mysql_sql(sql);
        assert!(out.contains("UPDATE employees SET salary"));
        assert!(!out.contains("employees.salary"));
    }
}
