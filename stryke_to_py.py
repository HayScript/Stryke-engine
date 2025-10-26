# stryke_to_py.py - simple compiler to Python
import re, sys, os

def compile_file(src_path, out_path=None):
    if not os.path.isfile(src_path):
        print("File not found:", src_path); return
    if not out_path:
        out_path = os.path.splitext(src_path)[0] + "_compiled.py"
    py_lines = []
    with open(src_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    indent = 0
    for ln in lines:
        s = ln.rstrip("\n")
        ts = s.strip()
        if not ts or ts.startswith("#"): continue
        # stryset -> assignment
        if ts.startswith("stryset"):
            m = re.match(r'^stryset\s+(\w+)\s*\(\s*(.+)\s*\)\s*$', ts)
            if m:
                name, expr = m.groups()
                py_lines.append(" " * (4*indent) + f"{name} = {expr}")
                continue
        # stryprint -> print
        if ts.startswith("stryprint"):
            m = re.match(r'^stryprint\s+(.+)$', ts)
            if m:
                expr = m.group(1).strip()
                if (expr.startswith('"') and expr.endswith('"')) or (expr.startswith("'") and expr.endswith("'")):
                    inner = expr[1:-1]
                    inner = re.sub(r"\{(\w+)\}", r'{\1}', inner)
                    py_lines.append(" " * (4*indent) + f'print(f"{inner}")')
                else:
                    py_lines.append(" " * (4*indent) + f'print({expr})')
                continue
        # if / else / while / def / return / end / import
        if ts.startswith("if"):
            m = re.match(r'^if\s*\(\s*(.+)\s*\):\s*$', ts)
            if m:
                py_lines.append(" " * (4*indent) + f"if {m.group(1)}:")
                indent += 1; continue
        if ts.startswith("else:"):
            indent = max(0, indent-1)
            py_lines.append(" " * (4*indent) + "else:")
            indent += 1; continue
        if ts.startswith("while"):
            m = re.match(r'^while\s*\(\s*(.+)\s*\):\s*$', ts)
            if m:
                py_lines.append(" " * (4*indent) + f"while {m.group(1)}:")
                indent += 1; continue
        if ts.startswith("def"):
            m = re.match(r'^def\s+(\w+)\s*\(\s*(.*?)\s*\)\s*:\s*$', ts)
            if m:
                name, params = m.groups()
                py_lines.append(" " * (4*indent) + f"def {name}({params}):")
                indent += 1; continue
        if ts.startswith("return"):
            expr = ts[len("return"):].strip()
            py_lines.append(" " * (4*indent) + f"return {expr}")
            continue
        if ts == "end":
            indent = max(0, indent-1); continue
        if ts.startswith("import"):
            m = re.match(r'^import\s+(\w+)\s*$', ts)
            if m:
                # Note: imported module code is not converted; we just note import
                py_lines.append(" " * (4*indent) + f"# import {m.group(1)} (module needs manual conversion)")
                continue
        # fallback raw expression
        py_lines.append(" " * (4*indent) + ts)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# Auto-compiled from .stryke\n")
        f.write("def _stryke_main():\n")
        if not py_lines:
            f.write("    pass\n")
        else:
            for l in py_lines:
                f.write("    " + l + "\n")
        f.write("\nif __name__=='__main__':\n    _stryke_main()\n")
    print("Compiled to", out_path)

if __name__=="__main__":
    if len(sys.argv)>=2:
        compile_file(sys.argv[1])
    else:
        print("Usage: python stryke_to_py.py file.stryke")
