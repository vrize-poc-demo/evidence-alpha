# Requirements From The Analyst Copilot Prompt

This project follows the requirements from `The_Analyst_Copilot 1.pdf`.

## Problem Statement

Equity analysts, credit teams, and auditors spend a large amount of time reading annual and quarterly reports to answer questions already contained in the filing. The application must help them answer quickly while avoiding unsupported or invented answers.

## Required Product

Build a chatbot over company annual and quarterly filings.

The chatbot must:

- accept a filing it has never seen before
- show visible processing status
- complete processing within 10 minutes for one filing
- answer analyst-style questions in plain English
- return precise answers with evidence
- show the document and page where evidence came from
- decline when the filing does not contain enough evidence

## Scoring Rule

The prompt makes trust more important than guessing:

- correct answer and correct location: positive score
- correct answer but wrong location: no score
- not found in filing: neutral score
- confidently wrong answer: negative score

This is why Evidence Alpha uses retrieval first, then asks the LLM to answer only from retrieved evidence.

## Dataset

The copied dataset contains:

- `data/practice-questions.jsonl`
- `data/filings/*.htm`

The filings are SEC HTML filings, not PDFs.

## Implemented Mapping

| Prompt Requirement | Evidence Alpha Feature |
| --- | --- |
| Add filing | Upload page |
| Upload new filing | Single and multiple file upload |
| Visible processing status | Global processor bar and dashboard status |
| Chat box | Ask page |
| Evidence on every answer | Evidence drawer with document/page/source text |
| Ability to decline | `not_found` response path |
| README to run app | Root `README.md` |
| One-page approach note | `docs/APPROACH.md` |
