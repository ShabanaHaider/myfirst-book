"""
Async utility functions for batch processing.
"""
import asyncio
import time
import logging
from typing import Callable, Any, List, TypeVar, Awaitable, Optional
from functools import wraps
import aiohttp
from src.utils.logging import StructuredLogger

T = TypeVar('T')


async def async_retry_with_backoff(
    func: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
) -> T:
    """
    Execute an async function with exponential backoff retry logic.

    Args:
        func: The async function to execute
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Multiplier for delay between retries
        exceptions: Tuple of exceptions to catch and retry on

    Returns:
        Result of the function call

    Raises:
        The original exception if all retries are exhausted
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func()
        except exceptions as e:
            last_exception = e
            if attempt == max_retries:
                # All retries exhausted
                break

            # Calculate delay with exponential backoff
            delay = min(base_delay * (backoff_factor ** attempt), max_delay)
            logging.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s...")

            # Wait before retrying
            await asyncio.sleep(delay)

    # If we get here, all retries were exhausted
    raise last_exception


def async_circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exception_types: tuple = (Exception,)
):
    """
    Decorator that implements the circuit breaker pattern for async functions.

    Args:
        failure_threshold: Number of failures before opening the circuit
        recovery_timeout: Time in seconds to wait before attempting recovery
        expected_exception_types: Tuple of exception types to count as failures
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        # Circuit breaker state
        state = {
            'closed': True,  # True = closed, False = open
            'failure_count': 0,
            'last_failure_time': None
        }

        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            current_time = time.time()

            # Check if circuit should be closed again after timeout
            if not state['closed'] and state['last_failure_time']:
                if current_time - state['last_failure_time'] >= recovery_timeout:
                    logging.info(f"Circuit breaker for {func.__name__} attempting reset after timeout")
                    state['closed'] = True
                    state['failure_count'] = 0

            # If circuit is open, raise exception without calling function
            if not state['closed']:
                raise Exception(f"Circuit breaker for {func.__name__} is OPEN. Call failed immediately.")

            try:
                # Call the function
                result = await func(*args, **kwargs)

                # If successful and circuit was half-open, reset it
                if not state['closed']:
                    logging.info(f"Circuit breaker for {func.__name__} closed after successful call")
                    state['closed'] = True
                    state['failure_count'] = 0

                return result

            except expected_exception_types as e:
                # Increment failure count
                state['failure_count'] += 1
                state['last_failure_time'] = current_time

                logging.warning(
                    f"Circuit breaker: {func.__name__} failed (attempt {state['failure_count']}). "
                    f"Error: {e}"
                )

                # Open the circuit if threshold is reached
                if state['failure_count'] >= failure_threshold:
                    logging.error(f"Circuit breaker for {func.__name__} OPENED after {failure_threshold} failures")
                    state['closed'] = False

                raise

        return wrapper
    return decorator


async def run_with_timeout(
    coro: Awaitable[T],
    timeout: float,
    default: T = None
) -> T:
    """
    Run a coroutine with a timeout.

    Args:
        coro: The coroutine to run
        timeout: Timeout in seconds
        default: Default value to return if timeout occurs

    Returns:
        Result of the coroutine or default value if timeout occurs
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        if default is not None:
            return default
        else:
            raise


async def batch_process(
    items: List[Any],
    processor: Callable[[Any], Awaitable[T]],
    batch_size: int = 10,
    delay_between_batches: float = 0.1
) -> List[T]:
    """
    Process a list of items in batches asynchronously.

    Args:
        items: List of items to process
        processor: Async function to process each item
        batch_size: Number of items to process in each batch
        delay_between_batches: Delay between batches in seconds

    Returns:
        List of processed results
    """
    results = []

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_tasks = [processor(item) for item in batch]

        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

        # Handle any exceptions that occurred during batch processing
        for result in batch_results:
            if isinstance(result, Exception):
                logging.error(f"Error processing item in batch: {result}")
                results.append(None)  # or handle differently based on requirements
            else:
                results.append(result)

        # Add delay between batches to be respectful to APIs or systems
        if i + batch_size < len(items) and delay_between_batches > 0:
            await asyncio.sleep(delay_between_batches)

    return results


async def limited_concurrent_execute(
    coroutines: List[Awaitable[T]],
    max_concurrent: int = 10
) -> List[T]:
    """
    Execute multiple coroutines with limited concurrency.

    Args:
        coroutines: List of coroutines to execute
        max_concurrent: Maximum number of concurrent executions

    Returns:
        List of results in the same order as input coroutines
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def limited_run(coro: Awaitable[T]) -> T:
        async with semaphore:
            return await coro

    tasks = [limited_run(coro) for coro in coroutines]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Check for any exceptions in the results
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logging.error(f"Exception in coroutine {i}: {result}")
            raise result

    return results


class AsyncRateLimiter:
    """
    An async rate limiter that restricts the number of operations per time period.
    """
    def __init__(self, max_calls: int, time_period: float):
        """
        Initialize the rate limiter.

        Args:
            max_calls: Maximum number of calls allowed per time period
            time_period: Time period in seconds
        """
        self.max_calls = max_calls
        self.time_period = time_period
        self.calls = []
        self._lock = asyncio.Lock()

    async def acquire(self):
        """
        Acquire permission to make a call, waiting if necessary.
        """
        async with self._lock:
            current_time = time.time()

            # Remove calls that are outside the current time window
            self.calls = [call_time for call_time in self.calls if current_time - call_time < self.time_period]

            if len(self.calls) >= self.max_calls:
                # Need to wait until enough time has passed
                sleep_time = self.time_period - (current_time - self.calls[0])
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    # After sleeping, recheck the calls list
                    current_time = time.time()
                    self.calls = [call_time for call_time in self.calls if current_time - call_time < self.time_period]

            self.calls.append(current_time)


async def with_rate_limit(rate_limiter: AsyncRateLimiter, func: Callable[[], Awaitable[T]]) -> T:
    """
    Execute a function with rate limiting.

    Args:
        rate_limiter: The rate limiter to use
        func: The async function to execute

    Returns:
        Result of the function call
    """
    await rate_limiter.acquire()
    return await func()


async def gather_with_limited_concurrency(
    tasks: List[Awaitable[T]],
    max_concurrent: int = 5
) -> List[T]:
    """
    Run multiple tasks with limited concurrency, similar to asyncio.gather but with concurrency limits.

    Args:
        tasks: List of tasks/coroutines to run
        max_concurrent: Maximum number of concurrent tasks

    Returns:
        List of results in the same order as input tasks
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    results = [None] * len(tasks)

    async def run_task(i: int, task: Awaitable[T]) -> None:
        async with semaphore:
            results[i] = await task

    await asyncio.gather(*(run_task(i, task) for i, task in enumerate(tasks)))

    return results


async def retry_on_exception(
    func: Callable[[], Awaitable[T]],
    exceptions: tuple,
    max_retries: int = 3,
    delay: float = 1.0
) -> T:
    """
    Retry a function if specific exceptions are raised.

    Args:
        func: The function to call
        exceptions: Tuple of exceptions that trigger a retry
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds

    Returns:
        Result of the successful function call
    """
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except exceptions as e:
            if attempt == max_retries:
                raise  # Re-raise the last exception if max retries reached

            logging.info(f"Attempt {attempt + 1} failed with {type(e).__name__}: {e}. Retrying in {delay}s...")
            await asyncio.sleep(delay)

    # This line should never be reached due to the return in the try block
    # or the raise in the except block, but included for type checking
    raise Exception("Unexpected flow in retry_on_exception")