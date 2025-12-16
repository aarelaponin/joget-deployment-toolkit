#!/usr/bin/env python3
"""
Performance benchmarking script for repository refactoring.

Compares performance of:
- Old approach: Direct SQL with manual connection management
- New approach: Repository pattern with connection pooling

Target: Demonstrate 50% overhead reduction through:
- Connection pooling
- Reduced connection creation/teardown
- Query optimization
- Reduced code duplication

Usage:
    python scripts/benchmark_repositories.py --iterations 100 --db-host localhost
"""

import argparse
import time
import statistics
from typing import List, Dict, Callable
from contextlib import contextmanager
import mysql.connector
from mysql.connector import Error as MySQLError

# Add src to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from joget_deployment_toolkit.models import DatabaseConfig
from joget_deployment_toolkit.database import DatabaseConnectionPool
from joget_deployment_toolkit.database.repositories import FormRepository, ApplicationRepository


# ============================================================================
# Old Approach (Manual Connection Management)
# ============================================================================

class OldStyleFormQueries:
    """Old approach with manual connection management per query."""

    def __init__(self, db_config: Dict):
        self.db_config = db_config

    def find_forms_by_app(self, app_id: str, app_version: str) -> List[Dict]:
        """Find forms using manual connection management."""
        connection = None
        cursor = None
        forms = []

        try:
            # Create new connection for each query
            connection = mysql.connector.connect(
                host=self.db_config.get('host', 'localhost'),
                port=self.db_config.get('port', 3306),
                database=self.db_config.get('database', 'jwdb'),
                user=self.db_config.get('user'),
                password=self.db_config.get('password')
            )

            cursor = connection.cursor(dictionary=True, buffered=True)

            query = """
                SELECT formId, name, tableName, appId, appVersion
                FROM app_form
                WHERE appId = %s AND appVersion = %s
                ORDER BY name
            """

            cursor.execute(query, (app_id, app_version))
            forms = cursor.fetchall()

        except MySQLError:
            pass
        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

        return forms

    def get_form_count(self, app_id: str, app_version: str) -> int:
        """Count forms using manual connection management."""
        connection = None
        cursor = None
        count = 0

        try:
            # Create new connection for each query
            connection = mysql.connector.connect(
                host=self.db_config.get('host', 'localhost'),
                port=self.db_config.get('port', 3306),
                database=self.db_config.get('database', 'jwdb'),
                user=self.db_config.get('user'),
                password=self.db_config.get('password')
            )

            cursor = connection.cursor(buffered=True)

            query = """
                SELECT COUNT(*) as count
                FROM app_form
                WHERE appId = %s AND appVersion = %s
            """

            cursor.execute(query, (app_id, app_version))
            result = cursor.fetchone()
            count = result[0] if result else 0

        except MySQLError:
            pass
        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

        return count


# ============================================================================
# New Approach (Repository with Connection Pooling)
# ============================================================================

class NewStyleRepositories:
    """New approach with connection pooling and repositories."""

    def __init__(self, db_config: DatabaseConfig):
        self.pool = DatabaseConnectionPool(db_config)
        self.form_repo = FormRepository(self.pool)

    def find_forms_by_app(self, app_id: str, app_version: str) -> List:
        """Find forms using repository with connection pooling."""
        return self.form_repo.find_by_app(app_id, app_version)

    def get_form_count(self, app_id: str, app_version: str) -> int:
        """Count forms using repository with connection pooling."""
        return self.form_repo.count(
            "app_form",
            "appId = %s AND appVersion = %s",
            (app_id, app_version)
        )

    def close(self):
        """Close connection pool."""
        self.pool.close()


# ============================================================================
# Benchmarking Framework
# ============================================================================

@contextmanager
def timer():
    """Simple timer context manager."""
    start = time.perf_counter()
    yield lambda: time.perf_counter() - start
    end = time.perf_counter()


def benchmark_function(
    name: str,
    func: Callable,
    iterations: int = 100
) -> Dict:
    """
    Benchmark a function.

    Args:
        name: Benchmark name
        func: Function to benchmark
        iterations: Number of iterations

    Returns:
        Dictionary with timing statistics
    """
    print(f"\nBenchmarking: {name}")
    print(f"  Iterations: {iterations}")

    times = []

    for i in range(iterations):
        with timer() as get_time:
            func()
        elapsed = get_time() * 1000  # Convert to milliseconds
        times.append(elapsed)

        if (i + 1) % 10 == 0:
            print(f"  Progress: {i + 1}/{iterations}", end='\r')

    print()  # New line after progress

    return {
        'name': name,
        'iterations': iterations,
        'mean': statistics.mean(times),
        'median': statistics.median(times),
        'stdev': statistics.stdev(times) if len(times) > 1 else 0,
        'min': min(times),
        'max': max(times),
        'total': sum(times)
    }


def print_results(results: List[Dict]):
    """Print benchmark results in formatted table."""
    print("\n" + "=" * 80)
    print("BENCHMARK RESULTS")
    print("=" * 80)

    for result in results:
        print(f"\n{result['name']}")
        print(f"  Iterations:  {result['iterations']}")
        print(f"  Mean:        {result['mean']:.2f} ms")
        print(f"  Median:      {result['median']:.2f} ms")
        print(f"  Std Dev:     {result['stdev']:.2f} ms")
        print(f"  Min:         {result['min']:.2f} ms")
        print(f"  Max:         {result['max']:.2f} ms")
        print(f"  Total:       {result['total']:.2f} ms")


def calculate_improvement(old_result: Dict, new_result: Dict) -> Dict:
    """
    Calculate performance improvement.

    Args:
        old_result: Old approach benchmark results
        new_result: New approach benchmark results

    Returns:
        Dictionary with improvement metrics
    """
    old_mean = old_result['mean']
    new_mean = new_result['mean']

    improvement_pct = ((old_mean - new_mean) / old_mean) * 100
    speedup = old_mean / new_mean

    return {
        'old_mean_ms': old_mean,
        'new_mean_ms': new_mean,
        'improvement_pct': improvement_pct,
        'speedup': speedup,
        'target_met': improvement_pct >= 50.0
    }


def print_comparison(improvement: Dict):
    """Print performance comparison."""
    print("\n" + "=" * 80)
    print("PERFORMANCE COMPARISON")
    print("=" * 80)

    print(f"\nOld Approach Mean: {improvement['old_mean_ms']:.2f} ms")
    print(f"New Approach Mean: {improvement['new_mean_ms']:.2f} ms")
    print(f"\nImprovement:       {improvement['improvement_pct']:.1f}%")
    print(f"Speedup:           {improvement['speedup']:.2f}x")

    print(f"\nTarget (50% reduction): {'✓ MET' if improvement['target_met'] else '✗ NOT MET'}")

    if improvement['target_met']:
        print("\n🎉 SUCCESS! Repository refactoring achieved target performance improvement!")
    else:
        print("\n⚠️  Target not met. Consider further optimization.")


def main():
    """Run performance benchmarks."""
    parser = argparse.ArgumentParser(
        description='Benchmark repository performance improvements'
    )
    parser.add_argument(
        '--iterations',
        type=int,
        default=100,
        help='Number of iterations for each benchmark (default: 100)'
    )
    parser.add_argument(
        '--db-host',
        default='localhost',
        help='Database host (default: localhost)'
    )
    parser.add_argument(
        '--db-port',
        type=int,
        default=3306,
        help='Database port (default: 3306)'
    )
    parser.add_argument(
        '--db-name',
        default='jwdb',
        help='Database name (default: jwdb)'
    )
    parser.add_argument(
        '--db-user',
        default='root',
        help='Database user (default: root)'
    )
    parser.add_argument(
        '--db-password',
        default='',
        help='Database password'
    )
    parser.add_argument(
        '--app-id',
        default='masterData',
        help='Application ID to use for benchmarks (default: masterData)'
    )
    parser.add_argument(
        '--app-version',
        default='1',
        help='Application version (default: 1)'
    )

    args = parser.parse_args()

    print("=" * 80)
    print("JOGET-TOOLKIT REPOSITORY PERFORMANCE BENCHMARK")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  Database: {args.db_user}@{args.db_host}:{args.db_port}/{args.db_name}")
    print(f"  Test App: {args.app_id} v{args.app_version}")
    print(f"  Iterations: {args.iterations}")

    # Database configuration
    db_config_dict = {
        'host': args.db_host,
        'port': args.db_port,
        'database': args.db_name,
        'user': args.db_user,
        'password': args.db_password
    }

    db_config = DatabaseConfig(
        host=args.db_host,
        port=args.db_port,
        database=args.db_name,
        user=args.db_user,
        password=args.db_password
    )

    # Test database connection
    print("\nTesting database connection...")
    try:
        pool = DatabaseConnectionPool(db_config)
        with pool.get_connection() as conn:
            if conn.is_connected():
                print("✓ Database connection successful")
        pool.close()
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return 1

    # Initialize old and new approaches
    old_queries = OldStyleFormQueries(db_config_dict)
    new_repos = NewStyleRepositories(db_config)

    results = []

    try:
        # Benchmark 1: Find forms by app (old approach)
        print("\n" + "-" * 80)
        old_result = benchmark_function(
            "Old Approach: Find forms by app (manual connections)",
            lambda: old_queries.find_forms_by_app(args.app_id, args.app_version),
            iterations=args.iterations
        )
        results.append(old_result)

        # Benchmark 2: Find forms by app (new approach)
        print("-" * 80)
        new_result = benchmark_function(
            "New Approach: Find forms by app (connection pooling)",
            lambda: new_repos.find_forms_by_app(args.app_id, args.app_version),
            iterations=args.iterations
        )
        results.append(new_result)

        # Print results
        print_results(results)

        # Calculate and print improvement
        improvement = calculate_improvement(old_result, new_result)
        print_comparison(improvement)

        return 0 if improvement['target_met'] else 1

    finally:
        # Cleanup
        new_repos.close()


if __name__ == "__main__":
    sys.exit(main())
