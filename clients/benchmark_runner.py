#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 25 00:29:11 2026

@author: dev
"""


import argparse
import csv
import json
import statistics
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import perf_counter
import numpy as np
import requests
from config import get_api_headers


def single_request(
    url,
    routing="balanced",
    provider=None,
    idx=0,
):

    payload = {
        "model": "auto",
        "messages": [
            {
                "role": "user",
                "content": f"Benchmark request {idx}"
            }
        ],
        "max_completion_tokens": 32,
        "routing": routing
    }

    if provider:
        payload["provider"] = provider

    start = perf_counter()

    try:

        response = requests.post(
            url,
            json=payload,
            headers=get_api_headers(),
            timeout=120
        )

        latency = perf_counter() - start

        try:
            data = response.json()
        except:
            data = {}

        return {
            "success": response.status_code == 200,
            "status": response.status_code,
            "latency": latency,
            "provider": (
                data.get("openbalancer", {})
                .get("provider", "unknown")
            )
        }

    except Exception:

        latency = perf_counter() - start

        return {
            "success": False,
            "status": None,
            "latency": latency,
            "provider": "exception"
        }


def run_benchmark(
    url,
    requests_count,
    workers,
    routing,
    provider=None
):

    provider_counts = Counter()

    latencies = []

    success = 0
    failure = 0

    start = perf_counter()

    with ThreadPoolExecutor(max_workers=workers) as pool:

        futures = [
            pool.submit(
                single_request,
                url,
                routing,
                provider,
                i
            )
            for i in range(requests_count)
        ]

        for future in as_completed(futures):

            result = future.result()

            provider_counts[result["provider"]] += 1

            latencies.append(result["latency"])

            if result["success"]:
                success += 1
            else:
                failure += 1

    elapsed = perf_counter() - start

    report = {
        "requests": requests_count,
        "success": success,
        "failure": failure,
        "success_rate": round(
            success / requests_count * 100,
            2
        ),
        "elapsed": round(elapsed, 2),
        "rps": round(
            requests_count / elapsed,
            2
        ),
        "avg_latency_ms":
            round(statistics.mean(latencies) * 1000, 2),

        "p50_ms":
            round(np.percentile(latencies, 50) * 1000, 2),

        "p95_ms":
            round(np.percentile(latencies, 95) * 1000, 2),

        "p99_ms":
            round(np.percentile(latencies, 99) * 1000, 2),

        "providers": dict(provider_counts)
    }

    return report


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument("--url", required=True)

    parser.add_argument("--requests", type=int, default=500)

    parser.add_argument("--workers", type=int, default=100)

    parser.add_argument("--routing", default="balanced")

    parser.add_argument("--provider", default=None)

    args = parser.parse_args()

    result = run_benchmark(
        args.url,
        args.requests,
        args.workers,
        args.routing,
        args.provider
    )

    print(json.dumps(result, indent=2))

    with open("benchmark_result.json", "w") as f:
        json.dump(result, f, indent=2)
