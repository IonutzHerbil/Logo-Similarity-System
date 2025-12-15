import pandas as pd
import logging
from typing import List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataReader:
    @staticmethod
    def read_parquet(filepath: str, url_column: str = 'domain') -> List[str]:
        try:
            logger.info(f"Reading Parquet file: {filepath}")
            df = pd.read_parquet(filepath)
            
            logger.info(f"Loaded {len(df)} rows")
            logger.info(f"Columns: {df.columns.tolist()}")
            
            possible_columns = [url_column, 'url', 'website', 'domain', 'company_domain', 'site']
            url_col = None
            
            for col in possible_columns:
                if col in df.columns:
                    url_col = col
                    break
            
            if url_col is None:
                logger.warning(f"Could not find URL column. Available columns: {df.columns.tolist()}")
                logger.info(f"Using first column: {df.columns[0]}")
                url_col = df.columns[0]
            
            websites = df[url_col].dropna().astype(str).tolist()
            websites = list(dict.fromkeys(websites))
            
            logger.info(f"Extracted {len(websites)} unique websites")
            
            return websites
            
        except Exception as e:
            logger.error(f"Failed to read Parquet file: {e}")
            return []
    
    @staticmethod
    def read_text_file(filepath: str) -> List[str]:
        try:
            with open(filepath, 'r') as f:
                websites = [line.strip() for line in f if line.strip()]
            
            logger.info(f"Loaded {len(websites)} websites from text file")
            return websites
            
        except Exception as e:
            logger.error(f"Failed to read text file: {e}")
            return []
    
    @staticmethod
    def read_csv(filepath: str, url_column: str = 'domain') -> List[str]:
        try:
            df = pd.read_csv(filepath)
            
            if url_column not in df.columns:
                logger.warning(f"Column '{url_column}' not found. Using first column.")
                url_column = df.columns[0]
            
            websites = df[url_column].dropna().astype(str).tolist()
            websites = list(dict.fromkeys(websites))
            
            logger.info(f"Loaded {len(websites)} websites from CSV")
            return websites
            
        except Exception as e:
            logger.error(f"Failed to read CSV file: {e}")
            return []
