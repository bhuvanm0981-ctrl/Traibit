import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from ..services.tinyfish import TinyFishClient

router = APIRouter()

class VerifyRequest(BaseModel):
    issue_url: str = Field(..., description="Full URL to a GitHub issue")

class VerificationResult(BaseModel):
    issue_url: str
    status: str = Field(..., description="Verified open / closed / claimed / unknown")
    last_activity: Optional[str] = None
    active_pr: Optional[bool] = None
    assignees: Optional[List[str]] = None
    comments_count: Optional[int] = None
    evidence_links: List[str] = Field(default_factory=list)

@router.post("/verify", response_model=VerificationResult)
def verify_issue(req: VerifyRequest, client: TinyFishClient = Depends()):
    """Verify an issue using TinyFish:
    1️⃣ Fetch the issue page (fetch API).
    2️⃣ Parse key fields (state, assignees, PR links, recent comments).
    """
    # Basic URL validation
    if not req.issue_url.startswith("https://github.com/") or "/issues/" not in req.issue_url:
        raise HTTPException(status_code=400, detail="Invalid GitHub issue URL")

    try:
        page = client.fetch(req.issue_url)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"TinyFish fetch failed: {exc}")

    html = page.get("content", "")
    # Simple regex‑based extraction (acceptable for MVP)
    import re
    state_match = re.search(r'"state":"(open|closed)"', html, re.IGNORECASE)
    state = state_match.group(1).capitalize() if state_match else "Unknown"

    # Find assignees list (GitHub embeds usernames in data-hovercard-url attributes)
    assignees = re.findall(r'data-hovercard-url="/users/([^/]+)/hovercard"', html)

    # Detect an active PR referencing this issue (common pattern "#<num>" in PR titles)
    pr_match = re.search(r'href="([^\"]+/pull/\d+)"[^>]*>#\d+', html, re.IGNORECASE)
    active_pr = bool(pr_match)

    comments = len(re.findall(r'"commentBody"', html))
    last_match = re.search(r'"updatedAt":"([^"]+)"', html)
    last_activity = last_match.group(1) if last_match else None

    return VerificationResult(
        issue_url=req.issue_url,
        status=state,
        last_activity=last_activity,
        active_pr=active_pr,
        assignees=assignees,
        comments_count=comments,
        evidence_links=[req.issue_url],
    )
