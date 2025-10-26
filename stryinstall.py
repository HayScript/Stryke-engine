# stryinstall.py - local package installer for Stryke
import os, shutil, json, sys

PKG_DIR = os.path.join(os.path.dirname(__file__), "lib")
META = os.path.join(PKG_DIR, "packages.json")

def _ensure():
    if not os.path.isdir(PKG_DIR):
        os.makedirs(PKG_DIR)
    if not os.path.isfile(META):
        with open(META, "w", encoding="utf-8") as f:
            json.dump({}, f)

def install_package(path):
    """Install a local package directory or single .stryke file into lib/"""
    _ensure()
    if not os.path.exists(path):
        print("[stinstall] path not found:", path); return
    name = os.path.basename(os.path.abspath(path))
    dest = os.path.join(PKG_DIR, name)
    if os.path.isdir(path):
        if os.path.exists(dest): shutil.rmtree(dest)
        shutil.copytree(path, dest)
    else:
        if not path.endswith(".stryke"):
            print("[stinstall] not a .stryke file"); return
        if not os.path.exists(dest):
            os.makedirs(dest)
        shutil.copy2(path, os.path.join(dest, os.path.basename(path)))
    with open(META, "r+", encoding="utf-8") as f:
        data = json.load(f)
        data[name] = {"installed": True, "path": dest}
        f.seek(0); f.truncate(); json.dump(data, f, indent=2)
    print("[stinstall] installed", name)

def uninstall_package(name):
    _ensure()
    with open(META, "r+", encoding="utf-8") as f:
        data = json.load(f)
        if name in data:
            path = data[name]["path"]
            if os.path.exists(path):
                shutil.rmtree(path)
            del data[name]
            f.seek(0); f.truncate(); json.dump(data, f, indent=2)
            print("[stinstall] removed", name)
        else:
            print("[stinstall] package not found:", name)

if __name__=="__main__":
    if len(sys.argv)>=3 and sys.argv[1]=="install":
        install_package(sys.argv[2])
    elif len(sys.argv)>=3 and sys.argv[1]=="uninstall":
        uninstall_package(sys.argv[2])
    else:
        print("Usage: python stryinstall.py install <path> | uninstall <name>")
