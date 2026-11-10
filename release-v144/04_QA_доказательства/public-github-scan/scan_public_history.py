from __future__ import annotations
import concurrent.futures
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

REPO = "altento/folio-portfolio"
API = f"https://api.github.com/repos/{REPO}"
EXTS = {".py", ".js", ".mjs", ".json", ".md", ".txt", ".ps1", ".yml", ".yaml",
        ".xml", ".html", ".css", ".properties", ".gradle", ".sh", ".bat",
        ".toml", ".ini", ".cfg", ".conf", ".sql", ".csv", ".lock"}
MAX_TEXT_BYTES = 20_000_000
HEADERS = {"User-Agent": "Folio-read-only-public-history-audit", "Accept": "application/vnd.github+json"}
MARKERS = {
    "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "github_token": re.compile(rb"(?:gh[pousr]_[A-Za-z0-9_]{30,}|github_pat_[A-Za-z0-9_]{30,})"),
    "aws_access_key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "google_api_key": re.compile(rb"AIza[0-9A-Za-z_-]{30,}"),
    "slack_token": re.compile(rb"xox[baprs]-[A-Za-z0-9-]{20,}"),
    "stripe_secret": re.compile(rb"sk_(?:live|test)_[A-Za-z0-9]{20,}"),
    "openai_secret": re.compile(rb"sk-(?:proj-|live-)?[A-Za-z0-9_-]{32,}"),
    "anthropic_secret": re.compile(rb"sk-ant-(?:apid{2}-)?[A-Za-z0-9_-]{30,}"),
    "npm_token": re.compile(rb"npm_[A-Za-z0-9]{30,}"),
    "pypi_token": re.compile(rb"pypi-[A-Za-z0-9_-]{40,}"),
    "telegram_bot_token": re.compile(rb"d{8,10}:[A-Za-z0-9_-]{30,}"),
    "discord_webhook": re.compile(rb"discord(?:app)?.com/api/webhooks/d+/[A-Za-z0-9_-]{20,}"),
}


def read(url: str, api: bool = False) -> bytes:
    headers = HEADERS if api else {"User-Agent": HEADERS["User-Agent"]}
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


def paged(endpoint: str):
    url = f"{API}/{endpoint}?per_page=100&page=1"
    result = []
    while url:
        request = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(request, timeout=45) as response:
            result.extend(json.loads(response.read()))
            links = response.headers.get("Link", "")
        url = next((part[part.find("<")+1:part.find(">")] for part in links.split(",")
                    if 'rel="next"' in part), None)
    return result


def main():
    commits = paged("commits")
    branches = paged("branches")
    tags = paged("tags")
    ref_shas = {item["sha"] for item in commits}
    ref_shas.update(item["commit"]["sha"] for item in branches)
    ref_shas.update(item["commit"]["sha"] for item in tags)
    unique = {}
    all_paths = set()
    tree_entry_count = 0
    truncated = []
    large_files = []
    for commit_sha in sorted(ref_shas):
        tree = json.loads(read(f"{API}/git/trees/{commit_sha}?recursive=1", api=True))
        entries = tree.get("tree", [])
        tree_entry_count += len(entries)
        if tree.get("truncated"):
            truncated.append(commit_sha)
        for entry in entries:
            if entry["type"] != "blob":
                continue
            path = entry["path"]
            all_paths.add(path)
            if Path(path).suffix.lower() not in EXTS:
                continue
            size = entry.get("size", 0)
            if size > MAX_TEXT_BYTES:
                large_files.append({"commit": commit_sha, "path": path, "size": size})
                continue
            unique.setdefault(entry["sha"], {"sha": entry["sha"], "path": path,
                                             "commit": commit_sha, "size": size})

    def scan(item):
        path = urllib.parse.quote(item["path"], safe="/")
        url = f"https://raw.githubusercontent.com/{REPO}/{item['commit']}/{path}"
        try:
            body = read(url)
        except Exception as exc:
            return item, [], type(exc).__name__
        return item, [name for name, regex in MARKERS.items() if regex.search(body)], None

    matches, failures = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
        for item, hits, error in pool.map(scan, unique.values()):
            if hits:
                matches.append({"path": item["path"], "blob_sha": item["sha"],
                                "commit": item["commit"], "marker_types": hits})
            if error:
                failures.append({"path": item["path"], "commit": item["commit"],
                                 "error_type": error})

    suspicious_paths = [path for path in sorted(all_paths) if re.search(
        r"(^|/)(\.env(?:\.|$)|id_rsa|id_ed25519|[^/]+\.(?:pem|p12|pfx|jks|keystore|sqlite3?|db)$)",
        path, re.I)]
    result = {
        "repository": REPO,
        "visibility": "public",
        "branches": [item["name"] for item in branches],
        "tags": [item["name"] for item in tags],
        "commits_on_default_branch": len(commits),
        "distinct_commit_trees_scanned": len(ref_shas),
        "aggregate_tree_entries_scanned": tree_entry_count,
        "unique_text_blobs_scanned": len(unique) - len(failures),
        "unique_text_blobs_failed": failures,
        "large_text_files_skipped": large_files,
        "truncated_trees": truncated,
        "credential_like_paths_in_history": suspicious_paths,
        "secret_marker_matches": matches,
        "coverage_complete_for_declared_text_scope": not failures and not truncated and not large_files,
        "scope": "All commits on the only listed branch (main), plus branch and tag heads; 14 commits, no tags observed. Text files on an explicit extension allowlist, up to 20 MB; selected credential markers and key/database-like filenames. No remote changes made.",
    }
    out = Path(__file__).with_name("results-public-github-history-scan.json")
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key not in {
        "unique_text_blobs_failed", "secret_marker_matches"}}, ensure_ascii=False))
    print(json.dumps({"secret_marker_matches": matches, "failed_count": len(failures)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
