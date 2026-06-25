#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Load testing tool for OpenBalancer.

This script performs concurrent requests to stress test the API and collect
statistics about provider load distribution and failure rates.
"""

from collections import Counter
import argparse
from itertools import islice
from tqdm import tqdm
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import perf_counter
from config import get_api_headers
import urllib3

# Turn off the specific InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


provider_counts = Counter()
failure_counts = Counter()
api_headers = get_api_headers()
TARGET_URL = "https://192.168.1.8:8000/v1/chat/completions"


def single_request(i,
                   routing=None,
                   provider=None):

    payload = {
        "model": "auto",
        "messages": [
            {
                "role": "user",
                "content": f"Say hello #{i}"
            }
        ],
        "max_completion_tokens": 64
    }

    if routing:
        payload["routing"] = routing

    if provider:
        payload["provider"] = provider

    start = perf_counter()

    response = requests.post(
        TARGET_URL,
        json=payload,
        headers=api_headers,
        timeout=120,
        verify=False
    )

    latency = perf_counter() - start

    content_type = response.headers.get("content-type", "")
    try:
        payload = response.json()
    except ValueError as exc:
        return {
            "status": response.status_code,
            "provider": "non_json_response",
            "error": f"{type(exc).__name__}: {exc}",
            "attempted_providers": [],
            "content_type": content_type,
            "body": response.text[:500],
            "latency": latency
        }

    return {
        "status": response.status_code,
        "provider": payload.get("openbalancer", {}).get("provider", "unknown"),
        "error": payload.get("error", {}).get("message") or payload.get("detail"),
        "attempted_providers": payload.get("openbalancer", {}).get("attempted_providers", []),
        "content_type": content_type,
        "body": response.text[:500],
        "latency": latency
    }


def load_test(n: int = 100,
              max_workers: int = 50,
              routing: str = None,
              provider: str = None):

    max_workers = min(max_workers, n)

    start = perf_counter()

    success = 0
    failed = 0
    failure_examples = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:

        futures = [
            executor.submit(single_request,
                            i,
                            routing,
                            provider)
            for i in range(n)
        ]

        with tqdm(
            total=n,
            desc="Load Test",
            unit="req"
        ) as pbar:

            for future in as_completed(futures):

                try:
                    result = future.result()
                    status = result["status"]
                    provider = result["provider"]

                    if status == 200:
                        success += 1
                    else:
                        failed += 1
                        failure_counts[provider] += 1
                        if len(failure_examples) < 5:
                            failure_examples.append(result)

                except Exception as exc:
                    failed += 1
                    provider = "unknown"
                    failure_counts[provider] += 1
                    if len(failure_examples) < 5:
                        failure_examples.append(
                            {"provider": provider, "error": str(exc), "status": None})

                pbar.update(1)

                provider_counts[provider] += 1

                pbar.set_postfix({
                    "ok": success,
                    "fail": failed,
                    "providers": len(provider_counts)
                })

    elapsed = perf_counter() - start

    print(f"\nSuccess: {success}")
    print(f"Failed: {failed}")
    print(f"Time: {elapsed:.2f}s")
    print(f"RPS: {n/elapsed:.2f}")

    print("\nProvider Distribution")

    for provider, count in provider_counts.most_common():
        print(f"{provider}: {count}")

    if failure_counts:
        print("\nFailure Distribution")

        for provider, count in failure_counts.most_common():
            print(f"{provider}: {count}")

        print("\nFailure Examples")
        for item in islice(failure_examples, 5):
            attempted = item.get("attempted_providers") or []
            attempted_text = ", ".join(attempted) if attempted else "n/a"
            body = item.get("body") or ""
            body_text = f" body={body!r}" if body else ""
            print(
                f"- status={item.get('status')} provider={item.get('provider')} "
                f"attempted={attempted_text} content_type={item.get('content_type')} "
                f"error={item.get('error')}{body_text}"
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run concurrent requests against OpenBalancer.")
    parser.add_argument("requests", nargs="?", type=int, default=50)
    parser.add_argument("workers", nargs="?", type=int, default=500)
    parser.add_argument("--routing", default=None)
    parser.add_argument("--provider", default=None)
    args = parser.parse_args()

    load_test(
        args.requests,
        args.workers,
        args.routing,
        args.provider
    )
