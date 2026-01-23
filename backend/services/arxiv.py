"""ArXiv paper digest service with daily scheduling."""

import asyncio
import json
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

import httpx
from ..config import get_settings
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class Paper:
    """Represents an arXiv paper."""

    arxiv_id: str
    title: str
    abstract: str
    authors: list[str]
    categories: list[str]
    published: str
    updated: str
    link: str
    relevance_score: float = 0.0
    relevance_reason: str = ""


@dataclass
class DigestState:
    """Tracks digest generation state."""

    last_digest: datetime | None = None
    is_generating: bool = False
    errors: list[str] = field(default_factory=list)


# Global state
_digest_state = DigestState()


def get_digest_state() -> DigestState:
    """Get the current digest state."""
    return _digest_state


def _get_digest_dir() -> Path:
    """Get the directory for storing digests."""
    base = Path(settings.chroma_persist_directory).parent
    digest_dir = base / "arxiv" / "digests"
    digest_dir.mkdir(parents=True, exist_ok=True)
    return digest_dir


def _get_ranking_llm():
    """Get LLM for paper ranking (uses cheaper/faster models)."""
    provider = settings.arxiv_llm_provider

    if provider == "anthropic":
        return ChatAnthropic(
            model="claude-3-haiku-20240307",
            api_key=settings.anthropic_api_key,
            max_tokens=256,
        )
    elif provider == "openai":
        return ChatOpenAI(
            model="gpt-3.5-turbo",
            api_key=settings.openai_api_key,
            max_tokens=256,
        )
    elif provider == "google":
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=settings.google_api_key,
            max_output_tokens=256,
        )
    else:
        raise ValueError(f"Unknown arxiv_llm_provider: {provider}")


async def fetch_papers(categories: list[str], max_results: int = 50) -> list[Paper]:
    """Fetch recent papers from arXiv API for given categories."""
    papers = []

    # Build query for multiple categories (OR them together)
    cat_query = "+OR+".join([f"cat:{cat}" for cat in categories])
    url = (
        f"http://export.arxiv.org/api/query?"
        f"search_query={cat_query}&"
        f"sortBy=submittedDate&"
        f"sortOrder=descending&"
        f"max_results={max_results}"
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch arXiv papers: {e}")
            return papers

    # Parse XML response
    try:
        root = ET.fromstring(response.text)
        ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

        for entry in root.findall("atom:entry", ns):
            # Extract arxiv ID from the id URL
            id_url = entry.find("atom:id", ns).text
            arxiv_id = id_url.split("/abs/")[-1]

            # Get categories
            cats = [
                cat.get("term") for cat in entry.findall("atom:category", ns) if cat.get("term")
            ]

            paper = Paper(
                arxiv_id=arxiv_id,
                title=entry.find("atom:title", ns).text.strip().replace("\n", " "),
                abstract=entry.find("atom:summary", ns).text.strip().replace("\n", " "),
                authors=[a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)],
                categories=cats,
                published=entry.find("atom:published", ns).text,
                updated=entry.find("atom:updated", ns).text,
                link=f"https://arxiv.org/abs/{arxiv_id}",
            )
            papers.append(paper)

    except ET.ParseError as e:
        logger.error(f"Failed to parse arXiv XML: {e}")

    return papers


async def rank_paper(paper: Paper, interests: str, llm) -> Paper:
    """Rank a single paper's relevance to interests."""
    prompt = f"""Rate this paper's relevance to the following research interests on a scale of 1-10.
Be strict - only give 8+ for papers directly relevant to the interests.

Research interests: {interests}

Paper title: {paper.title}
Abstract: {paper.abstract[:1000]}

Respond with ONLY a JSON object in this exact format (no other text):
{{"score": <number 1-10>, "reason": "<brief 1-sentence explanation>"}}"""

    try:
        response = await llm.ainvoke(prompt)
        content = response.content.strip()

        # Extract JSON from response (handle markdown code blocks)
        if "```" in content:
            content = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
            content = content.group(1) if content else "{}"

        result = json.loads(content)
        paper.relevance_score = float(result.get("score", 0))
        paper.relevance_reason = result.get("reason", "")
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning(f"Failed to parse ranking for {paper.arxiv_id}: {e}")
        paper.relevance_score = 5.0
        paper.relevance_reason = "Unable to rank"

    return paper


async def rank_papers(papers: list[Paper], interests: str) -> list[Paper]:
    """Rank all papers by relevance to interests."""
    llm = _get_ranking_llm()

    # Rank papers in batches to avoid rate limits
    batch_size = 5
    ranked_papers = []

    for i in range(0, len(papers), batch_size):
        batch = papers[i : i + batch_size]
        tasks = [rank_paper(paper, interests, llm) for paper in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Paper):
                ranked_papers.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Ranking error: {result}")

        # Small delay between batches
        if i + batch_size < len(papers):
            await asyncio.sleep(1)

    # Sort by relevance score descending
    ranked_papers.sort(key=lambda p: p.relevance_score, reverse=True)
    return ranked_papers


async def generate_digest(
    categories: list[str] | None = None,
    interests: str | None = None,
    max_papers: int | None = None,
    top_n: int | None = None,
) -> dict:
    """Generate a daily arXiv digest.

    Returns dict with digest metadata and papers.
    """
    state = get_digest_state()

    if state.is_generating:
        return {"status": "already_generating"}

    state.is_generating = True
    state.errors = []

    # Use settings defaults if not provided
    categories = categories or settings.arxiv_categories
    interests = interests or settings.arxiv_interests
    max_papers = max_papers or settings.arxiv_max_papers
    top_n = top_n or settings.arxiv_top_n

    try:
        logger.info(f"Fetching papers from arXiv for categories: {categories}")
        papers = await fetch_papers(categories, max_papers)
        logger.info(f"Fetched {len(papers)} papers")

        if not papers:
            state.errors.append("No papers fetched from arXiv")
            return {"status": "error", "errors": state.errors}

        logger.info(f"Ranking papers against interests: {interests[:50]}...")
        ranked_papers = await rank_papers(papers, interests)

        # Take top N papers
        top_papers = ranked_papers[:top_n]

        # Build digest
        now = datetime.now(timezone.utc)
        digest = {
            "date": now.strftime("%Y-%m-%d"),
            "generated_at": now.isoformat(),
            "categories": categories,
            "interests": interests,
            "total_papers_fetched": len(papers),
            "papers": [
                {
                    "arxiv_id": p.arxiv_id,
                    "title": p.title,
                    "abstract": p.abstract,
                    "authors": p.authors,
                    "categories": p.categories,
                    "published": p.published,
                    "link": p.link,
                    "relevance_score": p.relevance_score,
                    "relevance_reason": p.relevance_reason,
                }
                for p in top_papers
            ],
        }

        # Save digest to file
        digest_dir = _get_digest_dir()
        digest_file = digest_dir / f"{digest['date']}.json"
        with open(digest_file, "w", encoding="utf-8") as f:
            json.dump(digest, f, indent=2)

        logger.info(f"Digest saved to {digest_file}")
        state.last_digest = now

        return {"status": "completed", "digest": digest}

    except Exception as e:
        logger.error(f"Digest generation error: {e}")
        state.errors.append(str(e))
        return {"status": "error", "errors": state.errors}
    finally:
        state.is_generating = False


def get_digest(date: str | None = None) -> dict | None:
    """Get a digest by date (YYYY-MM-DD format). Returns None if not found."""
    digest_dir = _get_digest_dir()

    if date is None:
        # Get the most recent digest
        digests = sorted(digest_dir.glob("*.json"), reverse=True)
        if not digests:
            return None
        digest_file = digests[0]
    else:
        digest_file = digest_dir / f"{date}.json"

    if not digest_file.exists():
        return None

    with open(digest_file, "r", encoding="utf-8") as f:
        return json.load(f)


def list_digests(limit: int = 30) -> list[str]:
    """List available digest dates."""
    digest_dir = _get_digest_dir()
    digests = sorted(digest_dir.glob("*.json"), reverse=True)[:limit]
    return [d.stem for d in digests]


class ArxivScheduler:
    """Background scheduler for daily arXiv digest generation."""

    def __init__(self):
        self._task: asyncio.Task | None = None
        self._running = False
        self._schedule_hour = settings.arxiv_schedule_hour

    def start(self, schedule_hour: int | None = None):
        """Start the background digest scheduler."""
        if self._running:
            return

        if schedule_hour is not None:
            self._schedule_hour = schedule_hour

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"ArXiv scheduler started (daily at {self._schedule_hour}:00 UTC)")

    def stop(self):
        """Stop the background scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("ArXiv scheduler stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    def _seconds_until_next_run(self) -> float:
        """Calculate seconds until next scheduled run."""
        now = datetime.now(timezone.utc)
        target = now.replace(hour=self._schedule_hour, minute=0, second=0, microsecond=0)

        if now >= target:
            # Already past today's schedule, run tomorrow
            target += timedelta(days=1)

        return (target - now).total_seconds()

    async def _run_loop(self):
        """Background loop for scheduled digest generation."""
        while self._running:
            try:
                # Wait until next scheduled time
                wait_seconds = self._seconds_until_next_run()
                logger.info(
                    f"ArXiv scheduler: next run in {wait_seconds / 3600:.1f} hours"
                )
                await asyncio.sleep(wait_seconds)

                if self._running:
                    logger.info("Running scheduled arXiv digest generation...")
                    result = await generate_digest()
                    logger.info(f"Scheduled digest completed: {result.get('status')}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"ArXiv scheduler error: {e}")
                # Sleep a bit before retrying on error
                await asyncio.sleep(3600)


# Global scheduler instance
_scheduler = ArxivScheduler()


def get_arxiv_scheduler() -> ArxivScheduler:
    """Get the global arXiv scheduler."""
    return _scheduler
