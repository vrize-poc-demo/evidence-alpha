# Practice UI Evaluation

- App URL: http://127.0.0.1:8000/
- Model: local-llama3.1
- Tested: 5/136
- Points: -1/5
- Correct answer + location: 2
- Correct answer, wrong location: 0
- Not found / abstained: 0
- Wrong answer: 3
- UI / timeout errors: 0

## Failed Or Partial

| # | Filing | Expected page(s) | Score | Reason | Question |
| ---: | --- | --- | ---: | --- | --- |
| 2 | 3M_2018_10K | 57 | -1 | wrong_answer | Assume that you are a public equities analyst. Answer the following question by primarily using information that is shown in the balance sheet: what is the year |
| 3 | 3M_2022_10K | 47, 49, 51 | -1 | wrong_answer | Is 3M a capital-intensive business based on FY2022 data? |
| 5 | 3M_2022_10K | 24 | -1 | wrong_answer | If we exclude the impact of M&A, which segment has dragged down 3M's overall growth in 2022? |
