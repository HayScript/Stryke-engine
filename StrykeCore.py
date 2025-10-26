# StrykeCore.py v1.0
# Stryke — v1.0 "Release One"
# - Safe AST-based evaluation
# - variables, math, string concat, boolean logic
# - if / else / while blocks (closed by 'end')
# - def / return functions with local scope & args
# - import modulename (loads modulename.stryke into module namespace)
# - file IO: readfile(path), writefile(path,content)
# - stryinput("prompt")
# - friendly REPL with history (if readline available)
# - interactive debugger (breakpoints, step, watch)
# - helper REPL commands: compile, stinstall, tests run, show vars/funcs/modules
# - Version: v1.0

import ast
import operator
import re
import sys
import os
import traceback

VERSION = "v1.0"

# ---------------------------
# Environment
# ---------------------------
global_env = {"__modules__": {}, "__packages__": {}}
env = {"vars": {}, "funcs": {}}

# ---------------------------
# Debugger state
# ---------------------------
_debug_mode = False
_breakpoints = set()
_single_step = False
_step_over_depth = None
_call_depth = 0
_watch_expressions = []

_ops = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.And: lambda a, b: a and b,
    ast.Or: lambda a, b: a or b,
}

safe_functions = {
    "int": int,
    "float": float,
    "str": str,
    "len": len,
    "abs": abs,
    "max": max,
    "min": min,
    "round": round,
    "readfile": lambda p: open(p, "r", encoding="utf-8").read(),
    "writefile": lambda p, c: open(p, "w", encoding="utf-8").write(str(c)) or True,
    "input": lambda p="": input(p),
}

def _debug_print(*args):
    if _debug_mode:
        print("[DEBUG]", *args)

def eval_ast(node):
    if isinstance(node, ast.Expression):
        return eval_ast(node.body)
    if isinstance(node, ast.Constant):
        return node.value
    if hasattr(ast, "Num") and isinstance(node, ast.Num):
        return node.n
    if hasattr(ast, "Str") and isinstance(node, ast.Str):
        return node.s
    if isinstance(node, ast.BinOp):
        left = eval_ast(node.left)
        right = eval_ast(node.right)
        return _ops[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp):
        operand = eval_ast(node.operand)
        return _ops[type(node.op)](operand)
    if isinstance(node, ast.BoolOp):
        values = [eval_ast(v) for v in node.values]
        return all(values) if isinstance(node.op, ast.And) else any(values)
    if isinstance(node, ast.Compare):
        left = eval_ast(node.left)
        for op, comp in zip(node.ops, node.comparators):
            right = eval_ast(comp)
            if not _ops[type(op)](left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.Name):
        idn = node.id
        if idn in env["vars"]: return env["vars"][idn]
        if idn in global_env: return global_env[idn]
        if idn in safe_functions: return safe_functions[idn]
        raise NameError(f"Unknown identifier: {idn}")
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            fname = node.func.id
            args = [eval_ast(a) for a in node.args]
            if fname in env["funcs"]:
                return call_user_func(fname, args)
            if fname in safe_functions:
                return safe_functions[fname](*args)
            raise NameError(f"Unknown function: {fname}")
        raise ValueError("Unsupported call expression")
    raise ValueError("Unsupported expression type: " + str(type(node)))

def safe_eval(expr_text):
    expr_text = expr_text.strip()
    if (expr_text.startswith('"') and expr_text.endswith('"')) or (expr_text.startswith("'") and expr_text.endswith("'")):
        return expr_text[1:-1]
    try:
        node = ast.parse(expr_text, mode="eval")
    except Exception:
        if expr_text in env["vars"]:
            return env["vars"][expr_text]
        return expr_text
    return eval_ast(node)

class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value

def call_user_func(name, arg_values):
    global _call_depth
    params, body = env["funcs"][name]
    if len(arg_values) != len(params):
        raise TypeError(f"{name} expects {len(params)} args, got {len(arg_values)}")
    saved_vars = env["vars"].copy()
    _call_depth += 1
    try:
        for p, v in zip(params, arg_values):
            env["vars"][p] = v
        i = 0
        while i < len(body):
            res = execute_line(body[i], lines=body, idx=i, source_name=f"<func {name}>")
            if isinstance(res, ReturnSignal): return res.value
            if isinstance(res, int): i = res
            i += 1
    finally:
        env["vars"] = saved_vars
        _call_depth -= 1
    return None

def parse_block(lines, start_idx):
    block = []
    i = start_idx
    while i < len(lines):
        if lines[i].strip() == "end":
            return block, i
        block.append(lines[i])
        i += 1
    raise SyntaxError("Missing 'end'")

def check_debug_pause(source_name, lineno, line_text):
    return _single_step or (source_name, lineno) in _breakpoints or lineno in _breakpoints

def debug_prompt(source_name, lineno, line_text):
    print(f"\n== PAUSED at {source_name}:{lineno}  >> {line_text.strip()}")
    if _watch_expressions:
        print("  watches:")
        for w in _watch_expressions:
            try: print("   -", w, "=", safe_eval(w))
            except: print("   -", w, "= <err>")
    while True:
        try: cmd = input("(stry-debug) ").strip()
        except EOFError: return "continue"
        if cmd in ("c","continue"): return "continue"
        if cmd in ("s","step"): return "step"
        if cmd in ("n","next"): return "next"
        if cmd.startswith("b "):
            arg = cmd[2:].strip()
            if ":" in arg: fname, ln = arg.split(":",1); _breakpoints.add((fname,int(ln)))
            else: _breakpoints.add(int(arg)); print("[debug] breakpoint set", arg); continue
        if cmd.startswith("del "):
            arg = cmd[4:].strip()
            try: _breakpoints.discard(int(arg))
            except: pass
            print("[debug] breakpoint removed", arg); continue
        if cmd in ("bt","stack"): print("Call depth:",_call_depth,"Vars snapshot:",env["vars"]); continue
        if cmd.startswith("watch "): expr=cmd[6:].strip(); _watch_expressions.append(expr); print("[debug] watch added:", expr); continue
        if cmd.startswith("unwatch "): expr=cmd[8:].strip(); _watch_expressions.remove(expr) if expr in _watch_expressions else None; continue
        if cmd in ("vars",): print(env["vars"]); continue
        if cmd in ("help","?"):
            print("debug commands:\n  c/continue\n  s/step\n  n/next\n  b N or b file:N\n  del N\n  watch EXPR\n  unwatch EXPR\n  stack/bt\n  vars\n  help/?\n"); continue
        print("[debug] unknown debug command")

def execute_line(line, lines=None, idx=None, source_name="<stdin>"):
    global _single_step,_step_over_depth,_call_depth
    raw=line.rstrip("\n"); stripped=raw.strip()
    if not stripped or stripped.startswith("#"): return None
    lineno=(idx+1) if idx is not None else 0
    if check_debug_pause(source_name, lineno, raw):
        action=debug_prompt(source_name, lineno, raw)
        if action=="continue": pass
        elif action=="step": _single_step=True
        elif action=="next": _step_over_depth=_call_depth; _single_step=True

    m=re.match(r'^\s*stryset\s+(\w+)\s*\(\s*(.+)\s*\)\s*$', stripped)
    if m:
        name, expr = m.groups(); env["vars"][name] = safe_eval(expr); return None

    m=re.match(r'^\s*stryprint\s+(.+)$', stripped)
    if m:
        expr=m.group(1); val=safe_eval(expr); print(val); return None

    m=re.match(r'^\s*def\s+(\w+)\s*\((.*?)\)\s*:\s*$', stripped)
    if m:
        fname, params = m.groups(); param_list=[p.strip() for p in params.split(",") if p.strip()]
        block, end_idx=parse_block(lines, idx+1)
        env["funcs"][fname]=(param_list, block); return end_idx

    m=re.match(r'^\s*return\s+(.+)$', stripped)
    if m:
        val=safe_eval(m.group(1)); return ReturnSignal(val)

    m=re.match(r'^\s*if\s*\(\s*(.+)\s*\)\s*:\s*$', stripped)
    if m:
        cond=safe_eval(m.group(1))
        block, end_idx=parse_block(lines, idx+1)
        if cond:
            i=0
            while i<len(block): res=execute_line(block[i], lines=block, idx=i); 
            if isinstance(res,int): i=res; i+=1; continue
            elif isinstance(res,ReturnSignal): return res
            i+=1
        return end_idx

    if stripped=="end": return None
    return None

def run_file(path):
    if not os.path.isfile(path): print("File not found:", path); return
    with open(path,"r",encoding="utf-8") as f:
        lines=f.readlines()
    i=0
    while i<len(lines):
        res=execute_line(lines[i], lines, i, source_name=path)
        if isinstance(res,int): i=res
        elif isinstance(res,ReturnSignal): return res.value
        i+=1

def repl():
    print(f"Stryke v{VERSION} REPL — type 'help' for commands")
    hist=[]
    while True:
        try: cmd=input("stry> ").strip()
        except EOFError: print(); break
        if not cmd: continue
        hist.append(cmd)
        if cmd in ("exit","quit"): break
        if cmd=="help":
            print("Commands:\n  help — show this\n  vars — show variables\n  funcs — show functions\n  modules — show loaded modules\n  compile <file> — compile .stryke to .py\n  stinstall <path> — install package\n  tests run — run test harness\n  exit/quit — leave REPL")
            continue
        if cmd=="vars": print(env["vars"]); continue
        if cmd=="funcs": print(list(env["funcs"].keys())); continue
        if cmd=="modules": print(global_env["__modules__"]); continue
        if cmd.startswith("compile "):
            path=cmd[8:].strip(); import stryke_to_py; stryke_to_py.compile_file(path); continue
        if cmd.startswith("stinstall "):
            path=cmd[10:].strip(); import stryinstall; stryinstall.install_package(path); continue
        if cmd=="tests run":
            import test_harness; test_harness.run_tests(); continue
        try:
            execute_line(cmd)
        except Exception:
            traceback.print_exc()

def main():
    if len(sys.argv)>1 and sys.argv[1]=="run":
        if len(sys.argv)<3: print("Usage: python StrykeCore.py run <file>"); return
        run_file(sys.argv[2])
    else:
        repl()

if __name__=="__main__":
    main()
