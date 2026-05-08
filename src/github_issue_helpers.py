from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def resolve_repo_from_destination(destination: str) -> str:
    destination = str(destination or "").strip()
    if not destination:
        return ""

    repo = destination
    if "://" in destination:
        parsed = urlparse(destination)
        path_parts = [part for part in parsed.path.strip("/").split("/") if part]
        if len(path_parts) >= 2:
            repo = f"{path_parts[0]}/{path_parts[1]}"

    return repo.strip("/")


def build_browser_issue_url(destination: str, title: str, body: str, labels_value: str, assignees="", template: str = "") -> str:
    destination = str(destination or "").strip()
    if "://" not in destination:
        repo = destination.strip("/")
        base_url = f"https://github.com/{repo}/issues/new"
        params = {
            "title": title,
            "body": body,
            "labels": labels_value,
        }
        if assignees:
            params["assignees"] = assignees if isinstance(assignees, str) else ",".join(assignees)
        if template:
            params["template"] = template
        return f"{base_url}?{urlencode(params)}"

    parsed = urlparse(destination)
    query_items = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query_items.setdefault("title", title)
    query_items.setdefault("body", body)
    query_items.setdefault("labels", labels_value)
    new_query = urlencode(query_items)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))


def redact_config_sections(config_copy, section_names):
    for section_name in section_names:
        section = config_copy.get(section_name, {})
        if isinstance(section, dict):
            section_copy = dict(section)
            for key in ["email", "github_repo", "better_bugs_url", "github_issues_url", "github_token", "github_token_env"]:
                if key in section_copy:
                    section_copy[key] = "[REDACTED]"
            config_copy[section_name] = section_copy


def post_issue_via_api(repo: str, token: str, payload: dict):
    import requests

    api_url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    return requests.post(api_url, json=payload, headers=headers, timeout=20)


def test_issue_connection(repo: str, token: str):
    import requests

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    user_resp = requests.get("https://api.github.com/user", headers=headers, timeout=15)
    if user_resp.status_code != 200:
        return False, f"Token authentication failed: {user_resp.text or 'Unable to authenticate with the provided token.'}", ""

    user_login = (user_resp.json() or {}).get("login", "unknown")

    repo_resp = requests.get(f"https://api.github.com/repos/{repo}", headers=headers, timeout=15)
    if repo_resp.status_code != 200:
        return False, f"Repository access failed: {repo_resp.text or 'Repository not accessible.'}", user_login

    # Probe write access with an intentionally invalid payload. A 422 means the
    # credentials reached the create-issue endpoint and GitHub rejected only the content.
    probe_resp = requests.post(
        f"https://api.github.com/repos/{repo}/issues",
        json={"title": ""},
        headers=headers,
        timeout=15,
    )
    if probe_resp.status_code == 422:
        return True, f"Repository access is valid and issue creation permission appears available for {repo}.", user_login

    if probe_resp.status_code in (200, 201):
        issue_url = (probe_resp.json() or {}).get("html_url", "")
        return True, f"Write access confirmed for {repo}.\n{issue_url}", user_login

    try:
        message = (probe_resp.json() or {}).get("message", "")
    except Exception:
        message = probe_resp.text or "Unknown error"
    return False, f"Authenticated as {user_login}, but issue creation probe failed ({probe_resp.status_code}): {message}", user_login