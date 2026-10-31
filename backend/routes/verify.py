
import os
import re
import requests

from urllib.parse import urlparse
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


router = APIRouter()

GITHUB_API = "https://api.github.com"


class VerifyRequest(BaseModel):
    issue_url: str = Field(
        ...,
        description="Full URL to a GitHub issue"
    )


class VerificationResult(BaseModel):
    issue_url: str
    title: Optional[str] = None
    status: str
    last_activity: Optional[str] = None
    active_pr: Optional[bool] = None
    assignees: List[str] = Field(default_factory=list)
    comments_count: Optional[int] = None
    repo_archived: Optional[bool] = None
    evidence_links: List[str] = Field(default_factory=list)


def extract_issue_details(issue_url: str):
    """Validate and extract owner, repository and issue number."""

    parsed = urlparse(issue_url)

    if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
        raise HTTPException(
            status_code=400,
            detail="Only HTTPS GitHub issue URLs are accepted."
        )

    match = re.fullmatch(
        r"/([^/]+)/([^/]+)/issues/([1-9]\d*)/?",
        parsed.path
    )

    if not match:
        raise HTTPException(
            status_code=400,
            detail="Invalid GitHub issue URL."
        )

    owner, repo, number = match.groups()

    return owner, repo, int(number)


def github_get(endpoint: str):
    """Make a request to GitHub's REST API."""

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    token = os.getenv("GITHUB_TOKEN")

    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.get(
            f"{GITHUB_API}{endpoint}",
            headers=headers,
            timeout=15
        )

        if response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail="GitHub issue or repository not found."
            )

        if response.status_code == 403:
            raise HTTPException(
                status_code=503,
                detail="GitHub API rate limit or access restriction reached."
            )

        if response.status_code == 401:
            raise HTTPException(
                status_code=502,
                detail="GitHub API authentication failed."
            )

        response.raise_for_status()
        return response.json()

    except HTTPException:
        raise

    except requests.Timeout:
        raise HTTPException(
            status_code=504,
            detail="GitHub API request timed out."
        )

    except requests.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Unable to contact GitHub API."
        )


@router.post("/verify", response_model=VerificationResult)
def verify_issue(req: VerifyRequest):

    owner, repo, number = extract_issue_details(req.issue_url)

    issue_endpoint = (
        f"/repos/{owner}/{repo}/issues/{number}"
    )

    repo_endpoint = f"/repos/{owner}/{repo}"

    # 1. Fetch authoritative issue information.
    issue = github_get(issue_endpoint)

    # Do not accidentally treat a pull request as an issue.
    if "pull_request" in issue:
        raise HTTPException(
            status_code=400,
            detail="The supplied URL points to a pull request, not an issue."
        )

    # 2. Fetch repository information.
    repository = github_get(repo_endpoint)

    assignees = [
        person["login"]
        for person in issue.get("assignees", [])
    ]

    archived = repository.get("archived", False)

    # 3. Look for linked pull requests.
    active_pr = None
    evidence_links = [issue.get("html_url", req.issue_url)]

    try:
        timeline = github_get(
            f"{issue_endpoint}/timeline?per_page=100"
        )

        active_pr = False

        for event in timeline:
            source = event.get("source", {})
            source_issue = source.get("issue", {})

            # A cross-reference may point to a pull request.
            if (
                event.get("event") == "cross-referenced"
                and source_issue.get("pull_request")
                and source_issue.get("state") == "open"
            ):
                active_pr = True

                pr_url = source_issue.get("html_url")

                if pr_url and pr_url not in evidence_links:
                    evidence_links.append(pr_url)

    except HTTPException:
        # Issue verification can still succeed if timeline
        # access is unavailable. Keep PR status explicitly unknown.
        active_pr = None

    # 4. Determine the verified status.
    if issue.get("state") == "closed":
        status = "Closed"

    elif archived:
        status = "Repository Archived"

    elif assignees:
        status = "Open - Assigned"

    elif active_pr is True:
        status = "Open - Linked PR"

    elif active_pr is None:
        status = "Open - PR Status Unknown"

    else:
        status = "Open - Unassigned"

    return VerificationResult(
        issue_url=issue.get("html_url", req.issue_url),
        title=issue.get("title"),
        status=status,
        last_activity=issue.get("updated_at"),
        active_pr=active_pr,
        assignees=assignees,
        comments_count=issue.get("comments", 0),
        repo_archived=archived,
        evidence_links=evidence_links
    )
