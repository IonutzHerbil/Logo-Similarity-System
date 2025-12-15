import json
import os
import sys
from pathlib import Path
from typing import List, Dict
import logging
from tqdm import tqdm
import time

sys.path.append(str(Path(__file__).parent))

from extractors.logo_extractor import LogoExtractor
from processors.image_processor import ImageProcessor
from processors.feature_extractor import FeatureExtractor
from matchers.similarity_matcher import SimilarityMatcher
from utils.data_reader import DataReader

logging.basicConfig(
    level=logging.WARNING,  
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) 


class LogoMatchingPipeline:
    def __init__(self, 
                 output_dir: str = 'output',
                 cache_dir: str = 'logo_cache',
                 similarity_threshold: float = 0.15):
        self.output_dir = output_dir
        self.cache_dir = cache_dir
        
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(cache_dir, exist_ok=True)
        
        self.extractor = LogoExtractor()
        self.processor = ImageProcessor(cache_dir=cache_dir)
        self.feature_extractor = FeatureExtractor()
        self.matcher = SimilarityMatcher(similarity_threshold=similarity_threshold)
        
        logger.info("Pipeline initialized")
    
    def load_website_list(self, filepath: str) -> List[str]:
        try:
            file_ext = Path(filepath).suffix.lower()
            
            if file_ext == '.parquet':
                websites = DataReader.read_parquet(filepath)
            elif file_ext == '.csv':
                websites = DataReader.read_csv(filepath)
            else:
                websites = DataReader.read_text_file(filepath)
            
            logger.info(f"Loaded {len(websites)} websites from {filepath}")
            return websites
        except Exception as e:
            logger.error(f"Failed to load website list: {e}")
            return []
    
    def extract_logos(self, websites: List[str]) -> Dict[str, str]:
        logger.info(f"Starting logo extraction for {len(websites)} websites...")
        
        logo_urls = {}
        failed = []
        
        for website in tqdm(websites, desc="Extracting logos", unit="site"):
            try:
                logo_url = self.extractor.extract_logo(website)
                if logo_url:
                    logo_urls[website] = logo_url
                else:
                    failed.append(website)
                
                time.sleep(0.01) 
            except Exception as e:
                logger.debug(f"Error extracting logo for {website}: {e}")
                failed.append(website)
        
        extraction_rate = len(logo_urls) / len(websites) * 100
        logger.info(f"Logo extraction complete: {len(logo_urls)}/{len(websites)} ({extraction_rate:.1f}%)")
        
        if failed:
            with open(os.path.join(self.output_dir, 'failed_extractions.txt'), 'w') as f:
                f.write('\n'.join(failed))
        
        return logo_urls
    
    def process_and_extract_features(self, logo_urls: Dict[str, str]) -> Dict[str, Dict]:
        logger.info(f"Processing and extracting features for {len(logo_urls)} logos...")
        
        all_features = {}
        failed = []
        
        for website, logo_url in tqdm(logo_urls.items(), desc="Processing logos", unit="logo"):
            try:
                result = self.processor.process_logo(logo_url)
                if result is None:
                    failed.append(website)
                    continue
                
                processed_img, pil_img = result
                
                features = self.feature_extractor.extract_features(processed_img, pil_img)
                if features:
                    all_features[website] = features
                else:
                    failed.append(website)
                
            except Exception as e:
                logger.debug(f"Error processing {website}: {e}")
                failed.append(website)
        
        logger.info(f"Feature extraction complete: {len(all_features)}/{len(logo_urls)} logos processed")
        
        if failed:
            with open(os.path.join(self.output_dir, 'failed_processing.txt'), 'w') as f:
                f.write('\n'.join(failed))
        
        return all_features
    
    def compute_groups(self, all_features: Dict[str, Dict]) -> List[List[str]]:
        logger.info("Computing similarity matrix...")
        
        website_urls = list(all_features.keys())
        features_list = [all_features[url] for url in website_urls]
        
        similarity_matrix = self.matcher.create_similarity_matrix(features_list)
        
        logger.info("Performing threshold-based clustering...")
        groups = self.matcher.threshold_based_clustering(similarity_matrix, website_urls)
        
        logger.info(f"Clustering complete: {len(groups)} groups formed")
        
        return groups
    
    def save_results(self, 
                    groups: List[List[str]], 
                    all_features: Dict[str, Dict],
                    logo_urls: Dict[str, str],
                    total_input_websites: int):
        
        group_stats = self.matcher.compute_group_statistics(groups, all_features)
        
        for stats in group_stats:
            for i, website in enumerate(stats['websites']):
                stats['websites'][i] = {
                    'url': website,
                    'logo_url': logo_urls.get(website, '')
                }
        
        extraction_rate = (len(logo_urls) / total_input_websites * 100) if total_input_websites > 0 else 0
        
        output_path = os.path.join(self.output_dir, 'logo_groups.json')
        with open(output_path, 'w') as f:
            json.dump({
                'total_input_websites': total_input_websites,
                'successfully_extracted': len(logo_urls),
                'extraction_rate_percent': round(extraction_rate, 2),
                'total_groups': len(groups),
                'groups': group_stats
            }, f, indent=2)
        
        logger.info(f"Results saved to {output_path}")
        
        self._save_summary(groups, total_input_websites, len(logo_urls), all_features)
    
    def _save_summary(self, groups: List[List[str]], total_input: int, extracted: int, all_features: Dict):
        summary_path = os.path.join(self.output_dir, 'summary.txt')
        
        with open(summary_path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("LOGO MATCHING RESULTS SUMMARY\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Total input websites: {total_input}\n")
            f.write(f"Successfully extracted logos: {extracted}\n")
            f.write(f"Extraction rate: {extracted/total_input*100:.2f}%\n")
            f.write(f"Total groups formed: {len(groups)}\n\n")
            
            f.write("Group Size Distribution:\n")
            f.write("-" * 40 + "\n")
            size_counts = {}
            for group in groups:
                size = len(group)
                size_counts[size] = size_counts.get(size, 0) + 1
            
            for size in sorted(size_counts.keys(), reverse=True):
                f.write(f"  Groups with {size} website(s): {size_counts[size]}\n")
            
            f.write("\n")
            f.write("Top 10 Largest Groups:\n")
            f.write("-" * 40 + "\n")
            for i, group in enumerate(groups[:10], 1):
                f.write(f"\nGroup {i} ({len(group)} websites):\n")
                for website in group[:5]:
                    f.write(f"  - {website}\n")
                if len(group) > 5:
                    f.write(f"  ... and {len(group) - 5} more\n")
        
        logger.info(f"Summary saved to {summary_path}")
        print("\n" + "=" * 80)
        print("RESULTS SUMMARY")
        print("=" * 80)
        print(f"Extraction Rate: {extracted}/{total_input} ({extracted/total_input*100:.1f}%)")
        print(f"Total Groups: {len(groups)}")
        print(f"Largest Group: {len(groups[0])} websites" if groups else "No groups")
        print(f"Unique Logos: {size_counts.get(1, 0)}")
        print("=" * 80 + "\n")
    
    def run(self, website_list_file: str):
        print("=" * 80)
        print("LOGO MATCHING PIPELINE - OPTIMIZED VERSION")
        print("=" * 80)
        
        start_time = time.time()
        
        websites = self.load_website_list(website_list_file)
        if not websites:
            logger.error("No websites to process!")
            return
        
        total_input = len(websites)
        print(f"Processing {total_input} websites...\n")
        
        logo_urls = self.extract_logos(websites)
        if not logo_urls:
            logger.error("No logos extracted!")
            return
        
        all_features = self.process_and_extract_features(logo_urls)
        if not all_features:
            logger.error("No features extracted!")
            return
        
        groups = self.compute_groups(all_features)
        
        self.save_results(groups, all_features, logo_urls, total_input)
        
        elapsed = time.time() - start_time
        print(f"Pipeline completed in {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        print(f"Results saved to {self.output_dir}/")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Logo Similarity Matcher - Optimized')
    parser.add_argument('--input', '-i', required=True, 
                       help='Input file (.parquet, .csv, or .txt)')
    parser.add_argument('--output', '-o', default='output', help='Output directory')
    parser.add_argument('--threshold', '-t', type=float, default=0.15,
                       help='Similarity threshold (0-1, lower = stricter)')
    
    args = parser.parse_args()
    
    pipeline = LogoMatchingPipeline(
        output_dir=args.output,
        similarity_threshold=args.threshold
    )
    
    pipeline.run(args.input)


if __name__ == '__main__':
    main()
