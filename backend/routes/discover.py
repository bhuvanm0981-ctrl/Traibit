
import os
import re
import requests

from urllib.parse import urlparse
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from ..services.tinyfish import TinyFishClient


router = APIRouter()

GITHUB_API = "https://api.github.com"


class DiscoverRequest(BaseModel):
    language: List[str] = Field(...)
    topic: List[str] = Field(...)
    experience: str = Field(...)
    difficulty: Optional[str] = None
    keywords: Optional[str] = None


class IssueSummary(BaseModel):
    title: str
    repo_name: str
    language: str
    topic: str
    issue_number: int
    url: str
    description: Optional[str] = None
    difficulty_estimate: Optional[str] = None
    required_skills: Optional[List[str]] = None
    last_activity: Optional[str] = None
    status: Optional[str] = None
    active_pr: Optional[bool] = None
    assignees: List[str] = Field(default_factory=list)
    comments_count: Optional[int] = None
    repo_archived: Optional[bool] = None
    evidence_links: List[str] = Field(default_factory=list)


def extract_github_issue(url: str):
    """Extract owner, repository and issue number."""

    parsed = urlparse(url)

    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() not in {"github.com", "www.github.com"}
    ):
        return None

    match = re.fullmatch(
        r"/([^/]+)/([^/]+)/issues/([1-9]\d*)/?",
        parsed.path
    )

    if not match:
        return None

    owner, repo, number = match.groups()
    return owner, repo, int(number)


def github_get(endpoint: str):
    """Retrieve information from GitHub's REST API."""

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(
        f"{GITHUB_API}{endpoint}",
        headers=headers,
        timeout=15
    )

    if response.status_code == 404:
        return None

    if response.status_code == 403:
        raise requests.HTTPError(
            "GitHub API rate limit or access restriction reached."
        )

    response.raise_for_status()
    return response.json()


def verify_github_issue(owner: str, repo: str, number: int):
    """Verify issue, repository and linked PR information."""

    issue_endpoint = f"/repos/{owner}/{repo}/issues/{number}"

    issue = github_get(issue_endpoint)

    if not issue:
        return None

    # GitHub's issues endpoint also returns pull requests.
    if "pull_request" in issue:
        return None

    # Only open issues are candidates for contribution.
    if issue.get("state") != "open":
        return None

    repository = github_get(f"/repos/{owner}/{repo}")

    if not repository:
        return None

    assignees = [
        person.get("login", "")
        for person in issue.get("assignees", [])
    ]

    archived = repository.get("archived", False)

    # Check issue timeline for linked open pull requests.
    active_pr = None
    evidence_links = [
        issue.get("html_url", "")
    ]

    try:
        timeline = github_get(
            f"{issue_endpoint}/timeline?per_page=100"
        )

        if timeline is not None:
            active_pr = False

            for event in timeline:
                source_issue = (
                    event.get("source", {})
                    .get("issue", {})
                )

                if (
                    event.get("event") == "cross-referenced"
                    and source_issue.get("pull_request")
                    and source_issue.get("state") == "open"
                ):
                    active_pr = True

                    pr_url = source_issue.get("html_url")

                    if pr_url and pr_url not in evidence_links:
                        evidence_links.append(pr_url)

    except requests.RequestException:
        # Do not pretend that PR verification succeeded.
        active_pr = None

    # Determine a transparent status.
    if archived:
        status = "Repository Archived"
    elif assignees:
        status = "Open - Assigned"
    elif active_pr is True:
        status = "Open - Linked PR"
    elif active_pr is None:
        status = "Open - PR Status Unknown"
    else:
        status = "Open - Unassigned"

    labels = [
        label.get("name", "").lower()
        for label in issue.get("labels", [])
    ]

    beginner_labels = {
        "good first issue",
        "good first issue!",
        "beginner",
        "beginner-friendly",
        "first-timers-only"
    }

    difficulty = (
        "Beginner"
        if any(label in beginner_labels for label in labels)
        else "Needs review"
    )

    return {
        "title": issue.get("title", ""),
        "repo_name": f"{owner}/{repo}",
        "issue_number": number,
        "url": issue.get("html_url", ""),
        "description": issue.get("body") or "",
        "last_activity": issue.get("updated_at"),
        "status": status,
        "active_pr": active_pr,
        "assignees": assignees,
        "comments_count": issue.get("comments", 0),
        "repo_archived": archived,
        "evidence_links": evidence_links,
        "difficulty_estimate": difficulty,
        "required_skills": [],
        "language": repository.get("language") or "Unknown"
    }


@router.post("/discover", response_model=List[IssueSummary])
def discover_issues(
    request: DiscoverRequest,
    client: TinyFishClient = Depends()
):
    """Discover using TinyFish and verify using GitHub."""

    languages = request.language or ["Python"]
    language_text = " ".join(languages)

    topics = request.topic or []
    topic_text = " ".join(topics)
    keyword_text = request.keywords or "good first issue"

    queries = [
        f"GitHub {language_text} {topic_text} beginner open source issues",
        f'site:github.com/*/*/issues {language_text} "good first issue"',
        f"GitHub repositories {language_text} issues labeled good first issue",
        f"{language_text} beginner-friendly open source GitHub issues {keyword_text}"
    ]

    candidate_urls = set()

    # TinyFish Search discovers candidate issue URLs.
    for query in queries:
        try:
            search_data = client.search(query)

            for result in search_data.get("results", []):
                url = result.get("url", "")

                if extract_github_issue(url):
                    candidate_urls.add(url)

        except Exception:
            # Continue with other search queries.
            continue

    if not candidate_urls:
        raise HTTPException(
            status_code=404,
            detail="No GitHub issue URLs found. Try changing your search keywords."
        )

    verified_issues = []

    # GitHub API verifies every candidate.
    for url in candidate_urls:
        extracted = extract_github_issue(url)

        if not extracted:
            continue

        owner, repo, number = extracted

        try:
            issue = verify_github_issue(owner, repo, number)

            if not issue:
                continue

            issue["language"] = (
                issue["language"]
                if issue["language"] != "Unknown"
                else ", ".join(languages)
            )

            issue["topic"] = ", ".join(topics)

            verified_issues.append(issue)

        except requests.RequestException:
            # Do not show an issue whose verification failed.
            continue

    if not verified_issues:
        raise HTTPException(
            status_code=404,
            detail="No verified open issues found. Try broader keywords."
        )

    # Rank suitable issues first without hiding other verified issues.
    def ranking(issue):
        return (
            issue["repo_archived"],
            issue["status"] != "Open - Unassigned",
            issue["difficulty_estimate"] != "Beginner"
        )

    verified_issues.sort(key=ranking)

    return verified_issues[:20]
