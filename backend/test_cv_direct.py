#!/usr/bin/env python3
"""Direct test of CV parsing to debug where the hang occurs."""

import sys
import time

from llm import get_provider

print("Starting test...", file=sys.stderr, flush=True)

# Test 1: Check if adapter initializes
print("Test 1: Initialize adapter", file=sys.stderr, flush=True)

try:
    provider = get_provider()
    print(f"✓ Provider initialized: {type(provider).__name__}", file=sys.stderr, flush=True)
except Exception as e:
    print(f"✗ Provider init failed: {e}", file=sys.stderr, flush=True)
    sys.exit(1)

# Test 2: Check if parse_cv is callable
print("Test 2: Call parse_cv with short text", file=sys.stderr, flush=True)
cv_text = "John Doe\nSoftware Engineer\n10 years"
try:
    start = time.time()
    result = provider.parse_cv(cv_text)
    elapsed = time.time() - start
    print(f"✓ parse_cv succeeded in {elapsed:.2f}s", file=sys.stderr, flush=True)
    print(f"Result keys: {list(result.keys())}", file=sys.stderr, flush=True)
except Exception as e:
    elapsed = time.time() - start
    print(f"✗ parse_cv failed after {elapsed:.2f}s: {e}", file=sys.stderr, flush=True)
    import traceback

    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

print("All tests passed!", file=sys.stderr, flush=True)
