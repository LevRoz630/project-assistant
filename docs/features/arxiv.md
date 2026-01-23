# ArXiv Paper Digest

The ArXiv digest feature provides daily summaries of relevant research papers from arXiv.org, ranked by AI based on your research interests.

## Overview

The service:

1. Fetches recent papers from specified arXiv categories
2. Uses AI to score each paper's relevance to your interests
3. Returns the top N papers with explanations
4. Can run on a daily schedule or on-demand

## Configuration

Set these environment variables in `.env`:

```bash
# arXiv category codes (comma-separated)
ARXIV_CATEGORIES=cs.AI,cs.CL,cs.LG,q-fin.ST,stat.ML

# Research interests for AI ranking
ARXIV_INTERESTS=AI agents, LLMs, NLP, quantitative finance, ML for trading

# UTC hour for daily digest (0-23)
ARXIV_SCHEDULE_HOUR=6

# Maximum papers to fetch per run
ARXIV_MAX_PAPERS=50

# Top N papers to include in digest
ARXIV_TOP_N=10

# LLM provider for ranking
ARXIV_LLM_PROVIDER=anthropic
```

### Category Codes

Common arXiv categories:

| Category | Description |
|----------|-------------|
| cs.AI | Artificial Intelligence |
| cs.CL | Computation and Language (NLP) |
| cs.LG | Machine Learning |
| cs.CV | Computer Vision |
| cs.NE | Neural and Evolutionary Computing |
| stat.ML | Machine Learning (Statistics) |
| q-fin.ST | Statistical Finance |
| q-fin.PM | Portfolio Management |
| econ.EM | Econometrics |

Full taxonomy: https://arxiv.org/category_taxonomy

### LLM Provider

The service uses fast, cost-effective models for ranking:

| Provider | Model Used |
|----------|------------|
| anthropic | claude-3-haiku-20240307 |
| openai | gpt-3.5-turbo |
| google | gemini-1.5-flash |

## API Endpoints

### Get Latest Digest

```http
GET /arxiv/digest
```

Returns the most recent digest or a message if none exists.

### Get Digest by Date

```http
GET /arxiv/digest/{date}
```

Parameters:
- `date`: YYYY-MM-DD format

### List Available Digests

```http
GET /arxiv/digests?limit=30
```

Returns list of available digest dates.

### Generate Digest Now

```http
POST /arxiv/run-now
```

Triggers immediate digest generation in background.

### Start Scheduler

```http
POST /arxiv/scheduler/start?schedule_hour=6
```

Starts daily background scheduler.

### Stop Scheduler

```http
POST /arxiv/scheduler/stop
```

### Get Status

```http
GET /arxiv/status
```

Returns:
```json
{
  "is_generating": false,
  "last_digest": "2024-01-15T06:00:00Z",
  "scheduler_running": true,
  "errors": []
}
```

### Get Configuration

```http
GET /arxiv/config
```

### Update Configuration

```http
PUT /arxiv/config
Content-Type: application/json

{
  "categories": ["cs.AI", "cs.LG"],
  "interests": "deep learning, transformers",
  "top_n": 5
}
```

Note: Runtime changes only. For persistent changes, update environment variables.

## Digest Format

Digests are saved as JSON files in `./data/arxiv/digests/`:

```json
{
  "date": "2024-01-15",
  "generated_at": "2024-01-15T06:00:00Z",
  "categories": ["cs.AI", "cs.CL"],
  "interests": "AI agents, LLMs",
  "total_papers_fetched": 50,
  "papers": [
    {
      "arxiv_id": "2401.12345",
      "title": "Paper Title",
      "abstract": "Abstract text...",
      "authors": ["Author One", "Author Two"],
      "categories": ["cs.AI", "cs.CL"],
      "published": "2024-01-14T00:00:00Z",
      "link": "https://arxiv.org/abs/2401.12345",
      "relevance_score": 9.0,
      "relevance_reason": "Directly addresses AI agent architectures"
    }
  ]
}
```

## How Ranking Works

1. Papers are fetched from arXiv API sorted by submission date
2. Each paper is sent to the LLM with this prompt:

```
Rate this paper's relevance to the following research interests on a scale of 1-10.
Be strict - only give 8+ for papers directly relevant to the interests.

Research interests: {interests}

Paper title: {title}
Abstract: {abstract}

Respond with ONLY a JSON object:
{"score": <number>, "reason": "<explanation>"}
```

3. Papers are sorted by score and top N are returned
4. Ranking happens in batches of 5 with 1-second delays to avoid rate limits

## Storage

Digests are stored in:
```
./data/arxiv/digests/
├── 2024-01-15.json
├── 2024-01-14.json
└── ...
```

The `./data` directory should be mounted as a persistent volume in production.

## Usage Examples

### Python

```python
import httpx

# Generate a digest
response = httpx.post("http://localhost:8000/arxiv/run-now")
print(response.json())

# Get latest digest
response = httpx.get("http://localhost:8000/arxiv/digest")
digest = response.json()

for paper in digest["papers"]:
    print(f"{paper['relevance_score']}: {paper['title']}")
    print(f"  {paper['link']}")
    print(f"  {paper['relevance_reason']}")
```

### Start Daily Scheduler

```bash
curl -X POST "http://localhost:8000/arxiv/scheduler/start?schedule_hour=6"
```

The scheduler runs in the background and generates a digest at the specified UTC hour.

## Troubleshooting

### No Papers Fetched

- Check arXiv API availability
- Verify category codes are correct
- Check network connectivity

### Low Relevance Scores

- Refine your `ARXIV_INTERESTS` to be more specific
- The AI is conservative - 8+ scores indicate direct relevance

### Rate Limiting

The service batches LLM calls and adds delays. If you still hit limits:
- Reduce `ARXIV_MAX_PAPERS`
- Increase batch delay in code

### Scheduler Not Running

- Check `GET /arxiv/status` for errors
- Ensure the backend process stays running
- Use a process manager (systemd, supervisord) in production
