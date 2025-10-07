from typing import List, Dict, Any
import logging
from src.rag_app.core.interfaces.reranker_interface import ReRankerInterface

logger = logging.getLogger(__name__)

class ResultReRanker(ReRankerInterface):
    def re_rank(self, results: List[Dict[str, Any]], original_query: str) -> List[Dict[str, Any]]:
        logger.info(f"Re-ranking {len(results)} results for query: {original_query}")
        
        '''
        # Sort results by score in descending order
        re_ranked_results = sorted(results, key=lambda x: x['distance'], reverse=False)
        '''
        # Filter results with distance < 1.0 and sort by distance
        re_ranked_results = sorted(
            [r for r in results if r['distance'] < 1.1], # 1.1, 0.97
            key=lambda x: x['distance'],
            reverse=False
        )

        # Log distances for each result
        for i, result in enumerate(re_ranked_results):
            logger.info(f"Result {i+1} distance: {result['distance']:.4f}")
        

        
        return re_ranked_results[:3]
