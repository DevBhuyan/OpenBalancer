#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Fri Jun  5 21:53:28 2026

@author: dev
"""


import os
from contextlib import redirect_stdout
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests_test import (
    test_requests_completions,
    test_requests_stream,
    test_requests_stream_raw
)
from openai_test import (
    test_openai_response,
    test_openai_stream
)
from litellm_test import (
    test_litellm_completion,
    test_litellm_stream,
    test_litellm_stream_sse
)


def test_all():

    test_litellm_completion()
    test_litellm_stream()
    test_litellm_stream_sse()
    test_openai_response()
    test_openai_stream()
    test_requests_completions()
    test_requests_stream()
    test_requests_stream_raw()


def test_all_concurrently():

    tests = [
        test_litellm_completion,
        test_litellm_stream,
        test_litellm_stream_sse,
        test_openai_response,
        test_openai_stream,
        test_requests_completions,
        test_requests_stream,
        test_requests_stream_raw
    ]

    with ThreadPoolExecutor(max_workers=len(tests)) as executor:

        futures = {
            executor.submit(test): test.__name__
            for test in tests
        }

        for future in as_completed(futures):
            name = futures[future]

            try:
                future.result()
                print(f"✓ {name}")

            except Exception as e:
                print(f"✗ {name}: {e}")


if __name__ == "__main__":

    with open(os.devnull, "w") as devnull:
        with redirect_stdout(devnull):
            test_all()
            test_all_concurrently()
