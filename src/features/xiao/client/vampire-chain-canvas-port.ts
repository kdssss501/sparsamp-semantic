// @ts-nocheck

/**
 * Direct, isolated port of the title-chain pipeline from:
 * Yuimi-chaya.github.io/src/themes/kisara/pages/HomePage.astro:4067-4205,10058-12078.
 * Only the measured title text and the host lifecycle were adapted for VAMPIRE.
 */

export type VampireChainState =
	| "SEAL CHAINS / DORMANT"
	| "SEAL CHAINS / AWAKENING"
	| "OUTER BIND / WRAPPING"
	| "INNER BIND / INTERLOCKING"
	| "SEAL CORE / MAXIMUM TENSION"
	| "CONTRACT SEAL / RUPTURE";

export interface VampireChainFrame {
	fill: number;
	intro: number;
	burst?: number;
	velocity?: number;
	burstVelocity?: number;
}

export interface VampireChainCanvasController {
	resize(force?: boolean): void;
	render(timestamp: number, frame: VampireChainFrame): VampireChainState;
	destroy(): void;
}

interface ChainCanvasOptions {
	back: HTMLCanvasElement;
	front: HTMLCanvasElement;
	root: HTMLElement;
	anchor: HTMLElement;
}

const TITLE_TEXT = "VAMPIRE";
const fullTurn = Math.PI * 2;
const clamp = (value: number, min = 0, max = 1) => Math.min(max, Math.max(min, value));
const smoothstep = (value: number) => value * value * (3 - 2 * value);
const smootherstep = (value: number) => {
	const progress = clamp(value);
	const squared = progress * progress;
	const cubed = squared * progress;
	return cubed * (progress * (progress * 6 - 15) + 10);
};
const phaseProgress = (value: number, start: number, end: number) =>
	smoothstep(clamp((value - start) / Math.max(0.0001, end - start), 0, 1));
const easeOutCubic = (value: number) => 1 - (1 - clamp(value)) ** 3;
const randomSeed = (index: number) => {
	const value = Math.sin(index * 12.9898 + 78.233) * 43758.5453;
	return value - Math.floor(value);
};

const chainDefinitions = [
	{ id: 0, type: "frame", buildStart: 0.025, buildEnd: 0.54, direction: 1, phase: -1.92, radiusX: 0.445, radiusY: 0.13, rotation: -0.02, breakT: 0.18, desktopLinks: 52, mobileLinks: 20, linkScale: 0.98, entryOverscan: 0.16, entryBend: -0.06 },
	{ id: 1, type: "weave", buildStart: 0.1, buildEnd: 0.76, direction: 1, verticalPhase: 0, planePhase: 0, topInset: 0.02, bottomInset: 0.02, xInset: 0.075, xShift: -0.006, breakT: 0.5, desktopLinksPerSegment: 8, mobileLinksPerSegment: 3, linkScale: 0.96, entryOverscan: 0.14, entryBend: 0.09 },
	{ id: 2, type: "weave", buildStart: 0.38, buildEnd: 0.97, direction: -1, verticalPhase: 1, planePhase: 1, topInset: 0.2, bottomInset: 0.18, xInset: 0.055, xShift: 0.008, breakT: 0.44, desktopLinksPerSegment: 7, mobileLinksPerSegment: 3, linkScale: 0.82, entryOverscan: 0.14, entryBend: -0.08 },
];

const catmullCoordinate = (p0: number, p1: number, p2: number, p3: number, unit: number) => {
	const unit2 = unit * unit;
	const unit3 = unit2 * unit;
	return 0.5 * (2 * p1 + (-p0 + p2) * unit + (2 * p0 - 5 * p1 + 4 * p2 - p3) * unit2 + (-p0 + 3 * p1 - 3 * p2 + p3) * unit3);
};

const catmullTangent = (p0: number, p1: number, p2: number, p3: number, unit: number) => {
	const unit2 = unit * unit;
	return 0.5 * (-p0 + p2 + 2 * (2 * p0 - 5 * p1 + 4 * p2 - p3) * unit + 3 * (-p0 + 3 * p1 - 3 * p2 + p3) * unit2);
};

function resolveState(fill: number, intro: number): VampireChainState {
	if (fill <= 0.012) return "SEAL CHAINS / DORMANT";
	if (intro > 0.08) return "CONTRACT SEAL / RUPTURE";
	if (fill < 0.2) return "SEAL CHAINS / AWAKENING";
	if (fill < 0.5) return "OUTER BIND / WRAPPING";
	if (fill < 0.78) return "INNER BIND / INTERLOCKING";
	return "SEAL CORE / MAXIMUM TENSION";
}

export function mountVampireChainCanvas({ back, front, root, anchor }: ChainCanvasOptions): VampireChainCanvasController {
	const backContext = back.getContext("2d", { alpha: true });
	const frontContext = front.getContext("2d", { alpha: true });
	let destroyed = false;
	let mobilePerformance = false;
	let chainCanvasWidth = 1;
	let chainCanvasHeight = 1;
	let chainPixelRatio = 1;
	let chainTitleBox = { left: 0, top: 0, width: 1, height: 1 };
	let chainGlyphLayout = { textLeft: 0, textRight: 0, top: 0, bottom: 0, centerX: 0, centerY: 0, gaps: [], anchorBounds: [] };
	let velocity = 0;
	let burstVelocity = 0;
	const chainLinkUnitCache = new Map();
	const chainLinkSpriteCache = new Map();

	const clearTitleChains = () => {
		for (const [canvas, context] of [[back, backContext], [front, frontContext]]) {
			if (!context) continue;
			context.setTransform(1, 0, 0, 1, 0, 0);
			context.clearRect(0, 0, canvas.width, canvas.height);
			context.setTransform(chainPixelRatio, 0, 0, chainPixelRatio, 0, 0);
			canvas.style.opacity = "0";
		}
	};

	const rebuildTitleChainLayout = () => {
		if (!backContext || chainTitleBox.width <= 1) return;
		const style = window.getComputedStyle(anchor);
		const fontSize = Math.max(1, Number.parseFloat(style.fontSize));
		backContext.save();
		backContext.font = `${style.fontWeight} ${fontSize}px ${style.fontFamily}`;
		backContext.textBaseline = "alphabetic";
		const metrics = backContext.measureText(TITLE_TEXT);
		const measuredWidth = Math.max(1, metrics.width);
		const widthScale = chainTitleBox.width / measuredWidth;
		const centerX = chainTitleBox.left + chainTitleBox.width * 0.5;
		const textLeft = centerX - measuredWidth * widthScale * 0.5;
		const ascent = Number.isFinite(metrics.actualBoundingBoxAscent) && metrics.actualBoundingBoxAscent > 0 ? metrics.actualBoundingBoxAscent : fontSize * 0.72;
		const descent = Number.isFinite(metrics.actualBoundingBoxDescent) && metrics.actualBoundingBoxDescent >= 0 ? metrics.actualBoundingBoxDescent : fontSize * 0.06;
		const top = chainTitleBox.top + chainTitleBox.height * 0.08;
		const bottom = chainTitleBox.top + chainTitleBox.height * 0.92;
		const heightScale = (bottom - top) / Math.max(1, ascent + descent);
		const baseline = top + ascent * heightScale;
		const gaps = [];
		const glyphBounds = [];
		let prefixWidth = 0;
		for (let index = 0; index < TITLE_TEXT.length; index += 1) {
			const nextPrefixWidth = backContext.measureText(TITLE_TEXT.slice(0, index + 1)).width;
			const glyphMetrics = backContext.measureText(TITLE_TEXT[index]);
			const glyphAscent = Number.isFinite(glyphMetrics.actualBoundingBoxAscent) && glyphMetrics.actualBoundingBoxAscent > 0 ? glyphMetrics.actualBoundingBoxAscent : ascent;
			const glyphDescent = Number.isFinite(glyphMetrics.actualBoundingBoxDescent) && glyphMetrics.actualBoundingBoxDescent >= 0 ? glyphMetrics.actualBoundingBoxDescent : descent;
			glyphBounds.push({ left: textLeft + prefixWidth * widthScale, right: textLeft + nextPrefixWidth * widthScale, top: baseline - glyphAscent * heightScale, bottom: baseline + glyphDescent * heightScale });
			if (index < TITLE_TEXT.length - 1) gaps.push(textLeft + nextPrefixWidth * widthScale);
			prefixWidth = nextPrefixWidth;
		}
		backContext.restore();
		const anchorBounds = Array.from({ length: TITLE_TEXT.length + 1 }, (_, index) => {
			if (index === 0) return { top: glyphBounds[0].top, bottom: glyphBounds[0].bottom };
			if (index === TITLE_TEXT.length) {
				const glyph = glyphBounds[glyphBounds.length - 1];
				return { top: glyph.top, bottom: glyph.bottom };
			}
			const leftGlyph = glyphBounds[index - 1];
			const rightGlyph = glyphBounds[index];
			return { top: (leftGlyph.top + rightGlyph.top) * 0.5, bottom: (leftGlyph.bottom + rightGlyph.bottom) * 0.5 };
		});
		chainGlyphLayout = { textLeft, textRight: textLeft + measuredWidth * widthScale, top, bottom, centerX, centerY: chainTitleBox.top + chainTitleBox.height * 0.52, gaps, anchorBounds };
	};

	const resize = (force = false) => {
		if (destroyed || !backContext || !frontContext) return;
		const canvasRect = back.getBoundingClientRect();
		const titleRect = anchor.getBoundingClientRect();
		const width = Math.max(1, canvasRect.width);
		const height = Math.max(1, canvasRect.height);
		mobilePerformance = width < 680 || window.matchMedia("(pointer: coarse)").matches;
		const deviceScale = Math.min(window.devicePixelRatio || 1, mobilePerformance ? 1.08 : width < 640 ? 1.12 : 1.28);
		const pixelRatio = Math.min(deviceScale, 1660 / width, 560 / height);
		const pixelWidth = Math.max(1, Math.round(width * pixelRatio));
		const pixelHeight = Math.max(1, Math.round(height * pixelRatio));
		chainTitleBox = { left: titleRect.left - canvasRect.left, top: titleRect.top - canvasRect.top, width: titleRect.width, height: titleRect.height };
		if (force || back.width !== pixelWidth || back.height !== pixelHeight || Math.abs(chainPixelRatio - pixelRatio) > 0.01) {
			for (const canvas of [back, front]) { canvas.width = pixelWidth; canvas.height = pixelHeight; }
			chainCanvasWidth = width;
			chainCanvasHeight = height;
			chainPixelRatio = pixelRatio;
			chainLinkUnitCache.clear();
			chainLinkSpriteCache.clear();
			clearTitleChains();
		}
		rebuildTitleChainLayout();
	};

	const resolveSealMotion = (fill, intro) => {
		const scrollTension = phaseProgress(fill, 0.48, 1);
		const settle = phaseProgress(intro, 0, 0.018);
		const takeUp = easeOutCubic(clamp(intro / 0.075, 0, 1));
		const lockUnit = clamp((intro - 0.022) / 0.065, 0, 1);
		const lock = easeOutCubic(lockUnit);
		const lockKick = Math.sin(lockUnit * Math.PI) * Math.exp(-lockUnit * 1.2);
		const strain = Math.sin(phaseProgress(intro, 0.012, 0.15) * Math.PI);
		const weavePull = scrollTension * 0.009 + takeUp * 0.038 + lock * 0.018 + lockKick * 0.006;
		return { scrollTension, settle, takeUp, lock, lockKick, strain, weavePull };
	};

	const resolveTitleChainPath = (definition, fill, intro) => {
		if (definition.type === "frame") return { type: "frame", segmentCount: 4 };
		const box = chainTitleBox;
		const layout = chainGlyphLayout;
		const fallbackGaps = [0.14, 0.285, 0.43, 0.57, 0.715, 0.86].map((unit) => box.left + box.width * unit);
		const gaps = layout.gaps.length === TITLE_TEXT.length - 1 ? layout.gaps : fallbackGaps;
		const textLeft = layout.textRight > layout.textLeft ? layout.textLeft : box.left;
		const textRight = layout.textRight > layout.textLeft ? layout.textRight : box.left + box.width;
		const centerX = layout.centerX || box.left + box.width * 0.5;
		const centerY = layout.centerY || box.top + box.height * 0.52;
		const fallbackTop = layout.bottom > layout.top ? layout.top : box.top;
		const fallbackBottom = layout.bottom > layout.top ? layout.bottom : box.top + box.height;
		const xShift = box.width * definition.xShift;
		const anchorXs = [textLeft - box.width * definition.xInset, ...gaps.map((gap) => gap + xShift), textRight + box.width * definition.xInset];
		const anchorBounds = layout.anchorBounds.length === anchorXs.length ? layout.anchorBounds : anchorXs.map(() => ({ top: fallbackTop, bottom: fallbackBottom }));
		const { takeUp, lock, lockKick, weavePull: pull } = resolveSealMotion(fill, intro);
		const pointSpan = Math.max(1, anchorXs.length - 1);
		const points = anchorXs.map((x, index) => {
			const upper = (index + definition.verticalPhase) % 2 === 0;
			const bounds = anchorBounds[index];
			const localTop = Number.isFinite(bounds?.top) ? bounds.top : fallbackTop;
			const localBottom = Number.isFinite(bounds?.bottom) ? bounds.bottom : fallbackBottom;
			const localHeight = Math.max(1, localBottom - localTop);
			const top = localTop + localHeight * definition.topInset;
			const bottom = localBottom - localHeight * definition.bottomInset;
			const endpointEase = index === 0 || index === anchorXs.length - 1 ? 0.08 : 0;
			const y = upper ? top + localHeight * endpointEase : bottom - localHeight * endpointEase;
			const pointUnit = index / pointSpan;
			const windingWave = 0.5 + 0.5 * Math.cos(pointUnit * fullTurn * 1.55 + definition.verticalPhase * Math.PI - takeUp * fullTurn * 0.42);
			const localPull = pull * (0.58 + windingWave * 0.62);
			const localTwist = definition.direction * (takeUp * 0.105 + lock * 0.044 + lockKick * 0.012) * (0.42 + windingWave * 0.58);
			const offsetX = x - centerX;
			const offsetY = y - centerY;
			const tightenedX = offsetX * (1 - localPull);
			const tightenedY = offsetY * (1 - localPull);
			return { x: centerX + tightenedX * Math.cos(localTwist) - tightenedY * Math.sin(localTwist), y: centerY + tightenedX * Math.sin(localTwist) + tightenedY * Math.cos(localTwist) };
		});
		return { type: "weave", points, segmentCount: Math.max(1, points.length - 1) };
	};

	const getChainLinkDimensions = (definition) => {
		const mobileGeometry = mobilePerformance || chainTitleBox.width < 420;
		const linkUnit = clamp(chainTitleBox.height * (mobileGeometry ? 0.122 : 0.108), mobileGeometry ? 9.2 : 8.4, mobileGeometry ? 15.8 : 16.8) * definition.linkScale;
		return { width: linkUnit * 1.82, height: linkUnit * 1.02 };
	};

	const sampleTitleChain = (definition, path, unit, fill, intro, timestamp) => {
		const box = chainTitleBox;
		const centerX = chainGlyphLayout.centerX || box.left + box.width * 0.5;
		const centerY = chainGlyphLayout.centerY || box.top + box.height * 0.52;
		const { scrollTension, settle, takeUp, lock, lockKick, strain } = resolveSealMotion(fill, intro);
		const frameMotionResponse = definition.type === "frame" ? clamp(Math.abs(velocity) * 320 + Math.abs(burstVelocity) * 220 + phaseProgress(intro, 0, 0.018), 0, 1) : 1;
		const localTakeUp = smootherstep(clamp((takeUp - 0.018) / 0.982));
		let x = centerX, y = centerY, tangentX = 1, tangentY = 0, plane = "back", crossing = false, depth = 0;
		if (definition.type === "frame") {
			const layout = chainGlyphLayout;
			const mobileGeometry = mobilePerformance || box.width < 420;
			const glyphWidth = layout.textRight > layout.textLeft ? layout.textRight - layout.textLeft : box.width;
			const glyphHeight = layout.bottom > layout.top ? layout.bottom - layout.top : box.height * 0.84;
			const frameCenterX = layout.centerX || centerX;
			const frameCenterY = layout.centerY || centerY;
			const radiusX = glyphWidth * definition.radiusX * (mobileGeometry ? 1.04 : 1) * (1 - scrollTension * 0.004);
			const radiusY = glyphHeight * definition.radiusY * (mobileGeometry ? 2.6 : 1) * (1 - scrollTension * 0.006);
			const angle = definition.phase + definition.direction * unit * fullTurn;
			const framePoint = (sampleAngle) => {
				const c = Math.cos(sampleAngle), s = Math.sin(sampleAngle);
				const cinchWave = 0.5 + 0.5 * Math.cos((sampleAngle - definition.phase) * 2.05 - takeUp * fullTurn * 1.08 + lock * 1.4);
				const localCinch = takeUp * (0.022 + cinchWave * 0.058) + lock * (0.018 + (1 - cinchWave) * 0.038) + lockKick * cinchWave * 0.016;
				const localX = Math.sign(c) * Math.abs(c) ** 0.68 * radiusX * (0.965 + s * 0.035) * (1 - localCinch);
				const localY = Math.sign(s) * Math.abs(s) ** 0.68 * radiusY * (1 - localCinch * 1.12);
				return { x: frameCenterX + localX * Math.cos(definition.rotation) - localY * Math.sin(definition.rotation), y: frameCenterY + localX * Math.sin(definition.rotation) + localY * Math.cos(definition.rotation) };
			};
			const point = framePoint(angle);
			const tangentPoint = framePoint(angle + definition.direction * 0.0025);
			x = point.x; y = point.y; tangentX = tangentPoint.x - x; tangentY = tangentPoint.y - y;
			const slackBlend = clamp(scrollTension * 0.2 + settle * 0.14 + localTakeUp * 0.72 + lock * 0.16);
			const wobble = Math.sin(angle * 2.35 + timestamp * 0.00038 + definition.id * 1.37) * box.height * (0.008 + (0.0015 - 0.008) * slackBlend) * frameMotionResponse;
			const tangentLength = Math.max(0.001, Math.hypot(tangentX, tangentY));
			x += -tangentY / tangentLength * wobble; y += tangentX / tangentLength * wobble;
			depth = clamp((y - centerY) / Math.max(1, radiusY * 1.04), -1, 1);
			plane = depth >= 0 ? "front" : "back";
			crossing = Math.abs(depth) <= clamp(getChainLinkDimensions(definition).height / Math.max(1, radiusY * 5.4), 0.1, 0.2);
		} else {
			const reelStrength = takeUp * 0.1 + lock * 0.042 + lockKick * 0.014;
			const reelWave = 0.64 + 0.36 * Math.cos((unit - definition.breakT) * fullTurn * 1.38 - takeUp * Math.PI * 1.55 + definition.id * 0.73);
			const reeledUnit = clamp(unit + (definition.breakT - unit) * reelStrength * reelWave);
			const segmentPosition = reeledUnit * path.segmentCount;
			const segmentIndex = Math.min(path.segmentCount - 1, Math.floor(Math.min(segmentPosition, path.segmentCount - 0.000001)));
			const localUnit = clamp(segmentPosition - segmentIndex);
			const p0 = path.points[Math.max(0, segmentIndex - 1)], p1 = path.points[segmentIndex], p2 = path.points[Math.min(path.points.length - 1, segmentIndex + 1)], p3 = path.points[Math.min(path.points.length - 1, segmentIndex + 2)];
			x = catmullCoordinate(p0.x, p1.x, p2.x, p3.x, localUnit); y = catmullCoordinate(p0.y, p1.y, p2.y, p3.y, localUnit);
			tangentX = catmullTangent(p0.x, p1.x, p2.x, p3.x, localUnit); tangentY = catmullTangent(p0.y, p1.y, p2.y, p3.y, localUnit);
			plane = (segmentIndex + definition.planePhase) % 2 === 0 ? "front" : "back";
			const nearestBoundary = Math.round(segmentPosition);
			crossing = nearestBoundary > 0 && nearestBoundary < path.segmentCount && Math.abs(segmentPosition - nearestBoundary) < 0.045;
		}
		const tangentLength = Math.max(0.001, Math.hypot(tangentX, tangentY));
		tangentX /= tangentLength; tangentY /= tangentLength;
		const normalX = -tangentY, normalY = tangentX;
		const tensionWave = Math.sin(timestamp * (0.0008 + strain * 0.0032) + unit * fullTurn * (2.1 + definition.id * 0.16) + definition.id * 1.73);
		const residualSlack = 1 - clamp(settle * 0.14 + localTakeUp * 0.72 + lock * 0.16);
		const tensionOffset = tensionWave * box.height * (0.0014 + residualSlack * 0.0036 + strain * 0.0042) * frameMotionResponse;
		x += normalX * tensionOffset; y += normalY * tensionOffset;
		return { x, y, tangentX, tangentY, normalX, normalY, angle: Math.atan2(tangentY, tangentX), plane, crossing, depth };
	};

	const sampleTitleChainTravel = (definition, path, distanceUnit, spacing, fill, intro, timestamp) => {
		if (distanceUnit >= 0 && distanceUnit <= 1) return sampleTitleChain(definition, path, spacing.unitAtDistance(distanceUnit), fill, intro, timestamp);
		const boundaryUnit = distanceUnit < 0 ? 0 : 1;
		const boundary = sampleTitleChain(definition, path, boundaryUnit, fill, intro, timestamp);
		const outsideDistance = Math.abs(distanceUnit - boundaryUnit) * spacing.totalLength;
		const direction = distanceUnit < 0 ? -1 : 1;
		const bend = Math.sin(clamp(outsideDistance / Math.max(1, chainTitleBox.height * 2.4)) * Math.PI) * chainTitleBox.height * definition.entryBend;
		return { ...boundary, x: boundary.x + boundary.tangentX * direction * outsideDistance + boundary.normalX * bend, y: boundary.y + boundary.tangentY * direction * outsideDistance + boundary.normalY * bend, plane: "back", crossing: false };
	};

	const buildTitleChainLinkUnits = (definition, isMobile) => {
		const cacheKey = [definition.id, Math.round(chainTitleBox.width), Math.round(chainTitleBox.height), isMobile ? 1 : 0].join(":");
		const cached = chainLinkUnitCache.get(cacheKey); if (cached) return cached;
		const spacingPath = resolveTitleChainPath(definition, 0, 0);
		const sampleCount = definition.type === "frame" ? (isMobile ? 110 : 180) : (isMobile ? 88 : 140);
		const samples = [{ unit: 0, length: 0 }];
		let totalLength = 0;
		let previous = sampleTitleChain(definition, spacingPath, 0, 0, 0, 0);
		for (let index = 1; index <= sampleCount; index += 1) {
			const unit = index / sampleCount;
			const current = sampleTitleChain(definition, spacingPath, unit, 0, 0, 0);
			totalLength += Math.hypot(current.x - previous.x, current.y - previous.y);
			samples.push({ unit, length: totalLength }); previous = current;
		}
		const dimensions = getChainLinkDimensions(definition);
		const spacingFactor = definition.type === "frame" ? (isMobile ? 1.04 : 0.64) : (isMobile ? 0.98 : 0.6);
		const desiredCount = Math.round(totalLength / (dimensions.width * spacingFactor));
		const minimum = definition.type === "frame" ? (isMobile ? definition.mobileLinks : definition.desktopLinks) : (isMobile ? definition.mobileLinksPerSegment : definition.desktopLinksPerSegment) * spacingPath.segmentCount + 1;
		const maximum = definition.type === "frame" ? (isMobile ? 28 : 110) : (isMobile ? 22 : 86);
		let linkCount = Math.round(clamp(desiredCount, minimum, maximum));
		if (definition.type === "frame" && linkCount % 2 !== 0) linkCount += linkCount < maximum ? 1 : -1;
		const unitAtLength = (targetLength) => {
			let low = 1, high = samples.length - 1;
			while (low < high) { const middle = Math.floor((low + high) * 0.5); if (samples[middle].length < targetLength) low = middle + 1; else high = middle; }
			const upper = samples[low], lower = samples[Math.max(0, low - 1)];
			return lower.unit + (upper.unit - lower.unit) * clamp((targetLength - lower.length) / Math.max(0.0001, upper.length - lower.length));
		};
		const lengthAtUnit = (targetUnit) => { const position = clamp(targetUnit) * sampleCount; const lower = Math.floor(position), upper = Math.min(samples.length - 1, lower + 1); return samples[lower].length + (samples[upper].length - samples[lower].length) * (position - lower); };
		const records = Array.from({ length: linkCount }, (_, index) => { const distanceUnit = definition.type === "frame" ? (index + 0.5) / linkCount : index / Math.max(1, linkCount - 1); return { distanceUnit, unit: unitAtLength(distanceUnit * totalLength) }; });
		if (definition.type === "weave") {
			for (let boundary = 1; boundary < spacingPath.segmentCount; boundary += 1) {
				const boundaryUnit = boundary / spacingPath.segmentCount, boundaryDistanceUnit = lengthAtUnit(boundaryUnit) / totalLength;
				let nearestIndex = 0, nearestDistance = Infinity;
				for (let index = 0; index < records.length; index += 1) { const distance = Math.abs(records[index].distanceUnit - boundaryDistanceUnit); if (distance < nearestDistance) { nearestDistance = distance; nearestIndex = index; } }
				records[nearestIndex] = { distanceUnit: boundaryDistanceUnit, unit: boundaryUnit };
			}
			records.sort((left, right) => left.distanceUnit - right.distanceUnit);
		}
		const spacing = { records, totalLength, unitAtDistance: (distanceUnit) => unitAtLength(clamp(distanceUnit) * totalLength), distanceAtUnit: (unit) => lengthAtUnit(clamp(unit)) / totalLength };
		chainLinkUnitCache.set(cacheKey, spacing); if (chainLinkUnitCache.size > 24) chainLinkUnitCache.delete(chainLinkUnitCache.keys().next().value);
		return spacing;
	};

	const getChainLinkSprite = (definition, isFront, arcPart, hot, parity, variant) => {
		const dimensions = getChainLinkDimensions(definition);
		const cacheKey = [definition.id, Math.round(dimensions.width * 10), Math.round(dimensions.height * 10), isFront ? 1 : 0, arcPart, hot ? 1 : 0, parity, variant].join(":");
		const cached = chainLinkSpriteCache.get(cacheKey); if (cached) return cached;
		const simplifiedChain = mobilePerformance || chainTitleBox.width < 420;
		const spriteScale = simplifiedChain ? 1.55 : 2.4;
		const padding = simplifiedChain ? (isFront ? 8 : 7) : (isFront ? 12 : 10);
		const width = dimensions.width + padding * 2, height = dimensions.height + padding * 2;
		const canvas = document.createElement("canvas"); canvas.width = Math.ceil(width * spriteScale); canvas.height = Math.ceil(height * spriteScale);
		const context = canvas.getContext("2d", { alpha: true }); if (!context) return null;
		context.setTransform(spriteScale, 0, 0, spriteScale, width * spriteScale * 0.5, height * spriteScale * 0.5);
		context.lineCap = "round"; context.lineJoin = "round";
		const detailedMetal = !simplifiedChain && isFront && arcPart === "near";
		const variantUnit = variant / 2, toneShift = variantUnit - 0.5, nearUsesLowerArc = parity === 0;
		const lowerArc = [-Math.PI * 0.08, Math.PI * 1.08], upperArc = [Math.PI * 0.92, Math.PI * 2.08];
		const [arcStart, arcEnd] = arcPart === "full" ? [0, fullTurn] : arcPart === "near" ? (nearUsesLowerArc ? lowerArc : upperArc) : (nearUsesLowerArc ? upperArc : lowerArc);
		const prominentArc = arcPart !== "far";
		const metal = context.createLinearGradient(0, -dimensions.height * 0.62, 0, dimensions.height * 0.62);
		const stops = hot
			? [[0,`hsla(${337+toneShift*5},28%,${6+variantUnit*1.5}%,.99)`],[.13,`hsla(${342+toneShift*6},28%,${16+variantUnit*3}%,.99)`],[.27,`hsla(${350+toneShift*4},22%,${63+variantUnit*5}%,.99)`],[.39,`hsla(${344+toneShift*5},46%,${29+variantUnit*4}%,.99)`],[.58,`hsla(${336+toneShift*4},32%,${9+variantUnit*2}%,.99)`],[.76,`hsla(${349+toneShift*5},48%,${34+variantUnit*5}%,.99)`],[.9,`hsla(${339+toneShift*4},30%,${14+variantUnit*3}%,.99)`],[1,`hsla(${354+toneShift*4},38%,${54+variantUnit*6}%,.98)`]]
			: [[0,`hsla(${220+toneShift*5},28%,${5+variantUnit*1.5}%,.99)`],[.12,`hsla(${218+toneShift*6},24%,${17+variantUnit*3}%,.99)`],[.25,`hsla(${215+toneShift*4},14%,${73+variantUnit*5}%,.99)`],[.37,`hsla(${217+toneShift*5},22%,${35+variantUnit*5}%,.99)`],[.58,`hsla(${221+toneShift*5},28%,${9+variantUnit*2}%,.99)`],[.76,`hsla(${214+toneShift*5},20%,${42+variantUnit*6}%,.99)`],[.9,`hsla(${222+toneShift*4},24%,${14+variantUnit*3}%,.99)`],[1,`hsla(${212+toneShift*4},14%,${64+variantUnit*7}%,.98)`]];
		for (const [stop, color] of stops) metal.addColorStop(stop, color);
		for (const pass of [{ color:"rgba(3,4,13,.98)", width:isFront ? 5.7 : 5.05, alpha:prominentArc ? .96 : .72 }, { color:metal, width:isFront ? 3.45 : 3, alpha:prominentArc ? 1 : .8 }]) { context.globalAlpha=pass.alpha; context.strokeStyle=pass.color; context.lineWidth=pass.width*(.95+variantUnit*.08); context.beginPath(); context.ellipse(0,0,dimensions.width*.5,dimensions.height*.5,0,arcStart,arcEnd); context.stroke(); }
		context.globalCompositeOperation = "multiply"; context.globalAlpha = prominentArc ? 0.74 : 0.52; context.strokeStyle = hot ? "rgba(41,3,18,.92)" : "rgba(5,10,24,.9)"; context.lineWidth = 0.94 + variantUnit * 0.18; context.beginPath(); context.ellipse(0, dimensions.height * .045, dimensions.width * .455, dimensions.height * .415, 0, arcStart + Math.PI*.08, arcEnd - Math.PI*.08); context.stroke();
		if (detailedMetal) {
			context.globalCompositeOperation="screen"; context.globalAlpha=hot ? .58+variantUnit*.08 : .46+variantUnit*.08; context.strokeStyle=hot ? "rgba(255,224,232,.9)" : "rgba(226,235,248,.9)"; context.lineWidth=.66+variantUnit*.12; context.beginPath(); context.ellipse(0,-dimensions.height*.04,dimensions.width*.438,dimensions.height*.39,0,arcStart+(arcEnd-arcStart)*(.11+variantUnit*.035),arcStart+(arcEnd-arcStart)*(.5+variantUnit*.1)); context.stroke();
			context.globalCompositeOperation="source-over"; for(let wearIndex=0;wearIndex<2+variant;wearIndex+=1){const wearUnit=.2+wearIndex*(.58/Math.max(1,1+variant))+parity*.022+toneShift*.018;const wearAngle=arcStart+(arcEnd-arcStart)*wearUnit;const wearX=Math.cos(wearAngle)*dimensions.width*.47,wearY=Math.sin(wearAngle)*dimensions.height*.45,tx=-Math.sin(wearAngle),ty=Math.cos(wearAngle),length=.7+wearIndex*.27+variantUnit*.24;context.globalAlpha=hot ? .28+variantUnit*.06 : .23+variantUnit*.05;context.strokeStyle="rgba(4,5,14,.96)";context.lineWidth=.5+variantUnit*.13;context.beginPath();context.moveTo(wearX-tx*length,wearY-ty*length);context.lineTo(wearX+tx*length,wearY+ty*length);context.stroke();}
		}
		const sprite = { canvas, width, height }; chainLinkSpriteCache.set(cacheKey, sprite); return sprite;
	};

	const drawChainLinkArc = (context, record, isFront, arcPart) => {
		const { sample, linkIndex, definition, alpha, heat, rotationOffset = 0, scale = 1, lengthScale = 1 } = record; if (alpha <= .002) return;
		const parity=linkIndex%2, edgeOn=parity===1, frameDepth=Number.isFinite(sample.depth)?sample.depth:0;
		const layerAlpha=alpha*(definition.type==="frame"?(isFront ? .82+Math.max(0,frameDepth)*.18 : .78+Math.max(0,-frameDepth)*.16):(isFront ? 1 : .66));
		const variantSeed=randomSeed(41011+definition.id*701.3+linkIndex*43.17+parity*17.9), shapeSeed=randomSeed(52021+definition.id*389.7+linkIndex*71.11), variant=Math.min(2,Math.floor(variantSeed*3));
		const heatBlend=smootherstep(clamp((heat-(variantSeed-.5)*.1)/.96)), resolvedHeat=heatBlend*clamp((isFront ? .84 : .78)+variant*.03,0,.92), frameLink=definition.type==="frame";
		const sizeVariation=frameLink ? .97+shapeSeed*.06 : .92+shapeSeed*.15, aspectVariation=frameLink ? .98+variantSeed*.04 : .94+variantSeed*.12;
		const horizontalScale=scale*sizeVariation*aspectVariation*(edgeOn?(frameLink?lengthScale:1.08):1), verticalScale=scale*sizeVariation*(edgeOn ? .37+(variantSeed-.5)*.03 : 1.02)/aspectVariation;
		const coldSprite=resolvedHeat<.985?getChainLinkSprite(definition,isFront,arcPart,false,parity,variant):null, hotSprite=resolvedHeat>.015?getChainLinkSprite(definition,isFront,arcPart,true,parity,variant):null;
		context.save();context.translate(sample.x,sample.y);context.rotate(sample.angle+(edgeOn ? .045 : -.035)+(variantSeed-.5)*(frameLink ? .03 : .085)+rotationOffset);context.scale(horizontalScale,verticalScale);context.imageSmoothingEnabled=true;
		if(coldSprite){context.globalAlpha=layerAlpha*(1-resolvedHeat);context.drawImage(coldSprite.canvas,-coldSprite.width*.5,-coldSprite.height*.5,coldSprite.width,coldSprite.height);} if(hotSprite){context.globalAlpha=layerAlpha*resolvedHeat;context.drawImage(hotSprite.canvas,-hotSprite.width*.5,-hotSprite.height*.5,hotSprite.width,hotSprite.height);} context.restore();
	};

	const drawChainLayer = (context, records, isFront) => {
		if (mobilePerformance || chainTitleBox.width < 420) { for (const record of records) drawChainLinkArc(context, record, isFront, record.arcMode === "full" ? "full" : record.arcMode); return; }
		for (const pass of [{arcPart:"far",edgeOn:false},{arcPart:"far",edgeOn:true},{arcPart:"near",edgeOn:false},{arcPart:"near",edgeOn:true}]) for (const record of records) { if ((record.linkIndex%2===1)!==pass.edgeOn) continue; if(record.arcMode!=="full"&&record.arcMode!==pass.arcPart) continue; drawChainLinkArc(context,record,isFront,pass.arcPart); }
	};

	const drawChainLeader = (context, leader) => {
		if(!leader||leader.alpha<=.002)return;const {definition,sample,alpha,heat}=leader,dimensions=getChainLinkDimensions(definition),forward=definition.direction>0?1:-1;
		context.save();context.translate(sample.x,sample.y);context.rotate(sample.angle+(forward<0?Math.PI:0));context.globalCompositeOperation="screen";context.lineCap="round";const trail=context.createLinearGradient(-dimensions.width*1.9,0,-dimensions.width*.08,0);trail.addColorStop(0,"rgba(117,161,255,0)");trail.addColorStop(.68,"rgba(255,255,255,.08)");trail.addColorStop(1,"rgba(255,248,252,.5)");context.globalAlpha=alpha*(.34+heat*.2);context.strokeStyle=trail;context.lineWidth=1.05+Math.abs(velocity)*15;context.beginPath();context.moveTo(-dimensions.width*1.9,0);context.lineTo(-dimensions.width*.08,0);context.stroke();context.restore();
	};

	const createContractHeartPath=(centerX,centerY,size,scale=1)=>{const r=size*scale,path=new Path2D();path.moveTo(centerX,centerY+r*.74);path.bezierCurveTo(centerX-r*.16,centerY+r*.58,centerX-r*.92,centerY+r*.12,centerX-r*.92,centerY-r*.34);path.bezierCurveTo(centerX-r*.92,centerY-r*.73,centerX-r*.48,centerY-r*.92,centerX,centerY-r*.47);path.bezierCurveTo(centerX+r*.48,centerY-r*.92,centerX+r*.92,centerY-r*.73,centerX+r*.92,centerY-r*.34);path.bezierCurveTo(centerX+r*.92,centerY+r*.12,centerX+r*.16,centerY+r*.58,centerX,centerY+r*.74);path.closePath();return path;};

	const drawContractHeartImprint=(timestamp,intro,events,visibility,isMobile)=>{if(!backContext||!frontContext||events.length===0)return;const build=smootherstep(clamp((intro-.23)/.105)),collapse=smootherstep(clamp((intro-.68)/.105)),fade=1-smootherstep(clamp((intro-.84)/.11)),opacity=build*fade*visibility;if(opacity<=.001)return;const centerX=(chainGlyphLayout.centerX||chainTitleBox.left+chainTitleBox.width*.5)+chainTitleBox.width*.012,centerY=(chainGlyphLayout.centerY||chainTitleBox.top+chainTitleBox.height*.52)+chainTitleBox.height*.045,lockPulse=Math.exp(-Math.pow((intro-.36)/.042,2)),heartbeat=.5+Math.sin(timestamp*.016)*.5,size=clamp(chainTitleBox.height*(isMobile ? .205 : .19),isMobile ? 15 : 17,isMobile ? 25 : 32),heartScale=(.76+build*.24+lockPulse*.08)*(1-collapse*.56),heart=createContractHeartPath(centerX,centerY,size,heartScale);
		backContext.save();backContext.globalAlpha=opacity*(.3+lockPulse*.08);backContext.fillStyle="rgba(66,7,43,.8)";backContext.shadowColor="rgba(255,43,115,.3)";backContext.shadowBlur=4+lockPulse*3;backContext.fill(heart);backContext.globalAlpha=opacity*.78;backContext.strokeStyle="rgba(24,5,28,.96)";backContext.lineWidth=4.2;backContext.stroke(heart);backContext.restore();
		frontContext.save();frontContext.globalCompositeOperation="screen";frontContext.globalAlpha=opacity*(.24+lockPulse*.16);frontContext.fillStyle="rgba(255,53,121,.9)";frontContext.shadowColor="rgba(255,47,117,.56)";frontContext.shadowBlur=4+lockPulse*6;frontContext.fill(heart);frontContext.globalAlpha=opacity*(.82+heartbeat*.1);frontContext.strokeStyle="rgba(255,72,137,.99)";frontContext.lineWidth=2.1+lockPulse*.42;frontContext.stroke(heart);frontContext.globalAlpha=opacity*(.58+lockPulse*.24);frontContext.strokeStyle="rgba(255,247,251,.98)";frontContext.lineWidth=.68+lockPulse*.28;frontContext.stroke(heart);frontContext.restore();
	};

	const drawChainRupture=(timestamp,intro,events,visibility,isMobile)=>{if(!frontContext||events.length===0)return;const stressPulse=Math.sin(phaseProgress(intro,.012,.145)*Math.PI),rupturePulse=Math.sin(phaseProgress(intro,.1,.48)*Math.PI);if(Math.max(stressPulse,rupturePulse)<=.001)return;frontContext.save();frontContext.globalCompositeOperation="screen";frontContext.lineCap="round";for(const event of events){const {breakSample,breakSeed,heat,breakOpen,snapPulse}=event,dimensions=getChainLinkDimensions(event.definition);if(stressPulse>.001&&breakOpen<.98){const length=dimensions.width*(.4+stressPulse*.42);frontContext.globalAlpha=visibility*stressPulse*(1-breakOpen)*.72;frontContext.strokeStyle=heat>.5?"rgba(255,229,240,.98)":"rgba(226,238,255,.96)";frontContext.lineWidth=.8+stressPulse*1.2;frontContext.beginPath();frontContext.moveTo(breakSample.x-breakSample.tangentX*length,breakSample.y-breakSample.tangentY*length);frontContext.lineTo(breakSample.x+breakSample.tangentX*length,breakSample.y+breakSample.tangentY*length);frontContext.stroke();} if(snapPulse>.002){const radius=dimensions.width*(.24+snapPulse*.46),core=frontContext.createRadialGradient(breakSample.x,breakSample.y,0,breakSample.x,breakSample.y,radius);core.addColorStop(0,"rgba(255,255,255,.98)");core.addColorStop(.16,"rgba(255,221,235,.88)");core.addColorStop(.46,"rgba(255,62,130,.38)");core.addColorStop(1,"rgba(255,45,119,0)");frontContext.globalAlpha=visibility*snapPulse*.96;frontContext.fillStyle=core;frontContext.fillRect(breakSample.x-radius,breakSample.y-radius,radius*2,radius*2);} for(let i=0;i<(isMobile?5:8);i+=1){const seed=randomSeed(breakSeed*1000+i*37.1),direction=i%2===0?-1:1,tangentWeight=(.52+seed*.82)*direction,normalWeight=(seed-.5)*1.08,length=chainTitleBox.height*(.055+seed*.13)*(.52+rupturePulse*.48);frontContext.globalAlpha=visibility*rupturePulse*(.46+seed*.48);frontContext.strokeStyle=i%3===0?"rgba(255,251,253,.98)":"rgba(255,94,151,.94)";frontContext.lineWidth=.72+seed*1.08;frontContext.beginPath();frontContext.moveTo(breakSample.x,breakSample.y);frontContext.lineTo(breakSample.x+(breakSample.tangentX*tangentWeight+breakSample.normalX*normalWeight)*length,breakSample.y+(breakSample.tangentY*tangentWeight+breakSample.normalY*normalWeight)*length);frontContext.stroke();}}frontContext.restore();void timestamp;};

	const render = (timestamp: number, frame: VampireChainFrame) => {
		const fill=clamp(frame.fill),intro=clamp(frame.intro),burst=clamp(frame.burst??0);velocity=frame.velocity??0;burstVelocity=frame.burstVelocity??0;
		if(destroyed||!backContext||!frontContext)return resolveState(fill,intro);if(chainCanvasWidth<=1||chainTitleBox.width<=1)resize();
		const activation=phaseProgress(fill,.012,.11),introFade=1-phaseProgress(intro,.955,1),burstFade=1-phaseProgress(burst,.004,.045),visibility=activation*introFade*burstFade;
		for(const [canvas,context] of [[back,backContext],[front,frontContext]]){context.setTransform(1,0,0,1,0,0);context.clearRect(0,0,canvas.width,canvas.height);context.setTransform(chainPixelRatio,0,0,chainPixelRatio,0,0);} if(visibility<=.001){back.style.opacity="0";front.style.opacity="0";return resolveState(fill,intro);}
		const isMobile=mobilePerformance||chainTitleBox.width<420,releaseFade=phaseProgress(intro,.84,.985),layerRecords={back:[],front:[]},ruptureEvents=[],leaders=[];
		const colorFront=-.26+phaseProgress(fill,.1,1)*1.16+phaseProgress(intro,.02,.115)*.16,resolveHeat=(order,seed=.5)=>1-smootherstep(clamp((order-(colorFront+(seed-.5)*.1-.24))/.48));
		const edgeMarginX=Math.max(24,chainCanvasWidth*.07),edgeMarginY=Math.max(18,chainCanvasHeight*.08),edgeFade=(sample)=>smootherstep(clamp(sample.x/edgeMarginX))*smootherstep(clamp((chainCanvasWidth-sample.x)/edgeMarginX))*smootherstep(clamp(sample.y/edgeMarginY))*smootherstep(clamp((chainCanvasHeight-sample.y)/edgeMarginY));
		for(const definition of chainDefinitions){const buildStart=isMobile&&definition.type==="weave"?(definition.id===1 ? .22 : .56):definition.buildStart,buildEnd=isMobile&&definition.type==="weave"?(definition.id===1 ? .82 : 1):definition.buildEnd,build=phaseProgress(fill,buildStart,buildEnd);if(build<=.001)continue;const path=resolveTitleChainPath(definition,fill,intro),spacing=buildTitleChainLinkUnits(definition,isMobile),breakDelay=definition.id*.016,breakStart=.105+breakDelay*.58,breakOpen=easeOutCubic(clamp((intro-breakStart)/.05)),snapLinear=clamp((intro-breakStart)/.09),snapPulse=Math.sin(snapLinear*Math.PI)**.72,recoilUnit=clamp((intro-(breakStart+.018))/.19),recoil=clamp(easeOutCubic(recoilUnit)+Math.sin(recoilUnit*Math.PI)*Math.exp(-recoilUnit*1.8)*.16,0,1.08),breakDistanceUnit=spacing.distanceAtUnit(definition.breakT);let breakLinkIndex=0,nearest=Infinity;for(let i=0;i<spacing.records.length;i+=1){const d=Math.abs(spacing.records[i].distanceUnit-breakDistanceUnit);if(d<nearest){nearest=d;breakLinkIndex=i;}}
			const travel=easeOutCubic(build),travelSpan=1+definition.entryOverscan,travelOffset=definition.direction>0?travel*travelSpan-travelSpan:travelSpan-travel*travelSpan,sealMotion=resolveSealMotion(fill,intro),frameFeed=definition.type==="frame"?definition.direction*(smootherstep(phaseProgress(fill,definition.buildEnd,1))*.46+(sealMotion.takeUp*.17+sealMotion.lock*.055+sealMotion.lockKick*.018)*(1-phaseProgress(intro,.12,.17))):0,normalize=(u)=>{const w=u%1;return w<0?w+1:w;},breakTravel=definition.type==="frame"?normalize(breakDistanceUnit+frameFeed):breakDistanceUnit,breakSample=sampleTitleChainTravel(definition,path,breakTravel,spacing,fill,intro,timestamp),breakSeed=randomSeed(18001+definition.id*47.9),breakOrder=definition.direction>0?breakDistanceUnit:1-breakDistanceUnit,breakHeat=resolveHeat(breakOrder,breakSeed);ruptureEvents.push({breakSample,breakSeed,definition,heat:breakHeat,breakOpen,recoil,snapPulse,releaseFade});
			const leaderUnit=definition.direction>0?-definition.entryOverscan+travel*travelSpan:1+definition.entryOverscan-travel*travelSpan,leaderSample=sampleTitleChainTravel(definition,path,leaderUnit+frameFeed*phaseProgress(build,.84,.995),spacing,fill,intro,timestamp),leaderAlpha=visibility*phaseProgress(build,.06,.13)*(1-phaseProgress(build,.82,.99))*(1-releaseFade)*edgeFade(leaderSample);if(leaderAlpha>.002)leaders.push({definition,sample:leaderSample,alpha:leaderAlpha,heat:resolveHeat(definition.direction>0?leaderUnit:1-leaderUnit,breakSeed*.73)});
			for(let linkIndex=0;linkIndex<spacing.records.length;linkIndex+=1){const {distanceUnit}=spacing.records[linkIndex];let travelUnit=distanceUnit+travelOffset;if(definition.type==="frame"){travelUnit+=frameFeed*phaseProgress(build,.84,1);if(build>=.9995&&Math.abs(travelOffset)<=.001)travelUnit=normalize(travelUnit);}if(travelUnit<-.42||travelUnit>1.42)continue;const sample=sampleTitleChainTravel(definition,path,travelUnit,spacing,fill,intro,timestamp),outside=Math.max(0,-travelUnit,travelUnit-1),ingressFade=1-smootherstep(clamp((outside-.02)/.11));let alpha=visibility*phaseProgress(build,.02,.07)*ingressFade;if(breakOpen>.001){const side=linkIndex<=breakLinkIndex?-1:1,distanceFromBreak=Math.abs(distanceUnit-breakDistanceUnit),sideSpan=Math.max(.08,side<0?breakDistanceUnit:1-breakDistanceUnit),shatterOrder=clamp(distanceFromBreak/sideSpan),shatterSeed=randomSeed(23003+definition.id*307.1+linkIndex*43.7+(side>0?19.3:0)),shatterStart=breakStart+.008+shatterOrder*.17+shatterSeed*.014,shatterAge=clamp((intro-shatterStart)/.52);if(linkIndex===breakLinkIndex)alpha*=Math.max(0,1-breakOpen);alpha*=1-smootherstep(clamp(shatterAge/.035));}alpha*=(1-releaseFade*.96)*edgeFade(sample);const record={sample,linkIndex,definition,alpha,heat:resolveHeat(definition.direction>0?distanceUnit:1-distanceUnit,randomSeed(39019+definition.id*191.7+linkIndex*29.13)),rotationOffset:0,scale:definition.type==="frame" ? .96+sample.depth*.06 : 1,lengthScale:1,arcMode:"full"};if(sample.crossing){layerRecords.back.push({...record,arcMode:"far"});layerRecords.front.push({...record,arcMode:"near"});}else layerRecords[sample.plane].push(record);}
		}
		drawChainLayer(backContext,layerRecords.back.filter(r=>r.definition.type==="frame"),false);drawChainLayer(backContext,layerRecords.back.filter(r=>r.definition.type!=="frame"),false);drawChainLayer(frontContext,layerRecords.front.filter(r=>r.definition.type!=="frame"),true);drawChainLayer(frontContext,layerRecords.front.filter(r=>r.definition.type==="frame"),true);for(const leader of leaders)drawChainLeader(frontContext,leader);drawChainRupture(timestamp,intro,ruptureEvents,visibility,isMobile);drawContractHeartImprint(timestamp,intro,ruptureEvents,visibility,isMobile);
		back.style.opacity=Math.min(1,visibility*.88).toFixed(3);front.style.opacity=Math.min(1,visibility).toFixed(3);const state=resolveState(fill,intro);for(const canvas of[back,front]){canvas.dataset.chainProgress=fill.toFixed(3);canvas.dataset.chainIntro=intro.toFixed(3);canvas.dataset.chainState=state;canvas.dataset.chainSource="yuimi-direct-port";}root.dataset.chainSource="yuimi-direct-port";return state;
	};

	resize(true);
	return { resize, render, destroy(){destroyed=true;chainLinkUnitCache.clear();chainLinkSpriteCache.clear();clearTitleChains();} };
}
