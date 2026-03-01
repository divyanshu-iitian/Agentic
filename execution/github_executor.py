"""
GitHub Executor

Wraps the GithubAgent's SmartContributor to handle GitHub-related tasks:
- Open source contributions
- Creating PRs
- Searching projects
- Repository analysis

This executor delegates GitHub operations to the specialized GithubAgent.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional
from utils.logger import log

# Add GithubAgent to path
github_agent_path = Path(__file__).parent.parent / "GithubAgent"
if str(github_agent_path) not in sys.path:
    sys.path.insert(0, str(github_agent_path))


class GitHubExecutor:
    """Executor for GitHub-related operations."""
    
    def __init__(self):
        """Initialize GitHub executor."""
        self.contributor = None
        self._initialized = False
        log.info("GitHub executor initialized (lazy loading)")
    
    def _ensure_initialized(self):
        """Lazy initialize the SmartContributor."""
        if self._initialized:
            return
        
        try:
            from smart_opensource_contributor import SmartContributor
            self.contributor = SmartContributor()
            self._initialized = True
            log.info("✅ SmartContributor loaded successfully")
        except Exception as e:
            log.error(f"Failed to initialize SmartContributor: {e}")
            raise
    
    def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a GitHub action.
        
        Args:
            action: Action name (github_contribute, github_search_projects, etc.)
            params: Action parameters
        
        Returns:
            Execution result
        """
        try:
            self._ensure_initialized()
            
            if action == "github_contribute":
                return self._contribute_to_opensource(params)
            elif action == "github_search_projects":
                return self._search_projects(params)
            elif action == "github_create_pr":
                return self._create_pr(params)
            else:
                raise ValueError(f"Unknown GitHub action: {action}")
        
        except Exception as e:
            log.error(f"GitHub action '{action}' failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _contribute_to_opensource(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make an open source contribution.
        
        Params:
            - project_name (optional): Specific project to contribute to
            - focus_area (optional): What kind of contribution (bug, feature, docs, etc.)
            - max_contributions (optional): How many contributions to make (default: 1)
        """
        log.info("🚀 Starting open source contribution workflow")
        
        project_name = params.get("project_name")
        focus_area = params.get("focus_area", "any")
        max_contributions = params.get("max_contributions", 1)
        
        try:
            if project_name:
                # Contribute to specific project
                log.info(f"Contributing to specific project: {project_name}")
                result = self.contributor.contribute_to_project(project_name)
            else:
                # Search and contribute to best match
                log.info(f"Searching for projects (focus: {focus_area})")
                projects = self.contributor.search_meaningful_projects()
                
                if not projects:
                    return {
                        "success": False,
                        "error": "No suitable projects found"
                    }
                
                # Contribute to best project
                contributions_made = 0
                results = []
                
                for project in projects[:max_contributions]:
                    try:
                        repo_full_name = project.get("full_name")
                        log.info(f"Attempting contribution to: {repo_full_name}")
                        
                        result = self.contributor.contribute_to_project(repo_full_name)
                        results.append(result)
                        
                        if result.get("success"):
                            contributions_made += 1
                    except Exception as e:
                        log.warning(f"Failed to contribute to {repo_full_name}: {e}")
                        continue
                
                return {
                    "success": contributions_made > 0,
                    "contributions_made": contributions_made,
                    "details": results
                }
        
        except Exception as e:
            log.error(f"Contribution workflow failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _search_projects(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for GitHub projects.
        
        Params:
            - query (optional): Search query
            - language (optional): Programming language filter
            - min_stars (optional): Minimum stars
            - max_stars (optional): Maximum stars
        """
        log.info("🔍 Searching GitHub projects")
        
        try:
            projects = self.contributor.search_meaningful_projects()
            
            return {
                "success": True,
                "projects": [
                    {
                        "name": p.get("full_name"),
                        "description": p.get("description", ""),
                        "stars": p.get("stargazers_count", 0),
                        "language": p.get("language", ""),
                        "url": p.get("html_url", "")
                    }
                    for p in projects[:10]  # Top 10
                ]
            }
        
        except Exception as e:
            log.error(f"Project search failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _create_pr(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a pull request.
        
        Params:
            - repo: Repository (owner/name)
            - title: PR title
            - description: PR description
            - branch: Source branch
        """
        log.info("📝 Creating pull request")
        
        repo = params.get("repo")
        title = params.get("title")
        description = params.get("description")
        branch = params.get("branch", "main")
        
        if not repo or not title:
            return {
                "success": False,
                "error": "Missing required parameters: repo, title"
            }
        
        try:
            # Use contributor's GitHub manager
            result = self.contributor.github.create_pull_request(
                repo=repo,
                title=title,
                body=description,
                head=branch,
                base="main"
            )
            
            return {
                "success": True,
                "pr_url": result.get("html_url", ""),
                "pr_number": result.get("number", 0)
            }
        
        except Exception as e:
            log.error(f"PR creation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Module-level instance
_executor = None

def get_github_executor() -> GitHubExecutor:
    """Get or create the GitHub executor singleton."""
    global _executor
    if _executor is None:
        _executor = GitHubExecutor()
    return _executor
