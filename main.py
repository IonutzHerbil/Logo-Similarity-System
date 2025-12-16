#!/usr/bin/env python3
from __future__ import annotations
import json
import time
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from extractors.logo_extractor import LogoExtractor
from processors.image_processor import ImageProcessor
from matchers.similarity_matcher import SimilarityMatcher

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class LogoMatcher:
    def __init__(self, output: Path, workers: int = 20, threshold: float = 0.88):
        self.output = output
        self.workers = workers
        self.threshold = threshold
        self.images = output / "images"
        
        self.output.mkdir(exist_ok=True)
        
        self.extractor = LogoExtractor()
        self.processor = ImageProcessor(self.images)
        self.matcher = SimilarityMatcher(threshold)
        
        logger.info(f"Init: workers={workers}, threshold={threshold}")
    
    def load(self, path: Path) -> list[str]:
        ext = path.suffix.lower()
        
        if ext == ".parquet":
            import pandas as pd
            df = pd.read_parquet(path)
            return df.iloc[:, 0].unique().tolist()
        elif ext == ".csv":
            import pandas as pd
            df = pd.read_csv(path)
            return df.iloc[:, 0].unique().tolist()
        else:
            return [line.strip() for line in path.read_text().splitlines() if line.strip()]
    
    def save(self, groups: list[list[str]], logos: dict, total: int):
        out = {
            "metadata": {
                "total": total,
                "extracted": len(logos),
                "groups": len(groups),
                "threshold": self.threshold,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "groups": [
                {
                    "group_id": f"group_{i+1}",
                    "size": len(g),
                    "websites": [{"url": w, "logo": logos.get(w, "")} for w in g]
                }
                for i, g in enumerate(groups)
            ]
        }
        
        (self.output / "logo_groups.json").write_text(json.dumps(out, indent=2))
        
        with (self.output / "summary.txt").open("w") as f:
            f.write("=" * 80 + "\n")
            f.write("LOGO MATCHING RESULTS\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Input: {total}\n")
            f.write(f"Extracted: {len(logos)}\n")
            f.write(f"Groups: {len(groups)}\n")
            f.write(f"Threshold: {self.threshold}\n\n")
            f.write("Top Groups:\n")
            f.write("-" * 40 + "\n")
            for i, g in enumerate(groups[:20], 1):
                f.write(f"\nGroup {i} ({len(g)} websites):\n")
                for w in g[:10]:
                    f.write(f"  - {w}\n")
                if len(g) > 10:
                    f.write(f"  ... +{len(g)-10} more\n")
    
    def run(self, path: Path):
        print("=" * 80)
        print("LOGO SIMILARITY MATCHER")
        print("=" * 80 + "\n")
        
        start = time.time()
        
        websites = self.load(path)
        
        print(f"\n{'=' * 80}\nPHASE 1: EXTRACTION\n{'=' * 80}\n")
        logos = {}
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            futures = {ex.submit(self.extractor.extract, w): w for w in websites}
            for f in tqdm(as_completed(futures), total=len(websites), desc="Extracting"):
                w = futures[f]
                try:
                    url = f.result(timeout=30)
                    if url:
                        logos[w] = url
                except:
                    pass
        
        print(f"\nExtracted: {len(logos)}/{len(websites)} ({len(logos)/len(websites)*100:.1f}%)\n")
        
        print(f"\n{'=' * 80}\nPHASE 2: DOWNLOAD\n{'=' * 80}\n")
        image_map = {}
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            futures = {ex.submit(self.processor.download, w, url): w for w, url in logos.items()}
            for f in tqdm(as_completed(futures), total=len(logos), desc="Downloading"):
                w = futures[f]
                try:
                    p = f.result(timeout=30)
                    if p:
                        image_map[w] = p
                except:
                    pass
        
        print(f"\nDownloaded: {len(image_map)}/{len(logos)} ({len(image_map)/len(logos)*100:.1f}%)\n")
        
        print(f"\n{'=' * 80}\nPHASE 3: SIMILARITY\n{'=' * 80}\n")
        print("Encoding with CNN...")
        
        enc = self.matcher.encode_images(str(self.images))
        
        print(f"Finding duplicates...")
        dup = self.matcher.find_duplicates(enc, 0.80)
        
        groups = self.matcher.cluster(dup, image_map)
        
        print(f"\nGroups: {len(groups)}")
        print(f"Largest: {len(groups[0]) if groups else 0}\n")
        
        self.save(groups, logos, len(websites))
        
        self.extractor.cleanup()
        self.processor.cleanup()
        
        elapsed = time.time() - start
        print(f"\nCompleted in {elapsed:.1f}s ({elapsed/60:.1f}min)")
        print(f"Results: {self.output}/\n")


def main():
    import argparse
    
    p = argparse.ArgumentParser(description="Logo Similarity Matcher")
    p.add_argument("-i", "--input", required=True, help="Input file")
    p.add_argument("-o", "--output", default="output", help="Output dir")
    p.add_argument("-w", "--workers", type=int, default=20, help="Workers")
    p.add_argument("-t", "--threshold", type=float, default=0.88, help="Similarity threshold")
    
    args = p.parse_args()
    
    matcher = LogoMatcher(Path(args.output), args.workers, args.threshold)
    matcher.run(Path(args.input))


if __name__ == "__main__":
    main()