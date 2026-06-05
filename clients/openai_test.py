#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Fri Jun  5 22:19:10 2026

@author: dev
"""


import json
from openai import OpenAI


client = OpenAI(
    api_key="dummy",  # ignored by your server
    base_url="http://127.0.0.1:8000/v1"
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
