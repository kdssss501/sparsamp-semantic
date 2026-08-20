import assert from "node:assert/strict";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";
import sharp from "sharp";

const baseUrl = process.env.E2E_BASE_URL || "http://localhost:4321";
const browserPath =
	process.env.PLAYWRIGHT_BROWSER ||
	"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const outputDir = path.resolve("test-results/xiao-intro");
const viewports = [
	{ name: "desktop", width: 1440, height: 900 },
	{ name: "mobile", width: 390, height: 844 },
];

async function waitForIntroTime(page, elapsedMs) {
	await page.waitForFunction(
		(target) =>
			Number(
				document.querySelector("[data-vampire-intro]")?.dataset
					.introElapsedMs,
			) >= target,
		elapsedMs,
		{ timeout: 30_000 },
	);
}

await mkdir(outputDir, { recursive: true });
const browser = await chromium.launch({
	headless: true,
	executablePath: browserPath,
});

async function assertIntroGeometry(page) {
	const geometry = await page.evaluate(() => {
		const title = document.querySelector("[data-intro-title]");
		const canvases = Array.from(
			document.querySelectorAll("[data-chain-canvas]"),
		);
		const video = document.querySelector("[data-intro-video]");
		if (!(title instanceof HTMLElement) || !(video instanceof HTMLVideoElement)) {
			return null;
		}
		const titleBox = title.getBoundingClientRect();
		const nonBlank = canvases.map((canvas) => {
			if (!(canvas instanceof HTMLCanvasElement)) return false;
			const context = canvas.getContext("2d");
			if (!context) return false;
			const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
			for (let index = 3; index < pixels.length; index += 64) {
				if (pixels[index] > 0) return true;
			}
			return false;
		});
		return {
			title: title.getAttribute("aria-label"),
			titleFits: titleBox.left >= 0 && titleBox.right <= window.innerWidth,
			canvasCount: canvases.length,
			chainSources: canvases.map((canvas) => canvas.dataset.chainSource),
			nonBlank,
			videoReady: video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA,
			videoMuted: video.muted,
		};
	});
	assert.ok(geometry, "intro title, chain canvases, or video are missing");
	assert.equal(geometry.title, "VAMPIRE");
	assert.equal(geometry.titleFits, true, "intro title overflowed");
	assert.equal(geometry.canvasCount, 2, "front/back chain canvases are required");
	assert.deepEqual(geometry.chainSources, ["yuimi-direct-port", "yuimi-direct-port"]);
	assert.ok(geometry.nonBlank.some(Boolean), "chain canvases are visually blank");
	assert.equal(geometry.videoReady, true, "cinematic video has not decoded");
	assert.equal(geometry.videoMuted, true, "intro video must remain muted");
}

for (const viewport of viewports) {
	const context = await browser.newContext({ viewport });
	const page = await context.newPage();
	const errors = [];
	page.on("pageerror", (error) => errors.push(error.message));
	await page.goto(`${baseUrl}/live2D/`, {
		waitUntil: "domcontentloaded",
		timeout: 60_000,
	});
	await page.locator("[data-vampire-intro]").waitFor();
	assert.equal(await page.locator(".xiao-workspace").getAttribute("inert"), "");

	await waitForIntroTime(page, 2_500);
	assert.equal(
		await page.locator("[data-vampire-intro]").getAttribute("data-intro-phase"),
		"frames",
	);
	await page.screenshot({
		path: path.join(outputDir, `${viewport.name}-2.5s.png`),
	});

	await waitForIntroTime(page, 7_000);
	assert.equal(errors.length, 0, errors.join("\n"));
	assert.equal(
		await page.locator("[data-vampire-intro]").getAttribute("data-intro-phase"),
		"chain",
	);
	await assertIntroGeometry(page);
	await page.screenshot({
		path: path.join(outputDir, `${viewport.name}-7.0s.png`),
	});

	// Headless Canvas rendering can delay polling; sample early inside the
	// 10.8-13.5s reveal window so the assertion cannot land on the exit cue.
	await waitForIntroTime(page, 11_000);
	assert.equal(
		await page.locator("[data-vampire-intro]").getAttribute("data-intro-phase"),
		"revealed",
	);
	assert.ok(
		Number(await page.locator("[data-intro-title]").evaluate((element) => getComputedStyle(element).opacity)) > 0.5,
		"VAMPIRE title exited before the 13.5 second cue",
	);
	assert.ok(
		Number(await page.locator('[data-chain-canvas="front"]').evaluate((element) => getComputedStyle(element).opacity)) > 0.5,
		"chain canvas exited before the 13.5 second cue",
	);
	await page.screenshot({
		path: path.join(outputDir, `${viewport.name}-12.0s.png`),
	});
	await page.waitForFunction(() => {
		const host = document.querySelector("[data-live2d-host]");
		return (
			host?.dataset.performanceExpression === "stareyes" &&
			host.dataset.performanceAction === "mouse"
		);
	});
	assert.equal(
		await page.locator(".xiao-workspace__scene").getAttribute("data-camera-mode"),
		"portrait",
	);
	const live2dCapture = await page
		.locator("[data-live2d-host] canvas")
		.screenshot({ omitBackground: true });
	const live2dStats = await sharp(live2dCapture).stats();
	assert.ok(
		live2dStats.channels.some((channel) => channel.stdev > 8),
		"revealed Live2D canvas is visually blank",
	);

	await page.locator("[data-vampire-intro]").waitFor({
		state: "detached",
		timeout: 10_000,
	});
	assert.equal(await page.locator(".xiao-workspace").getAttribute("inert"), null);
	await page.screenshot({
		path: path.join(outputDir, `${viewport.name}-complete.png`),
	});
	await page.reload({ waitUntil: "domcontentloaded" });
	await page.waitForFunction(
		() => document.querySelector("[data-vampire-intro]") === null,
		undefined,
		{ timeout: 10_000 },
	);
	assert.equal(await page.locator("[data-vampire-intro]").count(), 0);

	await page.getByRole("button", { name: "重播吸血鬼片头" }).click();
	await page.locator("[data-vampire-intro]").waitFor();
	await page.getByRole("button", { name: "跳过" }).click();
	await page.locator("[data-vampire-intro]").waitFor({ state: "detached" });
	assert.equal(errors.length, 0, errors.join("\n"));
	await context.close();
}

const reducedContext = await browser.newContext({
	viewport: viewports[0],
	reducedMotion: "reduce",
});
const reducedPage = await reducedContext.newPage();
await reducedPage.goto(`${baseUrl}/live2D/`, { waitUntil: "domcontentloaded" });
await reducedPage.waitForFunction(
	() => document.querySelector("[data-vampire-intro]") === null,
	undefined,
	{ timeout: 10_000 },
);
assert.equal(await reducedPage.locator("[data-vampire-intro]").count(), 0);
assert.equal(await reducedPage.locator(".xiao-workspace").getAttribute("inert"), null);
await reducedContext.close();

const failureContext = await browser.newContext({ viewport: viewports[0] });
const failurePage = await failureContext.newPage();
await failurePage.route("**/__local-vampire/**", (route) => route.abort());
await failurePage.goto(`${baseUrl}/live2D/`, { waitUntil: "domcontentloaded" });
await failurePage.locator("[data-vampire-intro]").waitFor();
await failurePage.getByRole("button", { name: "跳过" }).click();
await failurePage
	.locator("[data-vampire-intro]")
	.waitFor({ state: "detached", timeout: 2_000 });
assert.equal(
	await failurePage.locator(".xiao-workspace").getAttribute("inert"),
	null,
);
await failureContext.close();

await browser.close();
console.log("Vampire intro desktop/mobile checks passed.");
