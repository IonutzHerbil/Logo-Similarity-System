import json
import time
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from extractors.logo_extractor import LogoExtractor
from processors.image_processor import ImageProcessor
from matchers.similarity_matcher import SimilarityMatcher


logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("logo-matcher")


class LogoMatcher:
    def __init__(self, output: Path, workers: int, threshold: float):
        self.output = output
        self.workers = workers
        self.threshold = threshold
        self.images = output / "images"

        self.output.mkdir(exist_ok=True)
        self.images.mkdir(exist_ok=True)

        self.extractor = LogoExtractor()
        self.processor = ImageProcessor(self.images)
        self.matcher = SimilarityMatcher(threshold)

    def load(self, path: Path) -> list[str]:
        if path.suffix == ".parquet":
            import pandas as pd
            return pd.read_parquet(path).iloc[:, 0].dropna().unique().tolist()
        if path.suffix == ".csv":
            import pandas as pd
            return pd.read_csv(path).iloc[:, 0].dropna().unique().tolist()
        return [l.strip() for l in path.read_text().splitlines() if l.strip()]

    def save(self, groups, logos, total):
        out = {
            "metadata": {
                "total": total,
                "extracted": len(logos),
                "groups": len(groups),
                "threshold": self.threshold,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
            "groups": [
                {
                    "group_id": f"group_{i+1}",
                    "size": len(g),
                    "websites": [{"url": w, "logo": logos.get(w, "")} for w in g],
                }
                for i, g in enumerate(groups)
            ],
        }

        (self.output / "logo_groups.json").write_text(json.dumps(out, indent=2))

    def run(self, path: Path):
        start = time.time()
        websites = self.load(path)

        logos = {}
        with ThreadPoolExecutor(self.workers) as ex:
            futures = {ex.submit(self.extractor.extract, w): w for w in websites}
            for f in tqdm(as_completed(futures), total=len(websites), desc="Extracting"):
                w = futures[f]
                r = f.result()
                if r:
                    logos[w] = r

        image_map = {}
        with ThreadPoolExecutor(self.workers) as ex:
            futures = {
                ex.submit(self.processor.download, w, u): w
                for w, u in logos.items()
            }
            for f in tqdm(as_completed(futures), total=len(logos), desc="Downloading"):
                w = futures[f]
                p = f.result()
                if p:
                    image_map[w] = p

        enc = self.matcher.encode(self.images)
        dup = self.matcher.find_duplicates(enc)
        groups = self.matcher.cluster(dup, image_map)

        self.save(groups, logos, len(websites))

        self.extractor.close()
        self.processor.close()

        logger.info(f"Done in {time.time() - start:.1f}s")


def main():
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("-i", "--input", required=True)
    p.add_argument("-o", "--output", default="output")
    p.add_argument("-w", "--workers", type=int, default=20)
    p.add_argument("-t", "--threshold", type=float, default=0.92)
    args = p.parse_args()

    LogoMatcher(Path(args.output), args.workers, args.threshold).run(Path(args.input))


if __name__ == "__main__":
    main()
