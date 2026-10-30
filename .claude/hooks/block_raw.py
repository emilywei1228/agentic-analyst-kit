"""Hook: block any write inside data/raw/, from file edits or shell commands. Claude Code passes the
planned action as JSON on stdin. Exit code 2 blocks the action and shows the message to Claude.
Shell checks catch the common ways to write a file; reading data/raw/ is always allowed."""
import json, re, sys

RAW = r"data/raw\b"
# Shell patterns that write to, move, or delete something under data/raw/
SHELL_WRITES = [
    rf">>?\|?\s*[\"']?[^\s;|&\"']*{RAW}",                          # > or >> redirect into data/raw/
    rf"\b(rm|mv|truncate|touch|tee|shred|unlink|rmdir)\b[^;|&]*{RAW}",
    rf"\b(cp|rsync|install|ln)\b[^;|&]*\s[\"']?\S*{RAW}\S*[\"']?\s*($|[;|&])",  # copy INTO data/raw/
    rf"\b(sed|perl|ruby)\b[^;|&]*\s-i[^;|&]*{RAW}",               # in-place edit
    rf"\bof=\S*{RAW}",                                            # dd of=
    rf"\.to_(csv|parquet|excel|json|pickle|feather|sql)\(\s*[rfb]?[\"'][^\"']*{RAW}",
    rf"open\(\s*[rfb]?[\"'][^\"']*{RAW}[^\"']*[\"']\s*,\s*(mode\s*=\s*)?[rfb]?[\"'][^\"']*[wax+]",
    rf"\b(os\.remove|os\.unlink|os\.rename|shutil\.(move|rmtree))\([^)]*{RAW}",
    rf"Path\([^)]*{RAW}[^)]*\)\.(write_\w+|unlink|rename|replace|touch)",
    rf"\bcd\s+[\"']?\S*{RAW}.*(>|\b(rm|mv|truncate|tee|touch|sed\s+-i|cp)\b)",  # cd into data/raw/, then write
]

def blocked():
    print("Blocked: data/raw/ is read-only. Write cleaned data to runs/ instead.", file=sys.stderr)
    sys.exit(2)

event = json.load(sys.stdin)
tool_input = event.get("tool_input", {})

path = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "").replace("\\", "/")
if "/data/raw/" in path or path.startswith("data/raw/"):
    blocked()

command = str(tool_input.get("command", "")).replace("\\", "/")
if any(re.search(p, command) for p in SHELL_WRITES):
    blocked()

sys.exit(0)
