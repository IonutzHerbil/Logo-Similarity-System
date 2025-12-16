import numpy as np
import imagehash
import logging
from typing import List, Dict
from collections import defaultdict
from sklearn.cluster import DBSCAN
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimilarityMatcher:
    def __init__(self, eps=0.12, min_samples=2):
        self.eps = eps
        self.min_samples = min_samples
    
    def compute_similarity(self, feat_a, feat_b):
        try:
            hash_types = ['phash', 'dhash', 'ahash', 'whash']
            dists = []
            
            for ht in hash_types:
                if ht in feat_a and ht in feat_b:
                    h1 = imagehash.hex_to_hash(feat_a[ht])
                    h2 = imagehash.hex_to_hash(feat_b[ht])
                    hamming = h1 - h2
                    max_dist = len(feat_a[ht]) * 4
                    normalized = hamming / max_dist
                    dists.append(normalized)
            
            return min(dists) if dists else 1.0
        except:
            return 1.0
    
    def create_similarity_matrix(self, features_list):
        n = len(features_list)
        matrix = np.zeros((n, n))
        
        total = (n * (n - 1)) // 2
        with tqdm(total=total, desc="Computing similarities") as pbar:
            for i in range(n):
                for j in range(i + 1, n):
                    d = self.compute_similarity(features_list[i], features_list[j])
                    matrix[i, j] = d
                    matrix[j, i] = d
                    pbar.update(1)
        
        return matrix
    
    def cluster_logos(self, sim_matrix, urls):
        clustering = DBSCAN(eps=self.eps, min_samples=self.min_samples, metric='precomputed')
        labels = clustering.fit_predict(sim_matrix)
        
        groups_dict = defaultdict(list)
        for i, label in enumerate(labels):
            groups_dict[label].append(urls[i])
        
        groups = list(groups_dict.values())
        groups.sort(key=len, reverse=True)
        
        logger.info(f"DBSCAN formed {len(groups)} groups (eps={self.eps}, min_samples={self.min_samples})")
        return groups
    
    def compute_group_statistics(self, groups, all_features):
        stats = []
        for i, group in enumerate(groups):
            s = {
                'group_id': f'group_{i + 1}',
                'size': len(group),
                'websites': group
            }
            stats.append(s)
        return stats