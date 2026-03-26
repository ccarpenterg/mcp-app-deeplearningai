import arxiv
import json
import os
from typing import List
from mcp.server.fastmcp import FastMCP


PAPER_DIR = "papers"

# Initialize FastMCP server
mcp = FastMCP("research")

@mcp.tool()
def search_papers(topic: str, max_results: int = 5) -> List[str]:
    """
    Search for papers on arXiv based on a topic and store their information.

    Args:
        topic (str): The topic to search for.
        max_results (int): The maximum number of results to return.

    Returns:
        List[str]: A list of paper IDs.
    """
    # Initialize arxiv client
    client = arxiv.Client()

    # Create topic directory under PAPER_DIR
    topic_dir = os.path.join(PAPER_DIR, topic)
    os.makedirs(topic_dir, exist_ok=True)

    # Path to papers_info.json
    papers_info_path = os.path.join(topic_dir, "papers_info.json")

    # Load existing papers info if file exists
    try:
        with open(papers_info_path, "r") as f:
            papers_info = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        papers_info = {}

    # Search for papers on arxiv
    search = arxiv.Search(
        query=topic,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance
    )

    results = []
    for result in client.results(search):
        paper_id = result.get_short_id()
        paper_info = {
            "title": result.title,
            "authors": [author.name for author in result.authors],
            "summary": result.summary,
            "published": result.published.isoformat(),
            "arxiv_url": result.entry_id
        }
        papers_info[paper_id] = paper_info
        results.append(paper_id)

    # Save papers info to JSON file
    with open(papers_info_path, "w") as json_file:
        json.dump(papers_info, json_file, indent=2)

    return results