from __future__ import annotations
import concurrent.futures
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = "altento/folio-portfolio"
TREE_URL = f"https://api.github.com/repos/{REPO}/git/trees/main?recursive=1"
TEXT_EXTENSIONS = {".py", ".js", ".mjs", ".json", ".md", ".txt", ".ps1", ".yml", ".yaml", ".xml", ".html", ".css", ".properties", ".gradle", ".sh", ".bat", ".toml", ".ini"}
MARKERS = {
    "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(rb"(?:gh[pousr]_[A-Za-z0-9_]{30,}|github_pat_[A-Za-z0-9_]{30,})"),
    "aws_access_key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "google_api_key": re.compile(rb"AIza[0-9A-Za-z_\-]{30,}"),
    "slack_token": re.compile(rb"xox[baprs]-[A-Za-z0-9-]{20,}"),
}
HEADERS = {"User-Agent": "Folio-public-repository-privacy-audit", "Accept": "application/vnd.github+json"}


def read_url(url: str) -> bytes:
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def main() -> None:
    tree = json.loads(read_url(TREE_URL))
    if tree.get("truncated"):
        raise RuntimeError("GitHub returned a truncated tree; audit cannot claim full snapshot coverage")
    candidates = [entry for entry in tree["tree"]
                  if entry["type"] == "blob" and Path(entry["path"]).suffix.lower() in TEXT_EXTENSIONS
                  and entry.get("size", 0) <= 5_000_000]
    unique: dict[str, dict] = {}
    for entry in candidates:
        unique.setdefault(entry["sha"], entry)
    sha = tree["sha"]

    def scan(item: dict) -> tuple[str, list[str], str | None]:
        path = item["path"]
        url = f"https://raw.githubusercontent.com/{REPO}/{sha}/{urllib.parse.quote(path, safe='/')}"
        try:
            body = read_url(url)
        except Exception as exc:
            return path, [], type(exc).__name__
        hits = [label for label, pattern in MARKERS.items() if pattern.search(body)]
        return path, hits, None

    matches: list[dict] = []
    failures: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        for path, hits, error in pool.map(scan, unique.values()):
            if hits:
                matches.append({"path": path, "marker_types": hits})
            if error:
                failures.append({"path": path, "error_type": error})

    suspicious_names = [entry["path"] for entry in tree["tree"]
        if entry["type"] == "blob" and re.search(r"(^|/)(\.env(?:\.|$)|id_rsa|id_ed25519|[^/]+\.(?:pem|p12|pfx|jks|keystore|sqlite3?|db)$)", entry["path"], re.I)]
    result = {
        "repository": REPO,
        "branch": "main",
        "commit": sha,
        "tree_entries": len(tree["tree"]),
        "text_paths": len(candidates),
        "unique_text_blobs_scanned": len(unique) - len(failures),
        "unique_text_blobs_failed": failures,
        "credential_like_paths": suspicious_names,
        "secret_marker_matches": matches,
        "coverage_complete": not failures and len(tree["tree"]) > 0,
    }
    out = Path(__file__).with_name("results-public-github-scan.json")
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in {"unique_text_blobs_failed", "secret_marker_matches"}}, ensure_ascii=False))
    print(json.dumps({"secret_marker_matches": matches, "failed_count": len(failures)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
