
from urllib.parse import urlparse
import re

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional

from ..services.tinyfish import TinyFishClient


router = APIRouter()


class PlanRequest(BaseModel):
    issue_url: str = Field(..., description="GitHub issue URL")


class Step(BaseModel):
    title: str
    description: str
    command: Optional[str] = None
    checked: bool = False


class ContributionPlan(BaseModel):
    issue_url: str
    summary: str
    steps: List[Step]


def _repo_from_issue(url: str):
    parsed = urlparse(url)

    if parsed.netloc.lower() not in ("github.com", "www.github.com"):
        return None

    match = re.match(
        r"^/([^/]+)/([^/]+)/issues/(\d+)/?$",
        parsed.path
    )

    if not match:
        return None

    owner, repo, number = match.groups()
    return owner, repo, int(number)


@router.post(
    "/contribution-plan",
    response_model=ContributionPlan
)
def generate_plan(
    req: PlanRequest,
    client: TinyFishClient = Depends()
):
    """Generate a beginner-friendly contribution plan."""

    repo_details = _repo_from_issue(req.issue_url)

    if not repo_details:
        raise HTTPException(
            status_code=400,
            detail="Invalid GitHub issue URL."
        )

    owner, repo, issue_number = repo_details
    repo_name = f"{owner}/{repo}"

    # TinyFish Fetch expects a list of URLs.
    try:
        fetch_data = client.fetch([req.issue_url])

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"TinyFish fetch failed: {str(exc)}"
        )

    # TinyFish returns fetched content inside results.
    results = fetch_data.get("results", [])

    if not results:
        errors = fetch_data.get("errors", [])
        raise HTTPException(
            status_code=502,
            detail=f"Could not retrieve issue details: {errors}"
        )

    issue_data = results[0]

    title = issue_data.get("title") or f"Issue #{issue_number}"

    issue_text = (
        issue_data.get("text")
        or issue_data.get("content")
        or ""
    )

    if not issue_text:
        issue_text = (
            "Review the original GitHub issue for its "
            "description, requirements and expected outcome."
        )

    summary = (
        f"Contribution roadmap for {title} "
        f"in repository {repo_name}."
    )

    steps = [
        Step(
            title="Understand the issue",
            description=(
                f"Read the issue carefully: {req.issue_url}\n\n"
                f"{issue_text[:1500]}"
            )
        ),
        Step(
            title="Clone the repository",
            description="Download the project to your computer.",
            command=f"git clone https://github.com/{repo_name}.git"
        ),
        Step(
            title="Open the project",
            description="Enter the repository folder.",
            command=f"cd {repo}"
        ),
        Step(
            title="Read the README",
            description="Understand the project and follow its setup instructions."
        ),
        Step(
            title="Check contribution guidelines",
            description="Look for CONTRIBUTING.md and follow the project's rules."
        ),
        Step(
            title="Create a new branch",
            description="Keep your changes separate from the main branch.",
            command="git checkout -b fix-issue"
        ),
        Step(
            title="Implement the solution",
            description="Make the smallest change that correctly addresses the issue."
        ),
        Step(
            title="Run tests",
            description="Run the project's recommended tests and check for errors."
        ),
        Step(
            title="Commit your changes",
            description="Save your work in Git.",
            command='git add . && git commit -m "Fix issue"'
        ),
        Step(
            title="Push your branch",
            description="Upload your changes to GitHub.",
            command="git push origin fix-issue"
        ),
        Step(
            title="Create a Pull Request",
            description=(
                f"Open a pull request in {repo_name} "
                f"and reference issue #{issue_number}."
            )
        )
    ]

    return ContributionPlan(
        issue_url=req.issue_url,
        summary=summary,
        steps=steps
    )
