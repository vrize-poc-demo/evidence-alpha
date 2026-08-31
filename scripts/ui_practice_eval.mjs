#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const QUESTIONS_PATH = path.join(ROOT, "data", "practice-questions.jsonl");
const REPORT_DIR = path.join(ROOT, "reports");
const DEFAULT_APP_URL = "http://127.0.0.1:8000/";

function parseArgs() {
  const args = {
    appUrl: process.env.APP_URL || DEFAULT_APP_URL,
    model: process.env.MODEL_CHOICE || "local-qwen3-14b",
    limit: Number(process.env.LIMIT || 0),
    start: Number(process.env.START || 0),
    timeoutMs: Number(process.env.QUESTION_TIMEOUT_MS || 180000),
    out: process.env.OUT || path.join(REPORT_DIR, `practice-ui-${Date.now()}.json`),
    headless: process.env.HEADLESS !== "false",
  };

  for (let index = 2; index < process.argv.length; index += 1) {
    const arg = process.argv[index];
    const next = process.argv[index + 1];
    if (arg === "--app-url" && next) args.appUrl = next;
    if (arg === "--model" && next) args.model = next;
    if (arg === "--limit" && next) args.limit = Number(next);
    if (arg === "--start" && next) args.start = Number(next);
    if (arg === "--timeout-ms" && next) args.timeoutMs = Number(next);
    if (arg === "--out" && next) args.out = path.resolve(next);
    if (arg === "--headed") args.headless = false;
  }
  return args;
}

function readQuestions() {
  return fs
    .readFileSync(QUESTIONS_PATH, "utf8")
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

function normalizeText(text) {
  return String(text || "")
    .toLowerCase()
    .replace(/\$|usd|us\$|,|\s+/g, " ")
    .replace(/[^\w.%() -]+/g, "")
    .trim();
}

function numericTokens(text) {
  return new Set(String(text || "").match(/-?\(?\d[\d,]*(?:\.\d+)?\)?%?/g) || []);
}

function numericValues(text) {
  return [...numericTokens(text)]
    .map((token) => {
      const isPercent = token.includes("%");
      const clean = token.replace(/[,$%()]/g, "");
      const value = Number(clean);
      if (!Number.isFinite(value)) return null;
      return { value: token.includes("(") ? -value : value, isPercent };
    })
    .filter(Boolean);
}

function numbersMatch(expected, actual) {
  const expectedValues = numericValues(expected);
  if (!expectedValues.length) return false;
  const actualValues = numericValues(actual);
  let matched = 0;
  for (const expectedValue of expectedValues) {
    if (
      actualValues.some((actualValue) => {
        if (actualValue.isPercent !== expectedValue.isPercent) return false;
        const tolerance = Math.max(0.01, Math.abs(expectedValue.value) * 0.01);
        const directMatch = Math.abs(actualValue.value - expectedValue.value) <= tolerance;
        const thousandMatch =
          Math.abs(actualValue.value * 1000 - expectedValue.value) <= tolerance ||
          Math.abs(actualValue.value / 1000 - expectedValue.value) <= tolerance;
        return directMatch || thousandMatch;
      })
    ) {
      matched += 1;
    }
  }
  return matched / expectedValues.length >= 0.6;
}

function expectedPages(row) {
  return new Set((row.evidence || []).map((item) => Number(item.evidence_page_num)).filter(Boolean));
}

function answerLooksCorrect(expected, actual) {
  const expectedNorm = normalizeText(expected);
  const actualNorm = normalizeText(actual);
  if (!expectedNorm || !actualNorm) return false;
  if (actualNorm.includes(expectedNorm)) return true;

  if (numericTokens(expected).size) return numbersMatch(expected, actual);

  const expectedWords = expectedNorm.split(/\s+/).filter((word) => word.length > 3);
  if (!expectedWords.length) return false;
  const matchedWords = expectedWords.filter((word) => actualNorm.includes(word));
  return matchedWords.length / expectedWords.length >= 0.55;
}

function scoreResult(row, result) {
  const answerCorrect = answerLooksCorrect(row.answer, result.answer);
  const pages = expectedPages(row);
  const docCorrect = result.document === row.doc_name;
  const resultPage = Number(result.page);
  const pageCorrect = pages.size === 0 || [...pages].some((page) => Math.abs(page - resultPage) <= 1);
  const locationCorrect = docCorrect && pageCorrect;
  const abstained = result.status !== "answered" || /not found|insufficient/i.test(result.answer || "");

  if (answerCorrect && locationCorrect) {
    return { points: 1, label: "correct_answer_correct_location", answerCorrect, locationCorrect };
  }
  if (answerCorrect && !locationCorrect) {
    return { points: 0, label: "correct_answer_wrong_location", answerCorrect, locationCorrect };
  }
  if (abstained) {
    return { points: 0, label: "not_found_or_abstained", answerCorrect, locationCorrect };
  }
  return { points: -1, label: "wrong_answer", answerCorrect, locationCorrect };
}

function writeReports(outputPath, payload) {
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, JSON.stringify(payload, null, 2));

  const markdownPath = outputPath.replace(/\.json$/i, ".md");
  const failed = payload.results.filter((item) => item.score.points < 1);
  const lines = [
    "# Practice UI Evaluation",
    "",
    `- App URL: ${payload.appUrl}`,
    `- Model: ${payload.model}`,
    `- Tested: ${payload.summary.tested}/${payload.summary.totalAvailable}`,
    `- Points: ${payload.summary.points}/${payload.summary.maxPoints}`,
    `- Correct answer + location: ${payload.summary.correct}`,
    `- Correct answer, wrong location: ${payload.summary.correctWrongLocation}`,
    `- Not found / abstained: ${payload.summary.abstained}`,
    `- Wrong answer: ${payload.summary.wrongAnswer}`,
    `- UI / timeout errors: ${payload.summary.uiErrors}`,
    "",
    "## Failed Or Partial",
    "",
    "| # | Filing | Expected page(s) | Score | Reason | Question |",
    "| ---: | --- | --- | ---: | --- | --- |",
    ...failed.map((item) => {
      const question = item.question.replace(/\|/g, "\\|").slice(0, 160);
      return `| ${item.index + 1} | ${item.expectedDoc} | ${item.expectedPages.join(", ")} | ${item.score.points} | ${item.score.label} | ${question} |`;
    }),
  ];
  fs.writeFileSync(markdownPath, `${lines.join("\n")}\n`);
}

async function importPlaywright() {
  try {
    return await import("playwright");
  } catch {
    console.error("Playwright is not installed.");
    console.error("Run: npm install -D playwright");
    console.error("Then run: npx playwright install chromium");
    process.exit(1);
  }
}

async function waitForIndex(page) {
  await page.getByTestId("nav-chat").click();
  await page.waitForSelector('[data-testid="question-input"]', { timeout: 120000 });
  await page.waitForFunction(() => !document.querySelector('[data-testid="ask-submit"]')?.disabled, null, { timeout: 120000 });
}

async function selectModel(page, model) {
  await page.getByText("Details").click().catch(async () => {
    await page.getByText(/Healthy|Needs attention|Service issue|Checking services/).last().click();
  });
  await page.getByLabel("Selected service").selectOption(model);
  await page.waitForTimeout(1000);
}

async function askQuestion(page, question, timeoutMs) {
  await page.getByTestId("nav-chat").click();
  await page.getByTestId("new-chat").click();
  const beforeCount = await page.locator('[data-testid="answer-card"]').count();
  await page.getByTestId("question-input").fill(question);
  await page.getByTestId("ask-submit").click();
  const card = page.locator('[data-testid="answer-card"]').nth(beforeCount);
  await card.waitFor({ state: "visible", timeout: timeoutMs });
  return {
    status: await card.getAttribute("data-status"),
    document: await card.getAttribute("data-document"),
    page: Number((await card.getAttribute("data-page")) || 0),
    confidence: Number((await card.getAttribute("data-confidence")) || 0),
    model: await card.getAttribute("data-model"),
    answer: (await card.getByTestId("answer-text").innerText()).trim(),
    citation: await card.getByTestId("answer-citation").innerText().catch(() => ""),
  };
}

async function main() {
  const args = parseArgs();
  const questions = readQuestions();
  const selected = questions.slice(args.start, args.limit ? args.start + args.limit : undefined);
  const { chromium } = await importPlaywright();

  const browser = await chromium.launch({ headless: args.headless });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
  const results = [];

  try {
    try {
      await page.goto(args.appUrl, { waitUntil: "networkidle", timeout: 120000 });
      await page.evaluate((model) => {
        localStorage.setItem("evidence-alpha-selected-model", model);
        localStorage.removeItem("evidence-alpha-chat-history");
      }, args.model);
      await page.reload({ waitUntil: "networkidle", timeout: 120000 });
      await selectModel(page, args.model);
      await waitForIndex(page);
    } catch (error) {
      fs.mkdirSync(path.dirname(args.out), { recursive: true });
      const debugBase = args.out.replace(/\.json$/i, "");
      await page.screenshot({ path: `${debugBase}-startup.png`, fullPage: true }).catch(() => {});
      fs.writeFileSync(`${debugBase}-startup.html`, await page.content().catch(() => ""));
      throw error;
    }

    for (let offset = 0; offset < selected.length; offset += 1) {
      const index = args.start + offset;
      const row = selected[offset];
      const startedAt = Date.now();
      let result;
      let score;
      try {
        result = await askQuestion(page, row.question, args.timeoutMs);
        score = scoreResult(row, result);
      } catch (error) {
        result = { status: "error", answer: String(error), document: "", page: 0, confidence: 0, model: args.model, citation: "" };
        score = { points: -1, label: "ui_or_timeout_error", answerCorrect: false, locationCorrect: false };
      }

      results.push({
        index,
        financebenchId: row.financebench_id,
        company: row.company,
        expectedDoc: row.doc_name,
        expectedPages: [...expectedPages(row)],
        expectedAnswer: row.answer,
        question: row.question,
        result,
        score,
        durationMs: Date.now() - startedAt,
      });

      const payload = summarize(args, questions.length, results);
      writeReports(args.out, payload);
      console.log(`${index + 1}/${questions.length} ${score.points} ${score.label} ${row.doc_name}`);
    }
  } finally {
    await browser.close();
  }

  const payload = summarize(args, questions.length, results);
  writeReports(args.out, payload);
  console.log(`Report: ${args.out}`);
  console.log(`Markdown: ${args.out.replace(/\.json$/i, ".md")}`);
}

function summarize(args, totalAvailable, results) {
  const summary = {
    totalAvailable,
    tested: results.length,
    points: results.reduce((sum, item) => sum + item.score.points, 0),
    maxPoints: results.length,
    correct: results.filter((item) => item.score.label === "correct_answer_correct_location").length,
    correctWrongLocation: results.filter((item) => item.score.label === "correct_answer_wrong_location").length,
    abstained: results.filter((item) => item.score.label === "not_found_or_abstained").length,
    wrongAnswer: results.filter((item) => item.score.label === "wrong_answer").length,
    uiErrors: results.filter((item) => item.score.label === "ui_or_timeout_error").length,
  };
  return {
    generatedAt: new Date().toISOString(),
    appUrl: args.appUrl,
    model: args.model,
    start: args.start,
    limit: args.limit || null,
    summary,
    results,
  };
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
