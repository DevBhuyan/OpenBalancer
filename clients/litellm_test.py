#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration tests using LiteLLM library.

LiteLLM provides a unified interface for multiple LLM providers.
These tests demonstrate using LiteLLM with OpenBalancer's OpenAI-compatible
API endpoint with API key authentication.
"""

from litellm import completion
from config import get_api_key


API_KEY = get_api_key()


def test_litellm_completion():
    response = completion(
        model="openai/auto",
        api_base="http://127.0.0.1:8000/v1",
        api_key=API_KEY,
        messages=[
            {
                "role": "user",
                "content": "Hi, how are you?"
            }
        ]
    )

    print(response.choices[0].message.content)
    print(response.model_dump())


def test_litellm_stream():
    response = completion(
        model="openai/auto",
        api_base="http://127.0.0.1:8000/v1",
        api_key=API_KEY,
        stream=True,
        messages=[
            {
                "role": "user",
                "content": "Write a short poem about load balancing."
            }
        ]
    )

    for chunk in response:
        if chunk.choices:
            delta = chunk.choices[0].delta

            if hasattr(delta, "content") and delta.content:
                print(delta.content, end="", flush=True)

    print()


def test_litellm_stream_sse():
    response = completion(
        model="openai/auto",
        api_base="http://127.0.0.1:8000/v1",
        api_key=API_KEY,
        stream=True,
        messages=[
            {
                "role": "user",
                "content": "Count from 1 to 20 slowly."
            }
        ]
    )

    for i, chunk in enumerate(response):
        print(f"\nChunk {i}")
        print(chunk.model_dump())
