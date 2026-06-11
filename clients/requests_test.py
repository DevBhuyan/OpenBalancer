#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration tests using the requests library.

These tests demonstrate making requests to OpenBalancer with API key authentication.
"""

import requests
import json
from config import get_api_headers


BASE_URL = 'https://192.168.1.5:8000/'
url = f"{BASE_URL}v1/chat/completions"
headers = get_api_headers()


def test_requests_completions():
    payload = {
        "model": "auto",
        "messages": [
            {
                "role": "user",
                "content": "Hi, how are you?"
            }
        ],
        "temperature": 0,
        "top_p": 0,
        "max_tokens": 0,
        "max_completion_tokens": 0,
        "stream": False,
        "routing": "fallback",
        "additionalProp1": {}
    }

    response = requests.post(
        url,
        json=payload,
        headers=headers
    )

    if response.status_code == 200:
        result = response.json()
        print(
            f"[{result['openbalancer']['provider']}] {result['model']}: {result['choices'][0]['message']['content']}"
        )
    else:
        print(response.json())


def test_requests_stream():

    payload = {
        "model": "auto",
        "messages": [
            {
                "role": "user",
                "content": "Write a short poem about load balancing."
            }
        ],
        "stream": True
    }

    with requests.post(
        url,
        json=payload,
        headers=headers,
        stream=True,
        verify=False
    ) as response:

        response.raise_for_status()

        for line in response.iter_lines(decode_unicode=True):

            if not line:
                continue

            if not line.startswith("data: "):
                continue

            data = line[6:]

            if data == "[DONE]":
                print("\n[DONE]")
                break

            chunk = json.loads(data)

            try:
                delta = chunk["choices"][0]["delta"]
                content = delta.get("content")

                if content:
                    print(content, end="", flush=True)

            except Exception as e:
                print(f"\nChunk parsing error: {e}")
                print(chunk)


def test_requests_stream_raw():
    payload = {
        "model": "auto",
        "messages": [
            {
                "role": "user",
                "content": "Count from 1 to 10."
            }
        ],
        "stream": True
    }

    with requests.post(
        url,
        json=payload,
        headers=headers,
        stream=True
    ) as response:

        response.raise_for_status()

        for i, line in enumerate(
            response.iter_lines(decode_unicode=True)
        ):
            print(f"\nLine {i}")
            print(repr(line))
