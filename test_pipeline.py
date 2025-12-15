import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
from extractors.logo_extractor import LogoExtractor
from processors.image_processor import ImageProcessor
from processors.feature_extractor import FeatureExtractor
from matchers.similarity_matcher import SimilarityMatcher

def test_logo_extraction():
    print("Testing Logo Extraction...")
    print("-" * 50)
    
    extractor = LogoExtractor()
    test_sites = ["microsoft.com", "apple.com", "google.com"]
    
    results = {}
    for site in test_sites:
        print(f"\nExtracting logo for {site}...")
        logo_url = extractor.extract_logo(site)
        if logo_url:
            print(f"  Found: {logo_url}")
            results[site] = logo_url
        else:
            print(f"  Not found")
    
    print(f"\nExtraction Rate: {len(results)}/{len(test_sites)}")
    return results

def test_image_processing(logo_urls):
    print("\n\nTesting Image Processing...")
    print("-" * 50)
    
    processor = ImageProcessor()
    processed = {}
    
    for site, logo_url in logo_urls.items():
        print(f"\nProcessing {site}...")
        result = processor.process_logo(logo_url)
        if result:
            processed_img, pil_img = result
            print(f"  Processed: shape={processed_img.shape}")
            processed[site] = (processed_img, pil_img)
        else:
            print(f"  Processing failed")
    
    print(f"\nProcessing Rate: {len(processed)}/{len(logo_urls)}")
    return processed

def test_feature_extraction(processed_images):
    print("\n\nTesting Feature Extraction...")
    print("-" * 50)
    
    extractor = FeatureExtractor()
    features = {}
    
    for site, (img, pil_img) in processed_images.items():
        print(f"\nExtracting features for {site}...")
        feat = extractor.extract_features(img, pil_img)
        if feat:
            print(f"  Extracted features:")
            print(f"    - Color histogram: {len(feat.get('color_hist', []))} dims")
            print(f"    - HOG: {len(feat.get('hog', []))} dims")
            print(f"    - pHash: {feat.get('phash', 'N/A')}")
            features[site] = feat
        else:
            print(f"  Feature extraction failed")
    
    print(f"\nFeature Extraction Rate: {len(features)}/{len(processed_images)}")
    return features

def test_similarity_computation(features):
    print("\n\nTesting Similarity Computation...")
    print("-" * 50)
    
    matcher = SimilarityMatcher()
    sites = list(features.keys())
    
    if len(sites) >= 2:
        for i in range(len(sites)):
            for j in range(i+1, len(sites)):
                site_a = sites[i]
                site_b = sites[j]
                dist = matcher.compute_similarity(features[site_a], features[site_b])
                print(f"\n{site_a} <-> {site_b}")
                print(f"  Distance: {dist:.4f}")
                print(f"  Similarity: {(1-dist)*100:.1f}%")
    
    return True

def main():
    print("=" * 50)
    print("LOGO MATCHER - COMPONENT TESTS")
    print("=" * 50)
    
    try:
        logo_urls = test_logo_extraction()
        if not logo_urls:
            print("\nExtraction failed - cannot proceed")
            return False
        
        processed = test_image_processing(logo_urls)
        if not processed:
            print("\nProcessing failed - cannot proceed")
            return False
        
        features = test_feature_extraction(processed)
        if not features:
            print("\nFeature extraction failed - cannot proceed")
            return False
        
        test_similarity_computation(features)
        
        print("\n" + "=" * 50)
        print("ALL TESTS PASSED")
        print("=" * 50)
        print("\nYou can now run: python main.py --input logos.snappy.parquet")
        
        return True
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
