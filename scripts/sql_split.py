"""Split SQL script into statements on semicolons outside quotes and comments."""


def split_sql(script: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    i = 0
    n = len(script)

    while i < n:
        ch = script[i]

        if ch == "'":
            current.append(ch)
            i += 1
            while i < n:
                current.append(script[i])
                if script[i] == "'":
                    if i + 1 < n and script[i + 1] == "'":
                        current.append(script[i + 1])
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            continue

        if ch == '"':
            current.append(ch)
            i += 1
            while i < n:
                current.append(script[i])
                if script[i] == '"':
                    if i + 1 < n and script[i + 1] == '"':
                        current.append(script[i + 1])
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            continue

        if ch == "-" and i + 1 < n and script[i + 1] == "-":
            current.append(ch)
            current.append(script[i + 1])
            i += 2
            while i < n:
                current.append(script[i])
                if script[i] == "\n":
                    i += 1
                    break
                i += 1
            continue

        if ch == "/" and i + 1 < n and script[i + 1] == "*":
            current.append(ch)
            current.append(script[i + 1])
            i += 2
            while i < n:
                current.append(script[i])
                if script[i] == "*" and i + 1 < n and script[i + 1] == "/":
                    current.append(script[i + 1])
                    i += 2
                    break
                i += 1
            continue

        if ch == ";":
            stmt = "".join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
            i += 1
            continue

        current.append(ch)
        i += 1

    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    return statements
