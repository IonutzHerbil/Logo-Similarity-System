import json
import os
import sys
from pathlib import Path
from typing import List, Dict
import logging
from tqdm import tqdm
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append(str(Path(__file__).parent))

from extractors.logo_extractor import LogoExtractor
from processors.image_processor import ImageProcessor
from processors.feature_extractor import FeatureExtractor
from matchers.similarity_matcher import SimilarityMatcher
from utils.data_reader import DataReader

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class LogoPipeline:
    def __init__(self, output_dir='output', cache_dir='logo_cache', 
                 max_extract_workers=20, max_process_workers=10,
                 eps=0.12, min_samples=2, use_selenium=True):
        
        self.output_dir = output_dir
        self.cache_dir = cache_dir
        
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(cache_dir, exist_ok=True)
        
        self.extractor = LogoExtractor(cache_dir=cache_dir, use_selenium=use_selenium)
        self.processor = ImageProcessor(cache_dir=cache_dir)
        self.feature_extractor = FeatureExtractor()
        self.matcher = SimilarityMatcher(eps=eps, min_samples=min_samples)
        
        self.max_extract_workers = max_extract_workers
        self.max_process_workers = max_process_workers
        
        logger.info(f"Pipeline initialized: extract_workers={max_extract_workers}, process_workers={max_process_workers}, eps={eps}")
    
    def load_websites(self, filepath):
        try:
            ext = Path(filepath).suffix.lower()
            
            if ext == '.parquet':
                websites = DataReader.read_parquet(filepath)
            elif ext == '.csv':
                websites = DataReader.read_csv(filepath)
            else:
                websites = DataReader.read_text_file(filepath)
            
            logger.info(f"Loaded {len(websites)} websites")
            return websites
        except Exception as e:
            logger.error(f"Failed to load websites: {e}")
            return []
    
    def extract_logos(self, websites):
        logger.info(f"Extracting logos from {len(websites)} websites...")
        print(f"\n{'='*80}\nPHASE 1: LOGO EXTRACTION\n{'='*80}\n")
        
        logo_urls = {}
        failed = []
        
        with ThreadPoolExecutor(max_workers=self.max_extract_workers) as executor:
            future_to_website = {
                executor.submit(self.extractor.extract_logo, w): w for w in websites
            }
            
            for future in tqdm(as_completed(future_to_website), total=len(websites), 
                             desc="Extracting", unit="site"):
                website = future_to_website[future]
                try:
                    logo_url = future.result(timeout=30)
                    if logo_url:
                        logo_urls[website] = logo_url
                    else:
                        failed.append(website)
                except:
                    failed.append(website)
        
        rate = len(logo_urls) / len(websites) * 100
        print(f"\n{'='*80}")
        print(f"EXTRACTION: {len(logo_urls)}/{len(websites)} ({rate:.1f}%)")
        print(f"{'='*80}\n")
        
        stats = self.extractor.get_statistics()
        if stats:
            print("Methods:")
            for method, data in stats.items():
                print(f"  {method}: {data['count']} ({data['percentage']:.1f}%)")
            print()
        
        if failed:
            with open(os.path.join(self.output_dir, 'failed_extractions.txt'), 'w') as f:
                f.write('\n'.join(failed))
        
        return logo_urls
    
    def process_logos(self, logo_urls):
        logger.info(f"Processing {len(logo_urls)} logos...")
        print(f"\n{'='*80}\nPHASE 2: FEATURE EXTRACTION\n{'='*80}\n")
        
        all_features = {}
        failed = []
        
        def process_single(item):
            website, logo_url = item
            try:
                result = self.processor.process_logo(logo_url)
                if result is None:
                    return website, None
                
                img, pil_img = result
                features = self.feature_extractor.extract_features(img, pil_img)
                
                return website, features
            except:
                return website, None
        
        with ThreadPoolExecutor(max_workers=self.max_process_workers) as executor:
            future_to_item = {
                executor.submit(process_single, item): item for item in logo_urls.items()
            }
            
            for future in tqdm(as_completed(future_to_item), total=len(logo_urls),
                             desc="Processing", unit="logo"):
                try:
                    website, features = future.result(timeout=60)
                    if features:
                        all_features[website] = features
                    else:
                        failed.append(website)
                except:
                    failed.append("unknown")
        
        rate = len(all_features) / len(logo_urls) * 100
        print(f"\n{'='*80}")
        print(f"PROCESSING: {len(all_features)}/{len(logo_urls)} ({rate:.1f}%)")
        print(f"{'='*80}\n")
        
        if failed:
            with open(os.path.join(self.output_dir, 'failed_processing.txt'), 'w') as f:
                f.write('\n'.join(failed))
        
        return all_features
    
    def compute_groups(self, all_features):
        logger.info("Computing similarity and clustering...")
        print(f"\n{'='*80}\nPHASE 3: CLUSTERING\n{'='*80}\n")
        
        urls = list(all_features.keys())
        features = [all_features[url] for url in urls]
        
        sim_matrix = self.matcher.create_similarity_matrix(features)
        groups = self.matcher.cluster_logos(sim_matrix, urls)
        
        print(f"\n{'='*80}")
        print(f"CLUSTERING: {len(groups)} groups")
        print(f"Largest: {len(groups[0]) if groups else 0} websites")
        print(f"Singletons: {sum(1 for g in groups if len(g) == 1)}")
        print(f"{'='*80}\n")
        
        return groups
    
    def save_results(self, groups, all_features, logo_urls, total_input):
        stats = self.matcher.compute_group_statistics(groups, all_features)
        
        for s in stats:
            for i, website in enumerate(s['websites']):
                s['websites'][i] = {
                    'url': website,
                    'logo_url': logo_urls.get(website, '')
                }
        
        ext_rate = (len(logo_urls) / total_input * 100) if total_input > 0 else 0
        
        output = os.path.join(self.output_dir, 'logo_groups.json')
        with open(output, 'w') as f:
            json.dump({
                'metadata': {
                    'total_input': total_input,
                    'extracted': len(logo_urls),
                    'extraction_rate': round(ext_rate, 2),
                    'processed': len(all_features),
                    'groups': len(groups),
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                },
                'groups': stats
            }, f, indent=2)
        
        logger.info(f"Results saved to {output}")
        
        self._save_summary(groups, total_input, len(logo_urls), all_features)
        self._save_distribution(groups)
    
    def _save_summary(self, groups, total, extracted, features):
        path = os.path.join(self.output_dir, 'summary.txt')
        
        size_counts = {}
        for g in groups:
            size = len(g)
            size_counts[size] = size_counts.get(size, 0) + 1
        
        with open(path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("LOGO MATCHING RESULTS\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Input: {total}\n")
            f.write(f"Extracted: {extracted} ({extracted/total*100:.1f}%)\n")
            f.write(f"Processed: {len(features)}\n")
            f.write(f"Groups: {len(groups)}\n\n")
            f.write("Distribution:\n")
            f.write("-" * 40 + "\n")
            for size in sorted(size_counts.keys(), reverse=True):
                f.write(f"  {size} websites: {size_counts[size]} groups\n")
            f.write("\nTop 20 Groups:\n")
            f.write("-" * 40 + "\n")
            for i, g in enumerate(groups[:20], 1):
                f.write(f"\nGroup {i} ({len(g)} websites):\n")
                for w in g[:10]:
                    f.write(f"  - {w}\n")
                if len(g) > 10:
                    f.write(f"  ... +{len(g)-10} more\n")
        
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Extracted: {extracted}/{total} ({extracted/total*100:.1f}%)")
        print(f"Processed: {len(features)}/{extracted} ({len(features)/extracted*100:.1f}%)")
        print(f"Groups: {len(groups)}")
        print(f"Largest: {len(groups[0])} websites" if groups else "0")
        print(f"Unique: {size_counts.get(1, 0)}")
        print("=" * 80 + "\n")
    
    def _save_distribution(self, groups):
        path = os.path.join(self.output_dir, 'distribution.json')
        
        counts = {}
        for g in groups:
            size = len(g)
            counts[size] = counts.get(size, 0) + 1
        
        with open(path, 'w') as f:
            json.dump({
                'total_groups': len(groups),
                'distribution': {str(k): v for k, v in sorted(counts.items(), reverse=True)}
            }, f, indent=2)
    
    def run(self, input_file):
        print("=" * 80)
        print("LOGO SIMILARITY MATCHER")
        print("=" * 80 + "\n")
        
        start = time.time()
        
        websites = self.load_websites(input_file)
        if not websites:
            return
        
        total = len(websites)
        
        logo_urls = self.extract_logos(websites)
        if not logo_urls:
            return
        
        features = self.process_logos(logo_urls)
        if not features:
            return
        
        groups = self.compute_groups(features)
        self.save_results(groups, features, logo_urls, total)
        
        self.extractor.cleanup()
        
        elapsed = time.time() - start
        print(f"\nCompleted in {elapsed:.1f}s ({elapsed/60:.1f}min)")
        print(f"Results: {self.output_dir}/\n")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Logo Similarity Matcher')
    parser.add_argument('--input', '-i', required=True, help='Input file')
    parser.add_argument('--output', '-o', default='output', help='Output directory')
    parser.add_argument('--eps', type=float, default=0.12, help='DBSCAN epsilon (lower=stricter)')
    parser.add_argument('--min-samples', type=int, default=2, help='DBSCAN min samples')
    parser.add_argument('--extract-workers', type=int, default=20, help='Extraction workers')
    parser.add_argument('--process-workers', type=int, default=10, help='Processing workers')
    parser.add_argument('--no-selenium', action='store_true', help='Disable Selenium')
    
    args = parser.parse_args()
    
    pipeline = LogoPipeline(
        output_dir=args.output,
        max_extract_workers=args.extract_workers,
        max_process_workers=args.process_workers,
        eps=args.eps,
        min_samples=args.min_samples,
        use_selenium=not args.no_selenium
    )
    
    pipeline.run(args.input)


if __name__ == '__main__':
    main()