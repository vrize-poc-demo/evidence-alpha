# Practice UI Evaluation

- App URL: http://127.0.0.1:8000/
- Model: local-qwen3-14b
- Tested: 3/136
- Points: -1
- Correct answer + location: 1
- Correct answer, wrong location: 0
- Not found / abstained: 0
- Wrong answer: 2

## Failed Or Partial

| # | Filing | Expected page(s) | Score | Reason | Question |
| ---: | --- | --- | ---: | --- | --- |
| 2 | 3M_2018_10K | 57 | -1 | ui_or_timeout_error | Assume that you are a public equities analyst. Answer the following question by primarily using information that is shown in the balance sheet: what is the year |
| 3 | 3M_2022_10K | 47, 49, 51 | -1 | ui_or_timeout_error | Is 3M a capital-intensive business based on FY2022 data? |
