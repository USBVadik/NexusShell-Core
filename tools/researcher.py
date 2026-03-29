"""
tools/researcher.py — USBAGENT Deep Research Engine v5.0.1

Pipeline:
  1. Use Gemini Google Search grounding to resolve the query and extract
     the top source URLs from grounding metadata.
  2. Asynchronously scrape the top-3 URLs in parallel (via web_parser).
  3. Synthesize all scraped content + the model's own grounded answer into
     a single structured ResearchResult that the /research handler can
     pass straight to the LLM for a final, cited answer.

Usage:
    from tools.researcher import deep_research
    result = await deep_research("latest MacBook M4 Pro benchmarks")
    # result.summary  — Gemini's grounded answer
    # result.sources  — list of SourceDoc(url, title, snippet)
    # result.context_block — ready-to-inject LLM context string
"""

import asyncio
import re
from dataclasses import dataclass, field
from typing import Optional

from google.genai import types

from config import STABLE_MODEL
from core.brain import _gemini_manager
from core.logger import brain_logger
from tools.web_parser import scrape_text

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SourceDoc:
    url: str
    title: str
    snippet: str          # scraped text (truncated)
    fetch_ok: bool = True


@dataclass
class ResearchResult:
    query: str
    summary: str                        # Gemini's own grounded answer
    sources: list[SourceDoc] = field(default_factory=list)
    context_block: str = ''             # formatted block ready for LLM injection
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_URL_RE = re.compile(r'https?://[^\s\)\]"\'<>]+')

# How many top sources to scrape
_TOP_N_SOURCES = 3

# Max chars per scraped source injected into context
_MAX_SNIPPET_CHARS = 4000


def _extract_urls_from_grounding(response) -> list[str]:
    """
    Pull source URLs out of a Gemini grounding-metadata response object.
    Falls back to regex scanning the raw text if metadata is absent.
    """
    urls: list[str] = []

    try:
        # Official path: candidates[0].grounding_metadata.grounding_chunks
        meta = response.candidates[0].grounding_metadata
        chunks = getattr(meta, 'grounding_chunks', None) or []
        for chunk in chunks:
            web = getattr(chunk, 'web', None)
            if web:
                uri = getattr(web, 'uri', None)
                if uri and uri not in urls:
                    urls.append(uri)
    except Exception:
        pass

    # Secondary path: search_entry_point rendered content sometimes has URLs
    if not urls:
        try:
            entry = (
                response.candidates[0]
                .grounding_metadata
                .search_entry_point
                .rendered_content
            )
            for m in _URL_RE.finditer(entry or ''):
                u = m.group(0).rstrip('.,;)')
                if u not in urls:
                    urls.append(u)
        except Exception:
            pass

    # Last resort: scan the raw answer text
    if not urls and response.text:
        for m in _URL_RE.finditer(response.text):
            u = m.group(0).rstrip('.,;)')
            if u not in urls:
                urls.append(u)

    return urls[:_TOP_N_SOURCES]


def _title_from_url(url: str) -> str:
    """Derive a human-readable title from a URL as a fallback."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        host = parsed.netloc.replace('www.', '')
        path = parsed.path.strip('/').replace('-', ' ').replace('_', ' ')
        parts = [p for p in path.split('/') if p]
        label = parts[-1] if parts else host
        return f"{host} — {label}" if label != host else host
    except Exception:
        return url


async def _scrape_one(url: str) -> SourceDoc:
    """Fetch and scrape a single URL, returning a SourceDoc."""
    brain_logger.debug(f"[Researcher] Scraping: {url}")
    try:
        text = await scrape_text(url, max_chars=_MAX_SNIPPET_CHARS)
        if text:
            brain_logger.info(f"[Researcher] Scraped {len(text)} chars from {url}")
            return SourceDoc(
                url=url,
                title=_title_from_url(url),
                snippet=text,
                fetch_ok=True,
            )
        else:
            brain_logger.warning(f"[Researcher] Empty scrape for {url}")
            return SourceDoc(
                url=url,
                title=_title_from_url(url),
                snippet='',
                fetch_ok=False,
            )
    except Exception as e:
        brain_logger.error(f"[Researcher] Scrape error for {url}: {e}", exc_info=True)
        return SourceDoc(
            url=url,
            title=_title_from_url(url),
            snippet='',
            fetch_ok=False,
        )


def _build_context_block(
    query: str,
    summary: str,
    sources: list[SourceDoc],
) -> str:
    """
    Assemble a structured context block that can be injected verbatim into
    a follow-up LLM prompt for synthesis / citation.
    """
    lines = [
        "=== DEEP RESEARCH CONTEXT ===",
        f"QUERY: {query}",
        "",
        "--- GROUNDED SUMMARY (Gemini Search) ---",
        summary.strip(),
        "",
    ]

    good_sources = [s for s in sources if s.fetch_ok and s.snippet]
    if good_sources:
        lines.append("--- SCRAPED SOURCE CONTENT ---")
        for i, src in enumerate(good_sources, 1):
            lines.append(f"\n[SOURCE {i}] {src.title}")
            lines.append(f"URL: {src.url}")
            lines.append(src.snippet)
            lines.append("")

    lines.append("=== END RESEARCH CONTEXT ===")
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def deep_research(query: str) -> ResearchResult:
    """
    Run the full Deep Research pipeline for *query*.

    Steps:
      1. Gemini Google Search grounding call → grounded summary + source URLs
      2. Parallel async scrape of top-3 URLs
      3. Assemble ResearchResult with context_block ready for LLM injection

    Never raises — errors are captured in ResearchResult.error.
    """
    brain_logger.info(f"[Researcher] Starting deep research for: {query!r}")

    # ------------------------------------------------------------------
    # Step 1: Grounded search via Gemini
    # ------------------------------------------------------------------
    try:
        grounded_response = await _gemini_manager.generate_with_retry(
            model=STABLE_MODEL,
            contents=query,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.2,
            ),
        )
        summary = (grounded_response.text or '').strip()
        brain_logger.info(
            f"[Researcher] Grounded summary: {len(summary)} chars"
        )
    except Exception as e:
        brain_logger.error(f"[Researcher] Grounded search failed: {e}", exc_info=True)
        return ResearchResult(
            query=query,
            summary='',
            error=f"Grounded search failed: {e}",
        )

    # ------------------------------------------------------------------
    # Step 2: Extract source URLs from grounding metadata
    # ------------------------------------------------------------------
    urls = _extract_urls_from_grounding(grounded_response)
    brain_logger.info(f"[Researcher] Extracted {len(urls)} source URLs: {urls}")

    # ------------------------------------------------------------------
    # Step 3: Parallel scrape of top-N sources
    # ------------------------------------------------------------------
    sources: list[SourceDoc] = []
    if urls:
        tasks = [_scrape_one(url) for url in urls[:_TOP_N_SOURCES]]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, SourceDoc):
                sources.append(r)
            else:
                brain_logger.error(f"[Researcher] Unexpected gather result: {r}")

    scraped_ok = sum(1 for s in sources if s.fetch_ok and s.snippet)
    brain_logger.info(
        f"[Researcher] Scraping complete: {scraped_ok}/{len(sources)} sources OK"
    )

    # ------------------------------------------------------------------
    # Step 4: Assemble result
    # ------------------------------------------------------------------
    context_block = _build_context_block(query, summary, sources)

    return ResearchResult(
        query=query,
        summary=summary,
        sources=sources,
        context_block=context_block,
    )
