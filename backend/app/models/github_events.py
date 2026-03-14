from typing import Optional
from pydantic import BaseModel


class GithubUser(BaseModel):
    login: str
    id: int


class GithubRepo(BaseModel):
    id: int
    name: str
    full_name: str
    private: bool
    default_branch: str = "main"


class PullRequestHead(BaseModel):
    sha: str
    ref: str


class PullRequest(BaseModel):
    number: int
    title: str
    state: str
    head: PullRequestHead
    user: GithubUser
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0
    html_url: str = ""


class Installation(BaseModel):
    id: int


class PullRequestEvent(BaseModel):
    action: str
    number: int
    pull_request: PullRequest
    repository: GithubRepo
    installation: Installation
    sender: GithubUser


class ReviewFinding(BaseModel):
    file: str
    line: int
    severity: str  # critical | high | medium | low | info
    category: str  # security | logic | performance | maintainability | style
    title: str
    body: str
    suggestion: str
    owasp_category: Optional[str] = None
    diff_position: int = 1
    cve_ids: list[str] = []
