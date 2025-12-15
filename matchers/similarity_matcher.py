"""
similarity matcher. hand-rolled because using real ML felt like cheating.
"""

import numpy as np
from scipy.spatial.distance import cosine, euclidean
import imagehash
import logging
from typing import List, Dict, Tuple, Set
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimilarityMatcher:
    """
    Match and group logos using simple math. nothing too smart happening here.
    """
    
    def __init__(self, 
                 color_weight: float = 0.3,
                 hog_weight: float = 0.3,
                 hash_weight: float = 0.4,
                 similarity_threshold: float = 0.15):
        # i just guessed these weights until things looked ok
        self.color_weight = color_weight
        self.hog_weight = hog_weight
        self.hash_weight = hash_weight
        self.similarity_threshold = similarity_threshold
    
    def compute_similarity(self, features_a: Dict, features_b: Dict) -> float:
        """Compute combined similarity score between two feature sets"""
        try:
            distances = []
            weights = []
            
            if 'color_hist' in features_a and 'color_hist' in features_b:
                color_dist = self._cosine_distance(features_a['color_hist'], features_b['color_hist'])
                distances.append(color_dist)
                weights.append(self.color_weight)
            
            if 'hog' in features_a and 'hog' in features_b:
                hog_dist = self._cosine_distance(features_a['hog'], features_b['hog'])
                distances.append(hog_dist)
                weights.append(self.hog_weight)
            
            if 'phash' in features_a and 'phash' in features_b:
                hash_dist = self._hash_distance(features_a['phash'], features_b['phash'])
                distances.append(hash_dist)
                weights.append(self.hash_weight)
            
            if distances:
                total_weight = sum(weights)
                combined_distance = sum(d * w for d, w in zip(distances, weights)) / total_weight
                return combined_distance
            else:
                # no features? then they are basically unrelated
                return 1.0
        except Exception as e:
            logger.debug(f"Similarity computation failed: {e}")
            return 1.0
    
    def _cosine_distance(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """Compute cosine distance"""
        try:
            if np.linalg.norm(vec_a) == 0 or np.linalg.norm(vec_b) == 0:
                return 1.0
            return cosine(vec_a, vec_b)
        except:
            return 1.0
    
    def _hash_distance(self, hash_a: str, hash_b: str) -> float:
        """Compute normalized Hamming distance between hashes"""
        try:
            h1 = imagehash.hex_to_hash(hash_a)
            h2 = imagehash.hex_to_hash(hash_b)
            
            hamming_dist = h1 - h2
            max_dist = len(hash_a) * 4
            normalized = hamming_dist / max_dist
            
            return normalized
        except Exception as e:
            logger.debug(f"Hash distance computation failed: {e}")
            return 1.0
    
    def create_similarity_matrix(self, all_features: List[Dict]) -> np.ndarray:
        """Create pairwise similarity matrix for all logos"""
        n = len(all_features)
        matrix = np.zeros((n, n))
        
        logger.info(f"Computing similarity matrix for {n} logos...")
        
        for i in range(n):
            for j in range(i + 1, n):
                distance = self.compute_similarity(all_features[i], all_features[j])
                matrix[i, j] = distance
                matrix[j, i] = distance
        
        return matrix
    
    def threshold_based_clustering(self, 
                                   similarity_matrix: np.ndarray,
                                   website_urls: List[str]) -> List[List[str]]:
        """Custom threshold-based clustering algorithm (NO ML libraries)"""
        n = len(website_urls)
        
        groups = {i: {i} for i in range(n)}
        
        pairs = []
        for i in range(n):
            for j in range(i + 1, n):
                pairs.append((similarity_matrix[i, j], i, j))
        
        pairs.sort(key=lambda x: x[0])
        
        logger.info(f"Starting threshold-based clustering with threshold={self.similarity_threshold}")
        
        merges = 0
        for distance, i, j in pairs:
            if distance > self.similarity_threshold:
                break
            
            group_i = self._find_group(i, groups)
            group_j = self._find_group(j, groups)
            
            if group_i != group_j:
                groups[group_i] = groups[group_i].union(groups[group_j])
                del groups[group_j]
                merges += 1
        
        logger.info(f"Completed clustering: {merges} merges, {len(groups)} final groups")
        
        result = []
        for group_indices in groups.values():
            group_urls = [website_urls[i] for i in group_indices]
            result.append(group_urls)
        
        result.sort(key=len, reverse=True)
        
        return result
    
    def _find_group(self, index: int, groups: Dict[int, Set[int]]) -> int:
        """Find which group an index belongs to"""
        for group_id, members in groups.items():
            if index in members:
                return group_id
        return index
    
    def compute_group_statistics(self, 
                                 groups: List[List[str]], 
                                 all_features: Dict[str, Dict]) -> List[Dict]:
        """Compute statistics for each group"""
        group_stats = []
        
        for i, group in enumerate(groups):
            stats = {
                'group_id': f'group_{i + 1}',
                'size': len(group),
                'websites': group,
                'common_features': {}
            }
            
            if len(group) > 0 and group[0] in all_features:
                try:
                    dominant_colors = []
                    for url in group:
                        if url in all_features and 'dominant_colors' in all_features[url]:
                            colors = all_features[url]['dominant_colors']['colors']
                            if colors:
                                dominant_colors.append(colors[0])
                    
                    if dominant_colors:
                        avg_color = np.mean(dominant_colors, axis=0).astype(int)
                        stats['common_features']['average_dominant_color'] = avg_color.tolist()
                except Exception as e:
                    logger.debug(f"Could not compute group statistics: {e}")
            
            group_stats.append(stats)
        
        return group_stats
