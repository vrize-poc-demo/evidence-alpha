# Practice UI Evaluation

- App URL: http://127.0.0.1:8000/
- Model: local-llama3.1
- Tested: 53/136
- Points: -13/53
- Correct answer + location: 19
- Correct answer, wrong location: 0
- Not found / abstained: 2
- Wrong answer: 24
- UI / timeout errors: 8

## Failed Or Partial

| # | Filing | Expected page(s) | Score | Reason | Question |
| ---: | --- | --- | ---: | --- | --- |
| 2 | 3M_2018_10K | 57 | -1 | wrong_answer | Assume that you are a public equities analyst. Answer the following question by primarily using information that is shown in the balance sheet: what is the year |
| 3 | 3M_2022_10K | 47, 49, 51 | -1 | wrong_answer | Is 3M a capital-intensive business based on FY2022 data? |
| 5 | 3M_2022_10K | 24 | -1 | wrong_answer | If we exclude the impact of M&A, which segment has dragged down 3M's overall growth in 2022? |
| 6 | 3M_2023Q2_10Q | 4 | -1 | wrong_answer | Does 3M have a reasonably healthy liquidity profile based on its quick ratio for Q2 of FY2023? If the quick ratio is not relevant to measure liquidity, please s |
| 9 | ACTIVISIONBLIZZARD_2019_10K | 68, 69 | -1 | wrong_answer | What is the FY2019 fixed asset turnover ratio for Activision Blizzard? Fixed asset turnover ratio is defined as: FY2019 revenue / (average PP&E between FY2018 a |
| 10 | ACTIVISIONBLIZZARD_2019_10K | 69, 72 | -1 | wrong_answer | What is the FY2017 - FY2019 3 year average of capex as a % of revenue for Activision Blizzard? Answer in units of percents and round to one decimal place. Calcu |
| 11 | ADOBE_2015_10K | 58, 62 | -1 | wrong_answer | You are an investment banker and your only resource(s) to answer the following question is (are): the statement of financial position and the cash flow statemen |
| 13 | ADOBE_2017_10K | 56, 60 | -1 | wrong_answer | What is the FY2017 operating cash flow ratio for Adobe? Operating cash flow ratio is defined as: cash from operations / total current liabilities. Round your an |
| 15 | ADOBE_2022_10K | 56 | 0 | not_found_or_abstained | Does Adobe have an improving Free cashflow conversion as of FY2022? |
| 17 | AES_2022_10K | 129, 131 | -1 | wrong_answer | Roughly how many times has AES Corporation sold its inventory in FY2022? Calculate inventory turnover ratio for the FY2022; if conventional inventory management |
| 18 | AES_2022_10K | 129, 131 | -1 | wrong_answer | Based on the information provided primarily in the statement of financial position and the statement of income, what is AES's FY2022 return on assets (ROA)? ROA |
| 19 | AMAZON_2017_10K | 37, 39 | -1 | wrong_answer | What is Amazon's FY2017 days payable outstanding (DPO)? DPO is defined as: 365 * (average accounts payable between FY2016 and FY2017) / (FY2017 COGS + change in |
| 24 | AMCOR_2023_10K | 51 | -1 | wrong_answer | Has AMCOR's quick ratio improved or declined between FY2023 and FY2022? If the quick ratio is not something that a financial analyst would ask about a company l |
| 25 | AMCOR_2023_10K | 63 | -1 | wrong_answer | What are major acquisitions that AMCOR has done in FY2023, FY2022 and FY2021? |
| 26 | AMCOR_2023_10K | 4 | -1 | wrong_answer | What industry does AMCOR primarily operate in? |
| 27 | AMCOR_2023_10K | 49 | -1 | wrong_answer | Does AMCOR have an improving gross margin profile as of FY2023? If gross margin is not a useful metric for a company like this, then state that and explain why. |
| 28 | AMCOR_2023Q2_10Q | 14 | -1 | wrong_answer | What is the nature & purpose of AMCOR's restructuring liability as oF Q2 of FY2023 close? |
| 30 | AMD_2022_10K | 55 | -1 | wrong_answer | Does AMD have a reasonably healthy liquidity profile based on its quick ratio for FY22? If the quick ratio is not relevant to measure liquidity, please state th |
| 31 | AMD_2022_10K | 3 | -1 | wrong_answer | What are the major products and services that AMD sells as of FY22? |
| 32 | AMD_2022_10K | 42 | -1 | wrong_answer | What drove revenue change as of the FY22 for AMD? |
| 34 | AMD_2022_10K | 57 | -1 | wrong_answer | Among operations, investing, and financing activities, which brought in the most (or lost the least) cash flow for AMD in FY22? |
| 37 | AMERICANEXPRESS_2022_10K |  | 0 | not_found_or_abstained | Which debt securities are registered to trade on a national securities exchange under American Express' name as of 2022? |
| 39 | AMERICANEXPRESS_2022_10K | 95 | -1 | wrong_answer | Does AMEX have an improving operating margin profile as of 2022? If operating margin is not a useful metric for a company like this, then state that and explain |
| 40 | AMERICANEXPRESS_2022_10K | 95 | -1 | wrong_answer | What drove gross margin change as of the FY2022 for American Express? If gross margin is not a useful metric for a company like this, then please state that and |
| 43 | AMERICANEXPRESS_2022_10K | 44 | -1 | wrong_answer | Was American Express able to retain card members during 2022? |
| 44 | AMERICANWATERWORKS_2020_10K | 85 | -1 | wrong_answer | How much (in USD billions) did American Water Works pay out in cash dividends for FY2020? Compute or extract the answer by primarily using the details outlined  |
| 46 | AMERICANWATERWORKS_2022_10K | 80, 81 | -1 | ui_or_timeout_error | Does American Water Works have positive working capital based on FY2022 data? If working capital is not a useful or relevant metric for this company, then pleas |
| 47 | BESTBUY_2017_10K | 55 | -1 | ui_or_timeout_error | In agreement with the information outlined in the income statement, what is the FY2015 - FY2017 3 year average net profit margin (as a %) for Best Buy? Answer i |
| 48 | BESTBUY_2019_10K | 51 | -1 | ui_or_timeout_error | What is the year end FY2019 total amount of inventories for Best Buy? Answer in USD millions. Base your judgments on the information provided primarily in the b |
| 49 | BESTBUY_2023_10K | 39 | -1 | ui_or_timeout_error | Are Best Buy's gross margins historically consistent (not fluctuating more than roughly 2% each year)? If gross margins are not a relevant metric for a company  |
| 50 | BESTBUY_2023_10K | 50 | -1 | ui_or_timeout_error | What are major acquisitions that Best Buy has done in FY2023, FY2022 and FY2021? |
| 51 | BESTBUY_2023_10K | 41 | -1 | ui_or_timeout_error | Among operations, investing, and financing activities, which brought in the most (or lost the least) cash flow for Best Buy in FY2023? |
| 52 | BESTBUY_2024Q2_10Q | 19 | -1 | ui_or_timeout_error | Was there any drop in Cash & Cash equivalents between FY 2023 and Q2 of FY2024? |
| 53 | BESTBUY_2024Q2_10Q | 16 | -1 | ui_or_timeout_error | Was there any change in the number of Best Buy stores between Q2 of FY2024 and FY2023? |
