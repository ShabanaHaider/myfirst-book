"""
Monitoring and metrics collection for the RAG Chatbot system.
"""
import time
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading
import json


@dataclass
class Metric:
    """Represents a single metric with timestamp and value."""
    name: str
    value: float
    timestamp: float
    tags: Dict[str, str]


class MetricsCollector:
    """
    Collects and stores system metrics for monitoring.
    """

    def __init__(self, max_metrics: int = 1000):
        """Initialize the metrics collector."""
        self.max_metrics = max_metrics
        self.metrics: List[Metric] = []
        self.lock = threading.Lock()
        self.counters = defaultdict(int)
        self.gauges = defaultdict(float)
        self.histograms = defaultdict(list)

    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a metric value."""
        with self.lock:
            metric = Metric(
                name=name,
                value=value,
                timestamp=time.time(),
                tags=tags or {}
            )
            self.metrics.append(metric)

            # Keep only the most recent metrics
            if len(self.metrics) > self.max_metrics:
                self.metrics = self.metrics[-self.max_metrics:]

    def increment_counter(self, name: str, tags: Optional[Dict[str, str]] = None, amount: int = 1):
        """Increment a counter metric."""
        with self.lock:
            key = f"{name}_{json.dumps(sorted(tags.items()) if tags else {})}"
            self.counters[key] += amount

    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set a gauge metric."""
        with self.lock:
            key = f"{name}_{json.dumps(sorted(tags.items()) if tags else {})}"
            self.gauges[key] = value

    def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a histogram value."""
        with self.lock:
            key = f"{name}_{json.dumps(sorted(tags.items()) if tags else {})}"
            self.histograms[key].append(value)

            # Keep only the most recent values
            if len(self.histograms[key]) > 1000:
                self.histograms[key] = self.histograms[key][-1000:]

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of collected metrics."""
        with self.lock:
            # Calculate summary statistics
            summary = {
                "total_metrics_recorded": len(self.metrics),
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "histogram_stats": {}
            }

            # Calculate histogram statistics
            for key, values in self.histograms.items():
                if values:
                    summary["histogram_stats"][key] = {
                        "count": len(values),
                        "avg": sum(values) / len(values),
                        "min": min(values),
                        "max": max(values),
                        "p50": sorted(values)[len(values) // 2] if values else 0,
                        "p95": sorted(values)[int(0.95 * len(values))] if values else 0,
                        "p99": sorted(values)[int(0.99 * len(values))] if values else 0
                    }

            return summary

    def get_metrics_by_name(self, name: str) -> List[Metric]:
        """Get all metrics with a specific name."""
        with self.lock:
            return [m for m in self.metrics if m.name == name]

    def get_metrics_in_time_range(self, start_time: float, end_time: float) -> List[Metric]:
        """Get metrics within a specific time range."""
        with self.lock:
            return [m for m in self.metrics if start_time <= m.timestamp <= end_time]

    def clear_metrics(self):
        """Clear all collected metrics."""
        with self.lock:
            self.metrics.clear()
            self.counters.clear()
            self.gauges.clear()
            self.histograms.clear()


class SystemMonitor:
    """
    Monitors various system components and collects metrics.
    """

    def __init__(self):
        """Initialize the system monitor."""
        self.metrics_collector = MetricsCollector()
        self.start_time = time.time()
        self.request_stats = defaultdict(deque)
        self.max_request_history = 1000  # Keep last 1000 requests per endpoint

    def record_request(self, endpoint: str, duration: float, status_code: int = 200):
        """Record an API request metric."""
        # Record response time
        self.metrics_collector.record_histogram(
            "api_response_time",
            duration,
            tags={"endpoint": endpoint, "status_code": str(status_code)}
        )

        # Record request count
        self.metrics_collector.increment_counter(
            "api_requests_total",
            tags={"endpoint": endpoint, "status_code": str(status_code)}
        )

        # Store for per-endpoint stats
        request_info = {
            "timestamp": time.time(),
            "duration": duration,
            "status_code": status_code
        }
        self.request_stats[endpoint].append(request_info)

        # Keep only recent requests
        if len(self.request_stats[endpoint]) > self.max_request_history:
            self.request_stats[endpoint].popleft()

    def record_embedding_operation(self, operation_type: str, duration: float, num_embeddings: int = 1):
        """Record an embedding operation metric."""
        self.metrics_collector.record_histogram(
            "embedding_operation_duration",
            duration,
            tags={"operation_type": operation_type}
        )

        self.metrics_collector.increment_counter(
            "embedding_operations_total",
            tags={"operation_type": operation_type}
        )

        if operation_type == "generate":
            self.metrics_collector.increment_counter(
                "embeddings_generated_total",
                amount=num_embeddings
            )

    def record_qdrant_operation(self, operation_type: str, duration: float, num_points: int = 1):
        """Record a Qdrant operation metric."""
        self.metrics_collector.record_histogram(
            "qdrant_operation_duration",
            duration,
            tags={"operation_type": operation_type}
        )

        self.metrics_collector.increment_counter(
            "qdrant_operations_total",
            tags={"operation_type": operation_type}
        )

        if operation_type in ["upsert", "store"]:
            self.metrics_collector.increment_counter(
                "qdrant_points_stored_total",
                amount=num_points
            )

    def get_system_uptime(self) -> float:
        """Get the system uptime in seconds."""
        return time.time() - self.start_time

    def get_api_stats(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """Get API statistics."""
        stats = {}

        if endpoint:
            requests = list(self.request_stats[endpoint])
        else:
            requests = []
            for endpoint_requests in self.request_stats.values():
                requests.extend(endpoint_requests)

        if requests:
            durations = [r["duration"] for r in requests]
            status_codes = [r["status_code"] for r in requests]

            stats = {
                "total_requests": len(requests),
                "avg_response_time": sum(durations) / len(durations),
                "min_response_time": min(durations),
                "max_response_time": max(durations),
                "p95_response_time": sorted(durations)[int(0.95 * len(durations))] if durations else 0,
                "status_codes": {str(code): status_codes.count(code) for code in set(status_codes)},
                "requests_per_minute": len(requests) / (self.get_system_uptime() / 60) if self.get_system_uptime() > 0 else 0
            }

        return stats

    def get_overall_stats(self) -> Dict[str, Any]:
        """Get overall system statistics."""
        return {
            "uptime_seconds": self.get_system_uptime(),
            "metrics_collector": self.metrics_collector.get_metrics_summary(),
            "api_stats": self.get_api_stats(),
            "active_endpoints": list(self.request_stats.keys())
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get key performance metrics."""
        metrics_summary = self.metrics_collector.get_metrics_summary()

        performance_metrics = {
            "requests_per_second": 0,
            "avg_response_time": 0,
            "error_rate": 0,
            "embedding_generation_rate": 0
        }

        # Calculate requests per second
        api_stats = self.get_api_stats()
        if api_stats:
            uptime = self.get_system_uptime()
            if uptime > 0:
                performance_metrics["requests_per_second"] = api_stats.get("requests_per_minute", 0) / 60
                performance_metrics["avg_response_time"] = api_stats.get("avg_response_time", 0)

        # Calculate error rate from counters
        counters = metrics_summary.get("counters", {})
        total_requests = sum(v for k, v in counters.items() if "api_requests_total" in k)
        error_requests = sum(v for k, v in counters.items()
                           if "api_requests_total" in k and "_status_code_4" in k or "_status_code_5" in k)

        if total_requests > 0:
            performance_metrics["error_rate"] = error_requests / total_requests

        # Calculate embedding generation rate
        embedding_count = counters.get("embeddings_generated_total_{}", 0)
        uptime = self.get_system_uptime()
        if uptime > 0:
            performance_metrics["embedding_generation_rate"] = embedding_count / uptime

        return performance_metrics


# Global monitor instance
monitor = SystemMonitor()


def record_api_request(endpoint: str, duration: float, status_code: int = 200):
    """Record an API request to the global monitor."""
    monitor.record_request(endpoint, duration, status_code)


def record_embedding_operation(operation_type: str, duration: float, num_embeddings: int = 1):
    """Record an embedding operation to the global monitor."""
    monitor.record_embedding_operation(operation_type, duration, num_embeddings)


def record_qdrant_operation(operation_type: str, duration: float, num_points: int = 1):
    """Record a Qdrant operation to the global monitor."""
    monitor.record_qdrant_operation(operation_type, duration, num_points)


def get_monitor_stats() -> Dict[str, Any]:
    """Get statistics from the global monitor."""
    return monitor.get_overall_stats()


def get_performance_metrics() -> Dict[str, Any]:
    """Get performance metrics from the global monitor."""
    return monitor.get_performance_metrics()