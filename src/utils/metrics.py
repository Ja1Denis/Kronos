class SystemMetrics:
    def __init__(self):
        self.fts_failures = 0
        self.vector_failures = 0
        self.total_queries = 0
    
    def log_failure(self, failure_type: str):
        if failure_type == "fts":
            self.fts_failures += 1
        elif failure_type == "vector":
            self.vector_failures += 1
    
    def log_query(self):
        self.total_queries += 1
    
    def health_score(self):
        """Postotak uspješnih querya"""
        if self.total_queries == 0:
            return 100.0
        failures = self.fts_failures + self.vector_failures
        return 100 * (1 - failures / self.total_queries)

# Singleton instance
metrics = SystemMetrics()
