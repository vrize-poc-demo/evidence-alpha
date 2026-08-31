# Practice UI Evaluation

- App URL: http://127.0.0.1:8000/
- Model: local-llama3.1
- Tested: 3/136
- Points: -2/3
- Correct answer + location: 0
- Correct answer, wrong location: 1
- Not found / abstained: 0
- Wrong answer: 2
- UI / timeout errors: 0

## Failed Or Partial

| # | Filing | Expected page(s) | Score | Reason | Question |
| ---: | --- | --- | ---: | --- | --- |
| 1 | 3M_2018_10K | 59 | 0 | correct_answer_wrong_location | What is the FY2018 capital expenditure amount (in USD millions) for 3M? Give a response to the question by relying on the details shown in the cash flow stateme |
| 2 | 3M_2018_10K | 57 | -1 | wrong_answer | Assume that you are a public equities analyst. Answer the following question by primarily using information that is shown in the balance sheet: what is the year |
| 3 | 3M_2022_10K | 47, 49, 51 | -1 | wrong_answer | Is 3M a capital-intensive business based on FY2022 data? |
