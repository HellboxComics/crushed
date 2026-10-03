"""Every prompt template the asset maker fills in with .format() can actually be filled in: a JSON example inside a
template must have its braces doubled, or .format() stops with a KeyError the first time the prompt is used.
(2026-10-03: layout.py's label prompt had never once run - its JSON schema's braces were read as blanks to fill.)"""
import ast
import glob
import os
import re
import string
import sys

LIB = "/home/claude/crushed/library"
sys.path.insert(0, LIB)
ok, bad = 0, []
files = glob.glob(os.path.join(LIB, "*.py")) + glob.glob(os.path.join(LIB, "*", "*.py"))
for f in files:
    src = open(f).read()
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        bad.append(f"{f}: does not parse ({e})")
        continue
    consts = {}
    for node in tree.body:                                    # module-level NAME = "..." (+ "..." / + OTHER)
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                consts[node.targets[0].id] = node.value
            except Exception:
                pass

    def value(expr, seen=()):
        if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
            return expr.value
        if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Add):
            a, b = value(expr.left, seen), value(expr.right, seen)
            return None if a is None or b is None else a + b
        if isinstance(expr, ast.Name) and expr.id in consts and expr.id not in seen:
            return value(consts[expr.id], seen + (expr.id,))
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ("format", "format_map"):
            tmpl = value(node.func.value)
            if tmpl is None:
                continue
            where = f"{os.path.relpath(f, LIB)}:{node.lineno}"
            try:
                fields = [fn for _, fn, _, _ in string.Formatter().parse(tmpl) if fn is not None]
            except ValueError as e:
                bad.append(f"{where}: the template can't be read by .format(): {e}")
                continue
            wrong = [fn for fn in fields if fn and not re.fullmatch(r"[A-Za-z_]\w*(\.\w+|\[\w+\])*|\d+", fn)]
            given = {k.arg for k in node.keywords if k.arg}
            has_star = any(k.arg is None for k in node.keywords) or node.args
            missing = [fn for fn in fields if fn and re.fullmatch(r"[A-Za-z_]\w*", fn) and fn not in given] \
                if not has_star else []
            if wrong:
                bad.append(f"{where}: braces that are not blanks (double them): {wrong[:3]}")
            elif missing:
                bad.append(f"{where}: blanks with nothing to fill them: {missing}")
            else:
                ok += 1
for b in bad:
    print("FAIL", b)
print(f"{ok} templates fill in" + (f"; {len(bad)} broken" if bad else ""))
sys.exit(1 if bad else 0)
