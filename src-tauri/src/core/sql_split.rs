/// Split SQL script into statements on semicolons outside quotes and comments.
pub fn split_sql(script: &str) -> Vec<String> {
    let mut statements = Vec::new();
    let mut current = String::new();
    let mut chars = script.chars().peekable();

    while let Some(ch) = chars.next() {
        match ch {
            '\'' => {
                current.push(ch);
                while let Some(next) = chars.next() {
                    current.push(next);
                    if next == '\'' {
                        if chars.peek() == Some(&'\'') {
                            current.push(chars.next().unwrap());
                            continue;
                        }
                        break;
                    }
                }
            }
            '"' => {
                current.push(ch);
                while let Some(next) = chars.next() {
                    current.push(next);
                    if next == '"' {
                        if chars.peek() == Some(&'"') {
                            current.push(chars.next().unwrap());
                            continue;
                        }
                        break;
                    }
                }
            }
            '-' if chars.peek() == Some(&'-') => {
                current.push(ch);
                current.push(chars.next().unwrap());
                while let Some(next) = chars.next() {
                    if next == '\n' {
                        current.push(next);
                        break;
                    }
                    current.push(next);
                }
            }
            '/' if chars.peek() == Some(&'*') => {
                current.push(ch);
                current.push(chars.next().unwrap());
                while let Some(next) = chars.next() {
                    if next == '*' && chars.peek() == Some(&'/') {
                        current.push(next);
                        current.push(chars.next().unwrap());
                        break;
                    }
                    current.push(next);
                }
            }
            ';' => {
                let stmt = current.trim();
                if !stmt.is_empty() {
                    statements.push(stmt.to_string());
                }
                current.clear();
            }
            _ => current.push(ch),
        }
    }

    let tail = current.trim();
    if !tail.is_empty() {
        statements.push(tail.to_string());
    }

    statements
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn splits_simple_statements() {
        let parts = split_sql("SELECT 1; SELECT 2;");
        assert_eq!(parts, vec!["SELECT 1", "SELECT 2"]);
    }

    #[test]
    fn ignores_semicolon_in_single_quotes() {
        let parts = split_sql("SELECT ';' AS x; SELECT 2;");
        assert_eq!(parts.len(), 2);
        assert!(parts[0].contains('\''));
    }

    #[test]
    fn ignores_semicolon_in_double_quotes() {
        let parts = split_sql(r#"SELECT ";" AS x; SELECT 2;"#);
        assert_eq!(parts.len(), 2);
    }

    #[test]
    fn ignores_semicolon_in_line_comment() {
        let parts = split_sql("SELECT 1; -- ; comment\nSELECT 2;");
        assert_eq!(parts.len(), 2);
        assert_eq!(parts[0], "SELECT 1");
        assert!(parts[1].contains("SELECT 2"));
    }
}
