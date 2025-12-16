import imagehash
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FeatureExtractor:
    def __init__(self, hash_size=16):
        self.hash_size = hash_size
    
    def extract_features(self, image, pil_image):
        try:
            features = {
                'phash': str(imagehash.phash(pil_image, hash_size=self.hash_size)),
                'dhash': str(imagehash.dhash(pil_image, hash_size=self.hash_size)),
                'ahash': str(imagehash.average_hash(pil_image, hash_size=self.hash_size)),
                'whash': str(imagehash.whash(pil_image, hash_size=self.hash_size)),
            }
            return features
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            return None