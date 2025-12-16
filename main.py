import json
import time
import logging
import pandas as pd
import webbrowser
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
<<<<<<< HEAD
from typing import Dict, List, Any

from extractors.logo_extractor import LogoExtractor
from processors.image_processor import ImageProcessor
from matchers.similarity_matcher import SimilarityMatcher
from utils.visualizer import Visualizer

=======
from extractors.logo_extractor import LogoExtractor
from processors.image_processor import ImageProcessor
from matchers.similarity_matcher import SimilarityMatcher
from utils.visualizer import LogoVisualizer
>>>>>>> 263f18090b045b9ed02c9dfcf4ba34c611d456be

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
<<<<<<< HEAD

        self.extractor = LogoExtractor(workers=workers)
        self.processor = ImageProcessor(self.images)
        self.matcher = SimilarityMatcher(threshold=self.threshold)
        self.visualizer = Visualizer(self.output)

    def load(self, path: Path) -> List[str]:
        if not path.exists():
            return []
        try:
            if path.suffix == ".parquet":
                return pd.read_parquet(path).iloc[:, 0].dropna().unique().tolist()
            if path.suffix == ".csv":
                return pd.read_csv(path).iloc[:, 0].dropna().unique().tolist()
            return [l.strip() for l in path.read_text().splitlines() if l.strip()]
        except Exception:
            return []

    def save(self, groups: List[List[str]], logos: Dict[str, str], total: int):
        formatted_groups = [
            {
                "group_id": f"group_{i+1}",
                "size": len(g),
                "websites": [{"url": w, "logo_url": logos.get(w, "")} for w in g],
            }
            for i, g in enumerate(groups)
        ]

        out: Dict[str, Any] = {
            "metadata": {
                "total_input_websites": total,
                "extracted_logos": len(logos),
                "logo_groups_found": len(groups),
                "cnn_threshold": self.matcher.threshold,
                "color_threshold": self.matcher.color_threshold,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
            "groups": formatted_groups,
=======
        self.extractor = LogoExtractor()
        self.processor = ImageProcessor(self.images)
        self.matcher = SimilarityMatcher(threshold)
        self.visualizer = LogoVisualizer(self.output)

    def load(self, path: Path):
        if path.suffix == ".parquet":
            import pandas as pd
            return pd.read_parquet(path).iloc[:, 0].dropna().unique().tolist()
        if path.suffix == ".csv":
            import pandas as pd
            return pd.read_csv(path).iloc[:, 0].dropna().unique().tolist()
        return [l.strip() for l in path.read_text().splitlines() if l.strip()]

    def save(self, groups, logos, total):
        out = {
            "metadata": {"total": total, "extracted": len(logos), "groups": len(groups), "threshold": self.threshold, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")},
            "groups": [{"group_id": f"group_{i+1}", "size": len(g), "websites": [{"url": w, "logo": logos.get(w, "")} for w in g]} for i, g in enumerate(groups)]
>>>>>>> 263f18090b045b9ed02c9dfcf4ba34c611d456be
        }
        (self.output / "logo_groups.json").write_text(json.dumps(out, indent=2))
        logger.info(f"Results saved to {self.output / 'logo_groups.json'}")
        
        report_file = self.visualizer.generate([[g] for g in formatted_groups], total)
        logger.info(f"Visual report generated: {report_file}")
        
        try:
            webbrowser.open(report_file.absolute().as_uri()) 
        except Exception as e:
            logger.error(f"Could not open browser automatically: {e}")

    def run(self, path: Path):
        start = time.time()
        websites = self.load(path)
<<<<<<< HEAD
        total_websites = len(websites)
        
        if not websites:
            return

        logos: Dict[str, str] = {}
=======
        logos = {}
>>>>>>> 263f18090b045b9ed02c9dfcf4ba34c611d456be
        with ThreadPoolExecutor(self.workers) as ex:
            futures = {ex.submit(self.extractor.extract, w): w for w in websites}
            for f in tqdm(as_completed(futures), total=total_websites, desc="1/3 Extracting"):
                w = futures[f]
                r = f.result()
                if r:
                    logos[w] = r
<<<<<<< HEAD
        self.extractor.close() 

        image_map: Dict[str, Path] = {}
        download_targets = logos.items() 
        
        with ThreadPoolExecutor(self.workers) as ex:
            futures = {
                ex.submit(self.processor.download, w, u): w
                for w, u in download_targets
            }
            for f in tqdm(as_completed(futures), total=len(download_targets), desc="2/3 Downloading"):
=======
        image_map = {}
        with ThreadPoolExecutor(self.workers) as ex:
            futures = {ex.submit(self.processor.download, w, u): w for w, u in logos.items()}
            for f in tqdm(as_completed(futures), total=len(logos), desc="Downloading"):
>>>>>>> 263f18090b045b9ed02c9dfcf4ba34c611d456be
                w = futures[f]
                p = f.result()
                if p:
                    image_map[w] = p
<<<<<<< HEAD
        
        self.processor.close()

        if not image_map:
             self.save([], logos, total_websites)
             return
             
        enc = self.matcher.encode(self.images)
        dup = self.matcher.find_duplicates(enc)
        groups = self.matcher.cluster(dup, image_map)

        self.save(groups, logos, total_websites)
        logger.info(f"Done in {time.time() - start:.1f}s")

=======
        enc = self.matcher.encode(self.images)
        dup = self.matcher.find_duplicates(enc)
        groups = self.matcher.cluster(dup, image_map)
        self.save(groups, logos, len(websites))
        self.visualizer.save_all_groups(groups, image_map, top_n=20)
        self.extractor.cleanup()
        self.processor.cleanup()
        logger.info(f"Done in {time.time()-start:.1f}s")
>>>>>>> 263f18090b045b9ed02c9dfcf4ba34c611d456be

def main():
    import argparse
    p = argparse.ArgumentParser()
<<<<<<< HEAD
    p.add_argument("-i", "--input", required=True)
    p.add_argument("-o", "--output", default="output")
    p.add_argument("-w", "--workers", type=int, default=20)
    p.add_argument("-t", "--threshold", type=float, default=0.75) 
=======
    p.add_argument("-i","--input", required=True)
    p.add_argument("-o","--output", default="output")
    p.add_argument("-w","--workers", type=int, default=20)
    p.add_argument("-t","--threshold", type=float, default=0.92)
>>>>>>> 263f18090b045b9ed02c9dfcf4ba34c611d456be
    args = p.parse_args()
    LogoMatcher(Path(args.output), args.workers, args.threshold).run(Path(args.input))

if __name__ == "__main__":
    main()