"""
Task 3c: LLM Review Detectors using Gemini 2.5 Flash.
Performs semantic verification ONLY on suspicious rows pre-filtered by cheaper detectors.
Batches rows together to minimize API calls, latency, and cost.
"""

from __future__ import annotations

import json
import os
import time
from typing import Dict, List, Any, Tuple
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


def _get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment.")
    return genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})


class LLMDetectors:
    def __init__(self, model: str = "gemini-3.5-flash-lite"):
        self.model = model
        self.total_tokens_in = 0
        self.total_tokens_out = 0
        self.total_latency_ms = 0.0

    # 1. Semantic Resolution-Status Contradiction Review
    def review_resolution_status_batch(
        self,
        candidate_records: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Reviews rows where Status is 'Closed' or 'Open' but the resolution description
        might be contradictory.
        """
        if not candidate_records:
            return [], {"tokens": 0, "latency_ms": 0}

        client = _get_client()
        prompt = f"""
You are a NYC 311 Data Quality auditor.
Analyze each of the following service requests. Determine if the 'status' strictly CONTRADICTS the 'resolution_description'.
For example, if status is 'Closed' but resolution says 'work is in progress', 'under investigation', or 'unresolved', that is a contradiction.
However, if status is 'Closed' and resolution says 'inspection completed and case closed', that is consistent.

CANDIDATES:
{json.dumps(candidate_records, indent=2)}

Return a JSON array where each object has:
- "unique_key": string,
- "is_contradiction": boolean,
- "confidence": number between 0 and 1,
- "explanation": brief string
"""

        t0 = time.perf_counter()
        try:
            resp = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json",
                ),
            )
            latency = (time.perf_counter() - t0) * 1000
            t_in = resp.usage_metadata.prompt_token_count if resp.usage_metadata else 0
            t_out = resp.usage_metadata.candidates_token_count if resp.usage_metadata else 0
            self.total_tokens_in += t_in
            self.total_tokens_out += t_out
            self.total_latency_ms += latency
            results = json.loads(resp.text or "[]")
        except Exception as e:
            latency = (time.perf_counter() - t0) * 1000
            t_in, t_out = 0, 0
            results = []

        return results, {"tokens_in": t_in, "tokens_out": t_out, "latency_ms": latency}

    # 2. Near-Duplicate Semantic Confirmation
    def review_near_duplicates_batch(
        self,
        candidate_pairs: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Reviews candidate duplicate pairs to confirm if they represent identical events
        reported twice or distinct legitimate complaints.
        """
        if not candidate_pairs:
            return [], {"tokens": 0, "latency_ms": 0}

        client = _get_client()
        prompt = f"""
You are a NYC 311 deduplication analyst.
Analyze these pairs of service requests reported around the same time and location.
Determine if each pair represents a true duplicate (same complaint, duplicate submission) or two distinct issues.

PAIRS:
{json.dumps(candidate_pairs, indent=2)}

Return a JSON array of objects:
- "pair_id": string,
- "is_duplicate": boolean,
- "confidence": number between 0 and 1,
- "reason": brief string
"""

        t0 = time.perf_counter()
        try:
            resp = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json",
                ),
            )
            latency = (time.perf_counter() - t0) * 1000
            t_in = resp.usage_metadata.prompt_token_count if resp.usage_metadata else 0
            t_out = resp.usage_metadata.candidates_token_count if resp.usage_metadata else 0
            self.total_tokens_in += t_in
            self.total_tokens_out += t_out
            self.total_latency_ms += latency
            results = json.loads(resp.text or "[]")
        except Exception as e:
            latency = (time.perf_counter() - t0) * 1000
            t_in, t_out = 0, 0
            results = []

        return results, {"tokens_in": t_in, "tokens_out": t_out, "latency_ms": latency}

    # 3. PII Confirmation (Filtering out false alarms)
    def review_pii_batch(
        self,
        snippets: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Confirms whether regex-flagged snippets contain actual citizen PII (citizen names,
        personal phone numbers, personal emails) vs standard city agency contacts or equipment IDs.
        """
        if not snippets:
            return [], {"tokens": 0, "latency_ms": 0}

        client = _get_client()
        prompt = f"""
You are a privacy compliance officer.
Determine if the following text snippets contain private personal citizen data (PII)
such as personal phone numbers, resident names, or personal emails that should not appear in public records.

SNIPPETS:
{json.dumps(snippets, indent=2)}

Return a JSON array of objects:
- "id": string,
- "contains_pii": boolean,
- "pii_type": "phone" | "email" | "name" | "none",
- "extracted_pii": string
"""

        t0 = time.perf_counter()
        try:
            resp = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json",
                ),
            )
            latency = (time.perf_counter() - t0) * 1000
            t_in = resp.usage_metadata.prompt_token_count if resp.usage_metadata else 0
            t_out = resp.usage_metadata.candidates_token_count if resp.usage_metadata else 0
            self.total_tokens_in += t_in
            self.total_tokens_out += t_out
            self.total_latency_ms += latency
            results = json.loads(resp.text or "[]")
        except Exception as e:
            latency = (time.perf_counter() - t0) * 1000
            t_in, t_out = 0, 0
            results = []

        return results, {"tokens_in": t_in, "tokens_out": t_out, "latency_ms": latency}
