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


def extract_github_issue(url: str):
    """Extract owner, repository and issue number from a GitHub URL."""

    parsed = urlparse(url)

    if parsed.netloc.lower() not in {
        "github.com",
        "www.github.com"
    }:
        return None

    match = re.match(
        r"^/([^/]+)/([^/]+)/issues/(\d+)/?$",
        parsed.path
    )

    if not match:
        return None

    owner, repo, number = match.groups()

    return owner, repo, int(number)


def verify_github_issue(owner: str, repo: str, number: int):
    """Verify issue status using the GitHub REST API."""

    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues/{number}"

    response = requests.get(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        },
        timeout=15
    )

    if response.status_code == 404:
        return None

    response.raise_for_status()

    issue = response.json()

    # GitHub's issues endpoint also returns pull requests.
    if "pull_request" in issue:
        return None

    if issue.get("state") != "open":
        return None

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

    assignees = issue.get("assignees", [])

    return {
        "title": issue.get("title", ""),
        "repo_name": f"{owner}/{repo}",
        "issue_number": number,
        "url": issue.get("html_url", ""),
        "description": issue.get("body") or "",
        "last_activity": issue.get("updated_at"),
        "status": "Open",
        "active_pr": False,
        "difficulty_estimate": difficulty,
        "required_skills": [],
        "assignee_count": len(assignees)
    }


@router.post("/discover", response_model=List[IssueSummary])
def discover_issues(
    request: DiscoverRequest,
    client: TinyFishClient = Depends()
):
    """Discover and verify GitHub issues using TinyFish and GitHub API."""

    languages = request.language or ["Python"]
    language_text = " ".join(languages)

    topic_text = " ".join(request.topic or [])
    keyword_text = request.keywords or "good first issue"

    queries = [
        f'GitHub {language_text} {topic_text} beginner open source issues',
        f'site:github.com/*/*/issues {language_text} "good first issue"',
        f'GitHub repositories {language_text} issues labeled good first issue',
        f'{language_text} beginner-friendly open source GitHub issues {keyword_text}'
    ]

    candidate_urls = set()

    for query in queries:
        try:
            search_data = client.search(query)
            results = search_data.get("results", [])

            for result in results:
                url = result.get("url", "")

                if extract_github_issue(url):
                    candidate_urls.add(url)

        except Exception:
            continue

    if not candidate_urls:
        raise HTTPException(
            status_code=404,
            detail="No GitHub issue URLs found. Try changing your search keywords."
        )

    verified_issues = []

    for url in candidate_urls:
        extracted = extract_github_issue(url)

        if not extracted:
            continue

        owner, repo, number = extracted

        try:
            issue = verify_github_issue(owner, repo, number)

            if not issue:
                continue

            # Do not show issues already assigned to someone.
            if issue["assignee_count"] > 0:
                continue

            issue["language"] = ", ".join(languages)
            issue["topic"] = ", ".join(request.topic or [])

            verified_issues.append(issue)

        except requests.RequestException:
            continue

    if not verified_issues:
        raise HTTPException(
            status_code=404,
            detail="No verified open and unassigned issues found. Try broader keywords."
        )

    # Put explicitly beginner-labelled issues first.
    verified_issues.sort(
        key=lambda issue: issue["difficulty_estimate"] != "Beginner"
    )

    return verified_issues[:20]