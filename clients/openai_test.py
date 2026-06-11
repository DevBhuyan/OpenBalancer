#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration tests using the OpenAI Python client.

These tests demonstrate using the OpenAI client library with OpenBalancer's
OpenAI-compatible API endpoint with API key authentication.
"""

import json
from openai import OpenAI
from config import get_api_key


client = OpenAI(
    api_key=get_api_key(),  # Use OpenBalancer API key
    base_url="https://192.168.1.5:8000/v1"
)


def test_openai_response():
    response = client.chat.completions.create(
        model="auto",
        messages=[
            {
                "role": "user",
                "content": "Hi, how are you?"
            }
        ]
    )

    print(response.choices[0].message.content)
    print(json.dumps(response.model_dump(), indent=4))


def test_openai_stream():
    stream = client.chat.completions.create(
        model="auto",
        messages=[
            {
                "role": "user",
                "content": "Write a short poem about load balancing."
            }
        ],
        stream=True
    )

    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            print(delta, end="", flush=True)

    print()
