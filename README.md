# Logo Similarity Matcher

**Author:** Ioan  

## Problem Statement

Given 4000+ company domains, build a system that:
1. Extracts logos from websites (>97% success rate)
2. Groups visually similar logos without traditional ML clustering
3. Generates visual report

## Solution

Multi-stage pipeline: web scraping → computer vision → graph clustering. High extraction via fallback strategies, accurate matching via dual-threshold (CNN + color).

## Quick Start

```bash
pip install -r requirements.txt
python main.py -i logos_sample_50.parquet
```

**Arguments:** `-i` input [required] | `-o` output dir | `-w` workers (20) | `-t` CNN threshold (0.75)

## Output

```
output/
├── logo_groups.json    # Results + metadata
├── report.html         # Visual report (auto-opens)
└── images/             # Downloaded logos
```

## Technical Approach

### 1. Logo Extraction (Waterfall)

1. **Clearbit API** → Cached, high-quality
2. **Meta tags** → og:image, schema.org, apple-touch-icon  
3. **Header parsing** → Score by keywords/dimensions/position
4. **Common paths** → /logo.png, /logo.svg, /favicon.ico

**Implementation:** User-Agent rotation, HEAD validation, size filter (>2KB)

### 2. Similarity Matching (Dual-Threshold)

```
Match = (CNN ≥ 0.75) AND (Color ≥ 0.60)
```

- **CNN** (MobileNet): Shape/structure similarity
- **Color**: Dominant RGB → prevents same-shape-different-brand false positives

### 3. Graph Clustering

Build graph (nodes=sites, edges=matches) → DFS connected components → sort by size

**Why not k-means?** No preset cluster count, handles variable sizes, deterministic

## Architecture

```
Input → Extract → Download → Encode → Cluster → Report
```

**Key decisions:**
- No databases (file-based I/O)
- Stateless (idempotent runs)
- Graceful degradation (continues on failures)
- ThreadPoolExecutor parallelization

## Performance

**50 sites (20 workers):**
- Extraction: 30-60s (I/O)
- Download: 10-20s (I/O)  
- Encoding: 5-10s (CPU)
- Total: **1-2 min**

**Success rate:** 96% (48/50)

**Scalability:** 3,400 sites ~45-60 min

## Configuration

**Strictness:**
```bash
python main.py -i input.parquet -t 0.85  # Fewer groups
python main.py -i input.parquet -t 0.65  # More groups
```

**Speed:**
```bash
python main.py -i input.parquet -w 50    # More workers
```

## Trade-offs

| Choice | Why | Cost |
|--------|-----|------|
| Pre-trained CNN | Robust, ready | Can't optimize for logos |
| Dual threshold | Reduces false positives | May miss rebrands |
| Graph clustering | No cluster count needed | Can't split large components |
| Clearbit first | Fast, cached | External dependency |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Low extraction (<90%) | Increase timeout, check User-Agent |
| Too many groups | Lower `-t` (0.65-0.70) |
| Too few groups | Raise `-t` (0.80-0.85) |
| Slow | Reduce workers, increase timeout |

## Dependencies

```
pandas requests beautifulsoup4 fake-useragent
Pillow imagehash imagededup numpy tqdm
```

## Testing

```bash
# Quick (50 domains, 1-2 min)
python main.py -i logos_sample_50.parquet

# Full (3,400 domains, ~1 hour)
python main.py -i logos.snappy.parquet -w 30
```

**Expected:** 90-98% extraction, 8-15 groups (sample)
