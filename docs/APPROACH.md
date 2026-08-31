# Approach Note

## Problem

Analysts need to ask plain-English questions over long SEC filings and receive precise answers with evidence. A wrong answer is worse than no answer, so the system must be able to abstain.

## What We Built

Evidence Alpha is a React + FastAPI demo app with:

- filing selection
- filing upload
- local SEC HTML parsing
- local indexing
- LLM answer generation
- analyst chat
- cited evidence
- conservative `Not found in this filing` behavior

## Why HTML Parsing

The provided filings are `.htm` SEC filings, not PDFs. Parsing HTML is faster and more reliable for this dataset because the source already contains text, tables, and inline financial tags.

## What We Kept

For the first proof-of-solution, we kept:

- page/chunk-level evidence retrieval
- optional answer-key support for controlled benchmark demos
- simple local indexing
- OpenAI LLM generation from retrieved evidence
- clean demo UI
- explicit evidence display

## What We Deferred

The current app does not yet include:

- embeddings
- vector database
- advanced table reconstruction
- automated benchmark scoring

It also does not train or fine-tune a model. The app uses retrieval-augmented generation: retrieve evidence first, then ask the LLM to answer from that evidence.

These are the right next upgrades after the client demo proves the workflow.

## Measurement Plan

Use `practice-questions.jsonl` to measure:

- top-1 evidence page accuracy
- top-3 evidence page accuracy
- exact answer match for metrics questions
- semantic answer quality for reasoning questions
- abstention quality for unsupported questions

## Recommended Next Implementation

The best production direction is a hybrid retrieval system:

1. HTML/table parser
2. keyword search for exact financial terms
3. vector search for semantic phrasing
4. reranking
5. LLM answer generation
6. answer verifier
7. citation-first UI

That approach keeps the product experience smooth while preserving the trust requirement.
