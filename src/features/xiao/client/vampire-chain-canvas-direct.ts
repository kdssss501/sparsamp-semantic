// @ts-nocheck

/**
 * Mechanical direct port from Yuimi-chaya HomePage.astro.
 * Source ranges: 4067-4205 and 10058-12078.
 * Adaptations are limited to the host lifecycle and the measured VAMPIRE title.
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
const clamp = (value, min = 0, max = 1) => Math.min(max, Math.max(min, value));
const smoothstep = (value) => value * value * (3 - 2 * value);
const phaseProgress = (value, start, end) => smoothstep(clamp((value - start) / Math.max(0.0001, end - start), 0, 1));
const easeOutCubic = (value) => 1 - (1 - clamp(value, 0, 1)) ** 3;
const smootherstep = (value) => {
	const progress = clamp(value, 0, 1);
	const progressSquared = progress * progress;
	const progressCubed = progressSquared * progress;
	return progressCubed * (progress * (progress * 6 - 15) + 10);
};
const randomSeed = (index) => {
	const value = Math.sin(index * 12.9898 + 78.233) * 43758.5453;
	return value - Math.floor(value);
};

const resolveState = (fill, intro) => {
	if (fill <= 0.012) return "SEAL CHAINS / DORMANT";
	if (intro > 0.08) return "CONTRACT SEAL / RUPTURE";
	if (fill < 0.2) return "SEAL CHAINS / AWAKENING";
	if (fill < 0.5) return "OUTER BIND / WRAPPING";
	if (fill < 0.78) return "INNER BIND / INTERLOCKING";
	return "SEAL CORE / MAXIMUM TENSION";
};

export function mountVampireChainCanvas({ back, front, root, anchor }: ChainCanvasOptions): VampireChainCanvasController {
	const chainBackCanvas = back;
	const chainFrontCanvas = front;
	const chainBackContext = chainBackCanvas.getContext("2d", { alpha: true });
	const chainFrontContext = chainFrontCanvas.getContext("2d", { alpha: true });
	const title = anchor;
	const mobileCanvasRatio = 1.08;
	let mobilePerformance = false;
	let chainPixelRatio = 1;
	let chainCanvasWidth = 1;
	let chainCanvasHeight = 1;
	let chainTitleBox = { left: 0, top: 0, width: 1, height: 1 };
	let chainGlyphLayout = { textLeft: 0, textRight: 0, top: 0, bottom: 0, centerX: 0, centerY: 0, gaps: [], anchorBounds: [] };
	let chargeIntroProgress = 0;
	let burstProgress = 0;
	let velocity = 0;
	let burstVelocity = 0;
	let disposed = false;
	const chainLinkUnitCache = new Map();
	const chainLinkSpriteCache = new Map();

	const clearTitleChains = () => {
	  const layers = [
	    [chainBackCanvas, chainBackContext],
	    [chainFrontCanvas, chainFrontContext]
	  ];
	  for (const [canvas, context] of layers) {
	    if (!canvas || !context) continue;
	    context.setTransform(1, 0, 0, 1, 0, 0);
	    context.clearRect(0, 0, canvas.width, canvas.height);
	    context.setTransform(chainPixelRatio, 0, 0, chainPixelRatio, 0, 0);
	    canvas.style.opacity = "0";
	  }
	};

	const rebuildTitleChainLayout = () => {
	  if (!chainBackContext || !title || chainTitleBox.width <= 1) return;
	  const text = TITLE_TEXT;
	  const style = window.getComputedStyle(title);
	  const fontSize = Math.max(1, Number.parseFloat(style.fontSize));
	  chainBackContext.save();
	  chainBackContext.font = `${style.fontWeight} ${fontSize}px ${style.fontFamily}`;
	  chainBackContext.textBaseline = "alphabetic";
	  const textMetrics = chainBackContext.measureText(text);
	  const measuredWidth = Math.max(1, textMetrics.width);
	  const widthScale = chainTitleBox.width / measuredWidth;
	  const centerX = chainTitleBox.left + chainTitleBox.width * 0.5;
	  const textLeft = centerX - measuredWidth * widthScale * 0.5;
	  const measuredAscent = Number.isFinite(textMetrics.actualBoundingBoxAscent)
	    && textMetrics.actualBoundingBoxAscent > 0
	    ? textMetrics.actualBoundingBoxAscent
	    : fontSize * 0.72;
	  const measuredDescent = Number.isFinite(textMetrics.actualBoundingBoxDescent)
	    && textMetrics.actualBoundingBoxDescent >= 0
	    ? textMetrics.actualBoundingBoxDescent
	    : fontSize * 0.06;
	  const top = chainTitleBox.top + chainTitleBox.height * 0.08;
	  const bottom = chainTitleBox.top + chainTitleBox.height * 0.92;
	  const heightScale = (bottom - top) / Math.max(1, measuredAscent + measuredDescent);
	  const baseline = top + measuredAscent * heightScale;
	  const gaps = [];
	  const glyphBounds = [];
	  let prefixWidth = 0;
	  for (let index = 0; index < text.length; index += 1) {
	    const nextPrefixWidth = chainBackContext.measureText(text.slice(0, index + 1)).width;
	    const glyphMetrics = chainBackContext.measureText(text[index]);
	    const glyphAscent = Number.isFinite(glyphMetrics.actualBoundingBoxAscent)
	      && glyphMetrics.actualBoundingBoxAscent > 0
	      ? glyphMetrics.actualBoundingBoxAscent
	      : measuredAscent;
	    const glyphDescent = Number.isFinite(glyphMetrics.actualBoundingBoxDescent)
	      && glyphMetrics.actualBoundingBoxDescent >= 0
	      ? glyphMetrics.actualBoundingBoxDescent
	      : measuredDescent;
	    glyphBounds.push({
	      left: textLeft + prefixWidth * widthScale,
	      right: textLeft + nextPrefixWidth * widthScale,
	      top: baseline - glyphAscent * heightScale,
	      bottom: baseline + glyphDescent * heightScale
	    });
	    if (index < text.length - 1) {
	      gaps.push(textLeft + nextPrefixWidth * widthScale);
	    }
	    prefixWidth = nextPrefixWidth;
	  }
	  chainBackContext.restore();
	  const anchorBounds = Array.from({ length: text.length + 1 }, (_, index) => {
	    if (index === 0) {
	      return { top: glyphBounds[0].top, bottom: glyphBounds[0].bottom };
	    }
	    if (index === text.length) {
	      const glyph = glyphBounds[glyphBounds.length - 1];
	      return { top: glyph.top, bottom: glyph.bottom };
	    }
	    const leftGlyph = glyphBounds[index - 1];
	    const rightGlyph = glyphBounds[index];
	    return {
	      top: (leftGlyph.top + rightGlyph.top) * 0.5,
	      bottom: (leftGlyph.bottom + rightGlyph.bottom) * 0.5
	    };
	  });
	  chainGlyphLayout = {
	    textLeft,
	    textRight: textLeft + measuredWidth * widthScale,
	    top,
	    bottom,
	    centerX,
	    centerY: chainTitleBox.top + chainTitleBox.height * 0.52,
	    gaps,
	    anchorBounds
	  };
	};

	const resizeTitleChains = (force = false) => {
	  if (
	    !chainBackCanvas
	    || !chainBackContext
	    || !chainFrontCanvas
	    || !chainFrontContext
	    || !title
	  ) return;
	  const canvasRect = chainBackCanvas.getBoundingClientRect();
	  const titleRect = title.getBoundingClientRect();
	  const width = Math.max(1, canvasRect.width);
	  const height = Math.max(1, canvasRect.height);
	  const deviceScale = Math.min(
	    window.devicePixelRatio || 1,
	    mobilePerformance ? mobileCanvasRatio : width < 640 ? 1.12 : 1.28
	  );
	  const pixelRatio = Math.min(deviceScale, 1660 / width, 560 / height);
	  const pixelWidth = Math.max(1, Math.round(width * pixelRatio));
	  const pixelHeight = Math.max(1, Math.round(height * pixelRatio));
	  const changed = force
	    || Math.abs(chainCanvasWidth - width) > 0.5
	    || Math.abs(chainCanvasHeight - height) > 0.5
	    || Math.abs(chainPixelRatio - pixelRatio) > 0.01
	    || chainBackCanvas.width !== pixelWidth
	    || chainBackCanvas.height !== pixelHeight
	    || chainFrontCanvas.width !== pixelWidth
	    || chainFrontCanvas.height !== pixelHeight;
	  chainTitleBox = {
	    left: titleRect.left - canvasRect.left,
	    top: titleRect.top - canvasRect.top,
	    width: titleRect.width,
	    height: titleRect.height
	  };
	  if (changed) {
	    chainBackCanvas.width = pixelWidth;
	    chainBackCanvas.height = pixelHeight;
	    chainFrontCanvas.width = pixelWidth;
	    chainFrontCanvas.height = pixelHeight;
	    chainCanvasWidth = width;
	    chainCanvasHeight = height;
	    chainPixelRatio = pixelRatio;
	    chainLinkUnitCache.clear();
	    chainLinkSpriteCache.clear();
	    clearTitleChains();
	  }
	  rebuildTitleChainLayout();
	};

	const chainDefinitions = [
	  {
	    id: 0,
	    type: "frame",
	    buildStart: 0.025,
	    buildEnd: 0.54,
	    direction: 1,
	    phase: -1.92,
	    radiusX: 0.445,
	    radiusY: 0.13,
	    rotation: -0.02,
	    breakT: 0.18,
	    desktopLinks: 52,
	    mobileLinks: 20,
	    linkScale: 0.98,
	    entryOverscan: 0.16,
	    entryBend: -0.06
	  },
	  {
	    id: 1,
	    type: "weave",
	    buildStart: 0.1,
	    buildEnd: 0.76,
	    direction: 1,
	    verticalPhase: 0,
	    planePhase: 0,
	    topInset: 0.02,
	    bottomInset: 0.02,
	    xInset: 0.075,
	    xShift: -0.006,
	    breakT: 0.5,
	    desktopLinksPerSegment: 8,
	    mobileLinksPerSegment: 3,
	    linkScale: 0.96,
	    entryOverscan: 0.14,
	    entryBend: 0.09
	  },
	  {
	    id: 2,
	    type: "weave",
	    buildStart: 0.38,
	    buildEnd: 0.97,
	    direction: -1,
	    verticalPhase: 1,
	    planePhase: 1,
	    topInset: 0.2,
	    bottomInset: 0.18,
	    xInset: 0.055,
	    xShift: 0.008,
	    breakT: 0.44,
	    desktopLinksPerSegment: 7,
	    mobileLinksPerSegment: 3,
	    linkScale: 0.82,
	    entryOverscan: 0.14,
	    entryBend: -0.08
	  }
	];

	const catmullCoordinate = (point0, point1, point2, point3, unit) => {
	  const unit2 = unit * unit;
	  const unit3 = unit2 * unit;
	  return 0.5 * (
	    2 * point1
	    + (-point0 + point2) * unit
	    + (2 * point0 - 5 * point1 + 4 * point2 - point3) * unit2
	    + (-point0 + 3 * point1 - 3 * point2 + point3) * unit3
	  );
	};

	const catmullTangent = (point0, point1, point2, point3, unit) => {
	  const unit2 = unit * unit;
	  return 0.5 * (
	    -point0 + point2
	    + 2 * (2 * point0 - 5 * point1 + 4 * point2 - point3) * unit
	    + 3 * (-point0 + 3 * point1 - 3 * point2 + point3) * unit2
	  );
	};

	const resolveSealMotion = (fill, intro) => {
	  const scrollTension = phaseProgress(fill, 0.48, 1);
	  const settle = phaseProgress(intro, 0, 0.018);
	  const takeUp = easeOutCubic(clamp(intro / 0.075, 0, 1));
	  const lockUnit = clamp((intro - 0.022) / 0.065, 0, 1);
	  const lock = easeOutCubic(lockUnit);
	  const lockKick = Math.sin(lockUnit * Math.PI) * Math.exp(-lockUnit * 1.2);
	  const strain = Math.sin(phaseProgress(intro, 0.012, 0.15) * Math.PI);
	  const weavePull = scrollTension * 0.009
	    + takeUp * 0.038
	    + lock * 0.018
	    + lockKick * 0.006;
	  return { scrollTension, settle, takeUp, lock, lockKick, strain, weavePull };
	};

	const resolveTitleChainPath = (definition, fill, intro) => {
	  if (definition.type === "frame") return { type: "frame", segmentCount: 4 };
	  const box = chainTitleBox;
	  const layout = chainGlyphLayout;
	  const fallbackGaps = [0.14, 0.285, 0.43, 0.57, 0.715, 0.86]
	    .map((unit) => box.left + box.width * unit);
	  const gaps = layout.gaps.length === TITLE_TEXT.length - 1 ? layout.gaps : fallbackGaps;
	  const textLeft = layout.textRight > layout.textLeft
	    ? layout.textLeft
	    : box.left;
	  const textRight = layout.textRight > layout.textLeft
	    ? layout.textRight
	    : box.left + box.width;
	  const centerX = layout.centerX || box.left + box.width * 0.5;
	  const centerY = layout.centerY || box.top + box.height * 0.52;
	  const fallbackTop = layout.bottom > layout.top ? layout.top : box.top;
	  const fallbackBottom = layout.bottom > layout.top
	    ? layout.bottom
	    : box.top + box.height;
	  const xShift = box.width * definition.xShift;
	  const anchorXs = [
	    textLeft - box.width * definition.xInset,
	    ...gaps.map((gap) => gap + xShift),
	    textRight + box.width * definition.xInset
	  ];
	  const anchorBounds = layout.anchorBounds.length === anchorXs.length
	    ? layout.anchorBounds
	    : anchorXs.map(() => ({ top: fallbackTop, bottom: fallbackBottom }));
	  const sealMotion = resolveSealMotion(fill, intro);
	  const { takeUp, lock, lockKick } = sealMotion;
	  const pull = sealMotion.weavePull;
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
	    const y = upper
	      ? top + localHeight * endpointEase
	      : bottom - localHeight * endpointEase;
	    const pointUnit = index / pointSpan;
	    const windingWave = 0.5 + 0.5 * Math.cos(
	      pointUnit * fullTurn * 1.55
	        + definition.verticalPhase * Math.PI
	        - takeUp * fullTurn * 0.42
	    );
	    const localPull = pull * (0.58 + windingWave * 0.62);
	    const localTwist = definition.direction
	      * (takeUp * 0.105 + lock * 0.044 + lockKick * 0.012)
	      * (0.42 + windingWave * 0.58);
	    const offsetX = x - centerX;
	    const offsetY = y - centerY;
	    const tightenedX = offsetX * (1 - localPull);
	    const tightenedY = offsetY * (1 - localPull);
	    const twistCosine = Math.cos(localTwist);
	    const twistSine = Math.sin(localTwist);
	    return {
	      x: centerX + tightenedX * twistCosine - tightenedY * twistSine,
	      y: centerY + tightenedX * twistSine + tightenedY * twistCosine
	    };
	  });
	  return {
	    type: "weave",
	    points,
	    segmentCount: Math.max(1, points.length - 1)
	  };
	};

	const sampleTitleChain = (definition, path, unit, fill, intro, timestamp) => {
	  const box = chainTitleBox;
	  const centerX = chainGlyphLayout.centerX || box.left + box.width * 0.5;
	  const centerY = chainGlyphLayout.centerY || box.top + box.height * 0.52;
	  const sealMotion = resolveSealMotion(fill, intro);
	  const { scrollTension, settle, takeUp, lock, lockKick, strain } = sealMotion;
	  const frameMotionResponse = definition.type === "frame"
	    ? clamp(
	        Math.abs(velocity) * 320
	          + Math.abs(burstVelocity) * 220
	          + phaseProgress(intro, 0, 0.018),
	        0,
	        1
	      )
	    : 1;
	  const chainOrder = definition.direction > 0 ? unit : 1 - unit;
	  const localTakeUp = smootherstep(clamp((takeUp - 0.018) / 0.982, 0, 1));
	  let x = centerX;
	  let y = centerY;
	  let tangentX = 1;
	  let tangentY = 0;
	  let plane = "back";
	  let crossing = false;
	  let depth = 0;

	  if (definition.type === "frame") {
	    const layout = chainGlyphLayout;
	    const mobileGeometry = mobilePerformance || box.width < 420;
	    const glyphWidth = layout.textRight > layout.textLeft
	      ? layout.textRight - layout.textLeft
	      : box.width;
	    const glyphHeight = layout.bottom > layout.top
	      ? layout.bottom - layout.top
	      : box.height * 0.84;
	    const frameCenterX = layout.centerX || centerX;
	    const frameCenterY = layout.centerY || centerY;
	    const radiusX = glyphWidth * definition.radiusX
	      * (mobileGeometry ? 1.04 : 1)
	      * (1 - scrollTension * 0.004);
	    const radiusY = glyphHeight * definition.radiusY
	      * (mobileGeometry ? 2.6 : 1)
	      * (1 - scrollTension * 0.006);
	    const angle = definition.phase + definition.direction * unit * fullTurn;
	    const rotationCosine = Math.cos(definition.rotation);
	    const rotationSine = Math.sin(definition.rotation);
	    const frameExponent = 0.68;
	    const framePoint = (sampleAngle) => {
	      const sampleCosine = Math.cos(sampleAngle);
	      const sampleSine = Math.sin(sampleAngle);
	      const cinchWave = 0.5 + 0.5 * Math.cos(
	        (sampleAngle - definition.phase) * 2.05
	          - takeUp * fullTurn * 1.08
	          + lock * 1.4
	      );
	      const localCinch = takeUp * (0.022 + cinchWave * 0.058)
	        + lock * (0.018 + (1 - cinchWave) * 0.038)
	        + lockKick * cinchWave * 0.016;
	      const frameX = Math.sign(sampleCosine) * Math.abs(sampleCosine) ** frameExponent;
	      const frameY = Math.sign(sampleSine) * Math.abs(sampleSine) ** frameExponent;
	      const perspectiveWidth = 0.965 + sampleSine * 0.035;
	      const localX = frameX * radiusX * perspectiveWidth * (1 - localCinch);
	      const localY = frameY * radiusY * (1 - localCinch * 1.12);
	      return {
	        x: frameCenterX + localX * rotationCosine - localY * rotationSine,
	        y: frameCenterY + localX * rotationSine + localY * rotationCosine
	      };
	    };
	    const point = framePoint(angle);
	    const tangentPoint = framePoint(angle + definition.direction * 0.0025);
	    x = point.x;
	    y = point.y;
	    tangentX = tangentPoint.x - x;
	    tangentY = tangentPoint.y - y;
	    const slackBlend = clamp(
	      scrollTension * 0.2 + settle * 0.14 + localTakeUp * 0.72 + lock * 0.16,
	      0,
	      1
	    );
	    const slackAmplitude = 0.008 + (0.0015 - 0.008) * slackBlend;
	    const wobble = Math.sin(
	      angle * 2.35
	        + timestamp * 0.00038
	        + definition.id * 1.37
	    ) * box.height * slackAmplitude * frameMotionResponse;
	    const tangentLength = Math.max(0.001, Math.hypot(tangentX, tangentY));
	    x += -tangentY / tangentLength * wobble;
	    y += tangentX / tangentLength * wobble;
	    depth = clamp((y - centerY) / Math.max(1, radiusY * 1.04), -1, 1);
	    plane = depth >= 0 ? "front" : "back";
	    const frameJoinDepth = clamp(
	      getChainLinkDimensions(definition).height / Math.max(1, radiusY * 5.4),
	      0.1,
	      0.2
	    );
	    crossing = Math.abs(depth) <= frameJoinDepth;
	  } else {
	    const reelStrength = takeUp * 0.1
	      + lock * 0.042
	      + lockKick * 0.014;
	    const reelWave = 0.64 + 0.36 * Math.cos(
	      (unit - definition.breakT) * fullTurn * 1.38
	        - takeUp * Math.PI * 1.55
	        + definition.id * 0.73
	    );
	    const reeledUnit = clamp(
	      unit + (definition.breakT - unit) * reelStrength * reelWave,
	      0,
	      1
	    );
	    const segmentPosition = reeledUnit * path.segmentCount;
	    const segmentIndex = Math.min(
	      path.segmentCount - 1,
	      Math.floor(Math.min(segmentPosition, path.segmentCount - 0.000001))
	    );
	    const localUnit = clamp(segmentPosition - segmentIndex, 0, 1);
	    const point0 = path.points[Math.max(0, segmentIndex - 1)];
	    const point1 = path.points[segmentIndex];
	    const point2 = path.points[Math.min(path.points.length - 1, segmentIndex + 1)];
	    const point3 = path.points[Math.min(path.points.length - 1, segmentIndex + 2)];
	    x = catmullCoordinate(point0.x, point1.x, point2.x, point3.x, localUnit);
	    y = catmullCoordinate(point0.y, point1.y, point2.y, point3.y, localUnit);
	    tangentX = catmullTangent(point0.x, point1.x, point2.x, point3.x, localUnit);
	    tangentY = catmullTangent(point0.y, point1.y, point2.y, point3.y, localUnit);
	    plane = (segmentIndex + definition.planePhase) % 2 === 0 ? "front" : "back";
	    const nearestBoundary = Math.round(segmentPosition);
	    crossing = nearestBoundary > 0
	      && nearestBoundary < path.segmentCount
	      && Math.abs(segmentPosition - nearestBoundary) < 0.045;
	  }

	  const tangentLength = Math.max(0.001, Math.hypot(tangentX, tangentY));
	  tangentX /= tangentLength;
	  tangentY /= tangentLength;
	  const normalX = -tangentY;
	  const normalY = tangentX;
	  const tensionWave = Math.sin(
	    timestamp * (0.0008 + strain * 0.0032)
	      + unit * fullTurn * (2.1 + definition.id * 0.16)
	      + definition.id * 1.73
	  );
	  const residualSlack = 1 - clamp(
	    settle * 0.14 + localTakeUp * 0.72 + lock * 0.16,
	    0,
	    1
	  );
	  const tensionOffset = tensionWave
	    * box.height
	    * (0.0014 + residualSlack * 0.0036 + strain * 0.0042)
	    * frameMotionResponse;
	  x += normalX * tensionOffset;
	  y += normalY * tensionOffset;
	  return {
	    x,
	    y,
	    tangentX,
	    tangentY,
	    normalX,
	    normalY,
	    angle: Math.atan2(tangentY, tangentX),
	    plane,
	    crossing,
	    depth
	  };
	};

	const sampleTitleChainTravel = (
	  definition,
	  path,
	  distanceUnit,
	  spacing,
	  fill,
	  intro,
	  timestamp
	) => {
	  if (distanceUnit >= 0 && distanceUnit <= 1) {
	    return sampleTitleChain(
	      definition,
	      path,
	      spacing.unitAtDistance(distanceUnit),
	      fill,
	      intro,
	      timestamp
	    );
	  }
	  const boundaryUnit = distanceUnit < 0 ? 0 : 1;
	  const boundary = sampleTitleChain(
	    definition,
	    path,
	    boundaryUnit,
	    fill,
	    intro,
	    timestamp
	  );
	  const outsideDistance = Math.abs(distanceUnit - boundaryUnit) * spacing.totalLength;
	  const direction = distanceUnit < 0 ? -1 : 1;
	  const bend = Math.sin(
	    clamp(outsideDistance / Math.max(1, chainTitleBox.height * 2.4), 0, 1) * Math.PI
	  )
	    * chainTitleBox.height
	    * definition.entryBend;
	  return {
	    ...boundary,
	    x: boundary.x
	      + boundary.tangentX * direction * outsideDistance
	      + boundary.normalX * bend,
	    y: boundary.y
	      + boundary.tangentY * direction * outsideDistance
	      + boundary.normalY * bend,
	    plane: "back",
	    crossing: false
	  };
	};

	const getChainLinkDimensions = (definition) => {
	  const mobileGeometry = mobilePerformance || chainTitleBox.width < 420;
	  const linkUnit = clamp(
	    chainTitleBox.height * (mobileGeometry ? 0.122 : 0.108),
	    mobileGeometry ? 9.2 : 8.4,
	    mobileGeometry ? 15.8 : 16.8
	  ) * definition.linkScale;
	  return {
	    width: linkUnit * 1.82,
	    height: linkUnit * 1.02
	  };
	};

	const buildTitleChainLinkUnits = (definition, isMobile) => {
	  const cacheKey = [
	    definition.id,
	    Math.round(chainTitleBox.width),
	    Math.round(chainTitleBox.height),
	    isMobile ? 1 : 0
	  ].join(":");
	  const cached = chainLinkUnitCache.get(cacheKey);
	  if (cached) return cached;
	  const spacingPath = resolveTitleChainPath(definition, 0, 0);
	  const sampleCount = definition.type === "frame"
	    ? (isMobile ? 110 : 180)
	    : (isMobile ? 88 : 140);
	  const samples = [];
	  let totalLength = 0;
	  let previous = sampleTitleChain(definition, spacingPath, 0, 0, 0, 0);
	  samples.push({ unit: 0, length: 0 });
	  for (let index = 1; index <= sampleCount; index += 1) {
	    const unit = index / sampleCount;
	    const current = sampleTitleChain(definition, spacingPath, unit, 0, 0, 0);
	    totalLength += Math.hypot(current.x - previous.x, current.y - previous.y);
	    samples.push({ unit, length: totalLength });
	    previous = current;
	  }
	  if (totalLength <= 0.001) {
	    return {
	      records: [{ unit: 0, distanceUnit: 0 }],
	      totalLength: 1,
	      unitAtDistance: () => 0,
	      distanceAtUnit: () => 0
	    };
	  }

	  const dimensions = getChainLinkDimensions(definition);
	  const spacingFactor = definition.type === "frame"
	    ? (isMobile ? 1.04 : 0.64)
	    : (isMobile ? 0.98 : 0.6);
	  const desiredCount = Math.round(totalLength / (dimensions.width * spacingFactor));
	  const minimum = definition.type === "frame"
	    ? (isMobile ? definition.mobileLinks : definition.desktopLinks)
	    : (isMobile
	        ? definition.mobileLinksPerSegment
	        : definition.desktopLinksPerSegment) * spacingPath.segmentCount + 1;
	  const maximum = definition.type === "frame"
	    ? (isMobile ? 28 : 110)
	    : (isMobile ? 22 : 86);
	  let linkCount = Math.round(clamp(desiredCount, minimum, maximum));
	  if (definition.type === "frame" && linkCount % 2 !== 0) {
	    linkCount += linkCount < maximum ? 1 : -1;
	  }
	  const unitAtLength = (targetLength) => {
	    let low = 1;
	    let high = samples.length - 1;
	    while (low < high) {
	      const middle = Math.floor((low + high) * 0.5);
	      if (samples[middle].length < targetLength) low = middle + 1;
	      else high = middle;
	    }
	    const upper = samples[low];
	    const lower = samples[Math.max(0, low - 1)];
	    const span = Math.max(0.0001, upper.length - lower.length);
	    const blend = clamp((targetLength - lower.length) / span, 0, 1);
	    return lower.unit + (upper.unit - lower.unit) * blend;
	  };
	  const lengthAtUnit = (targetUnit) => {
	    const samplePosition = clamp(targetUnit, 0, 1) * sampleCount;
	    const lowerIndex = Math.floor(samplePosition);
	    const upperIndex = Math.min(samples.length - 1, lowerIndex + 1);
	    const blend = samplePosition - lowerIndex;
	    return samples[lowerIndex].length
	      + (samples[upperIndex].length - samples[lowerIndex].length) * blend;
	  };
	  const records = [];
	  for (let index = 0; index < linkCount; index += 1) {
	    const distanceUnit = definition.type === "frame"
	      ? (index + 0.5) / linkCount
	      : index / Math.max(1, linkCount - 1);
	    records.push({
	      distanceUnit,
	      unit: unitAtLength(distanceUnit * totalLength)
	    });
	  }
	  if (definition.type === "weave") {
	    for (let boundary = 1; boundary < spacingPath.segmentCount; boundary += 1) {
	      const boundaryUnit = boundary / spacingPath.segmentCount;
	      const boundaryDistanceUnit = lengthAtUnit(boundaryUnit) / totalLength;
	      let nearestIndex = 0;
	      let nearestDistance = Infinity;
	      for (let index = 0; index < records.length; index += 1) {
	        const distance = Math.abs(records[index].distanceUnit - boundaryDistanceUnit);
	        if (distance < nearestDistance) {
	          nearestDistance = distance;
	          nearestIndex = index;
	        }
	      }
	      records[nearestIndex] = {
	        distanceUnit: boundaryDistanceUnit,
	        unit: boundaryUnit
	      };
	    }
	    records.sort((left, right) => left.distanceUnit - right.distanceUnit);
	  }
	  const spacing = {
	    records,
	    totalLength,
	    unitAtDistance: (distanceUnit) => unitAtLength(clamp(distanceUnit, 0, 1) * totalLength),
	    distanceAtUnit: (unit) => lengthAtUnit(clamp(unit, 0, 1)) / totalLength
	  };
	  chainLinkUnitCache.set(cacheKey, spacing);
	  if (chainLinkUnitCache.size > 24) {
	    chainLinkUnitCache.delete(chainLinkUnitCache.keys().next().value);
	  }
	  return spacing;
	};

	const getChainLinkSprite = (definition, isFront, arcPart, hot, parity, variant) => {
	  const dimensions = getChainLinkDimensions(definition);
	  const cacheKey = [
	    definition.id,
	    Math.round(dimensions.width * 10),
	    Math.round(dimensions.height * 10),
	    isFront ? 1 : 0,
	    arcPart,
	    hot ? 1 : 0,
	    parity,
	    variant
	  ].join(":");
	  const cached = chainLinkSpriteCache.get(cacheKey);
	  if (cached) return cached;
	  const simplifiedChain = mobilePerformance || chainTitleBox.width < 420;
	  const spriteScale = simplifiedChain ? 1.55 : 2.4;
	  const padding = simplifiedChain ? (isFront ? 8 : 7) : (isFront ? 12 : 10);
	  const width = dimensions.width + padding * 2;
	  const height = dimensions.height + padding * 2;
	  const canvas = document.createElement("canvas");
	  canvas.width = Math.max(1, Math.ceil(width * spriteScale));
	  canvas.height = Math.max(1, Math.ceil(height * spriteScale));
	  const context = canvas.getContext("2d", { alpha: true });
	  if (!context) return null;
	  context.setTransform(spriteScale, 0, 0, spriteScale, width * spriteScale * 0.5, height * spriteScale * 0.5);
	  context.lineCap = "round";
	  context.lineJoin = "round";
	  const detailedMetal = !simplifiedChain && isFront && arcPart === "near";
	  const variantUnit = variant / 2;
	  const toneShift = variantUnit - 0.5;
	  const nearUsesLowerArc = parity === 0;
	  const lowerArc = [-Math.PI * 0.08, Math.PI * 1.08];
	  const upperArc = [Math.PI * 0.92, Math.PI * 2.08];
	  const [arcStart, arcEnd] = arcPart === "full"
	    ? [0, fullTurn]
	    : arcPart === "near"
	      ? (nearUsesLowerArc ? lowerArc : upperArc)
	      : (nearUsesLowerArc ? upperArc : lowerArc);
	  const prominentArc = arcPart !== "far";
	  const metal = context.createLinearGradient(
	    0,
	    -dimensions.height * 0.62,
	    0,
	    dimensions.height * 0.62
	  );
	  if (hot) {
	    metal.addColorStop(0, `hsla(${337 + toneShift * 5}, 28%, ${6 + variantUnit * 1.5}%, 0.99)`);
	    metal.addColorStop(0.13, `hsla(${342 + toneShift * 6}, 28%, ${16 + variantUnit * 3}%, 0.99)`);
	    metal.addColorStop(0.27, `hsla(${350 + toneShift * 4}, 22%, ${63 + variantUnit * 5}%, 0.99)`);
	    metal.addColorStop(0.39, `hsla(${344 + toneShift * 5}, 46%, ${29 + variantUnit * 4}%, 0.99)`);
	    metal.addColorStop(0.58, `hsla(${336 + toneShift * 4}, 32%, ${9 + variantUnit * 2}%, 0.99)`);
	    metal.addColorStop(0.76, `hsla(${349 + toneShift * 5}, 48%, ${34 + variantUnit * 5}%, 0.99)`);
	    metal.addColorStop(0.9, `hsla(${339 + toneShift * 4}, 30%, ${14 + variantUnit * 3}%, 0.99)`);
	    metal.addColorStop(1, `hsla(${354 + toneShift * 4}, 38%, ${54 + variantUnit * 6}%, 0.98)`);
	  } else {
	    metal.addColorStop(0, `hsla(${220 + toneShift * 5}, 28%, ${5 + variantUnit * 1.5}%, 0.99)`);
	    metal.addColorStop(0.12, `hsla(${218 + toneShift * 6}, 24%, ${17 + variantUnit * 3}%, 0.99)`);
	    metal.addColorStop(0.25, `hsla(${215 + toneShift * 4}, 14%, ${73 + variantUnit * 5}%, 0.99)`);
	    metal.addColorStop(0.37, `hsla(${217 + toneShift * 5}, 22%, ${35 + variantUnit * 5}%, 0.99)`);
	    metal.addColorStop(0.58, `hsla(${221 + toneShift * 5}, 28%, ${9 + variantUnit * 2}%, 0.99)`);
	    metal.addColorStop(0.76, `hsla(${214 + toneShift * 5}, 20%, ${42 + variantUnit * 6}%, 0.99)`);
	    metal.addColorStop(0.9, `hsla(${222 + toneShift * 4}, 24%, ${14 + variantUnit * 3}%, 0.99)`);
	    metal.addColorStop(1, `hsla(${212 + toneShift * 4}, 14%, ${64 + variantUnit * 7}%, 0.98)`);
	  }

	  context.globalAlpha = prominentArc ? 0.96 : 0.72;
	  context.strokeStyle = "rgba(3,4,13,0.98)";
	  context.lineWidth = (isFront ? 5.7 : 5.05) * (0.95 + variantUnit * 0.08);
	  context.shadowColor = "rgba(1,2,11,0.9)";
	  context.shadowBlur = detailedMetal ? 2.8 + variantUnit * 0.8 : 0;
	  context.beginPath();
	  context.ellipse(0, 0, dimensions.width * 0.5, dimensions.height * 0.5, 0, arcStart, arcEnd);
	  context.stroke();

	  context.globalAlpha = prominentArc ? 1 : 0.8;
	  context.strokeStyle = metal;
	  context.lineWidth = (isFront ? 3.45 : 3) * (0.96 + variantUnit * 0.07);
	  context.shadowColor = hot ? "rgba(255,76,122,0.24)" : "rgba(124,157,211,0.15)";
	  context.shadowBlur = detailedMetal ? (hot ? 2.4 : 1.65) + variantUnit * 0.45 : 0;
	  context.beginPath();
	  context.ellipse(0, 0, dimensions.width * 0.5, dimensions.height * 0.5, 0, arcStart, arcEnd);
	  context.stroke();

	  context.globalCompositeOperation = "multiply";
	  context.globalAlpha = prominentArc ? 0.74 : 0.52;
	  context.strokeStyle = hot ? "rgba(41,3,18,0.92)" : "rgba(5,10,24,0.9)";
	  context.lineWidth = 0.94 + variantUnit * 0.18;
	  context.shadowBlur = 0;
	  context.beginPath();
	  context.ellipse(
	    0,
	    dimensions.height * 0.045,
	    dimensions.width * 0.455,
	    dimensions.height * 0.415,
	    0,
	    arcStart + Math.PI * 0.08,
	    arcEnd - Math.PI * 0.08
	  );
	  context.stroke();

	  if (detailedMetal) {
	    context.globalCompositeOperation = "screen";
	    context.globalAlpha = hot ? 0.58 + variantUnit * 0.08 : 0.46 + variantUnit * 0.08;
	    context.strokeStyle = hot ? "rgba(255,224,232,0.9)" : "rgba(226,235,248,0.9)";
	    context.lineWidth = 0.66 + variantUnit * 0.12;
	    context.shadowColor = hot ? "rgba(255,133,159,0.38)" : "rgba(157,183,224,0.26)";
	    context.shadowBlur = 0.8 + variantUnit * 0.35;
	    context.beginPath();
	    context.ellipse(
	      0,
	      -dimensions.height * 0.04,
	      dimensions.width * 0.438,
	      dimensions.height * 0.39,
	      0,
	      arcStart + (arcEnd - arcStart) * (0.11 + variantUnit * 0.035),
	      arcStart + (arcEnd - arcStart) * (0.5 + variantUnit * 0.1)
	    );
	    context.stroke();

	    context.globalAlpha = hot ? 0.28 + variantUnit * 0.08 : 0.22 + variantUnit * 0.07;
	    context.lineWidth = 0.48 + variantUnit * 0.12;
	    context.beginPath();
	    context.ellipse(
	      0,
	      -dimensions.height * 0.02,
	      dimensions.width * 0.438,
	      dimensions.height * 0.39,
	      0,
	      arcStart + (arcEnd - arcStart) * 0.72,
	      arcStart + (arcEnd - arcStart) * 0.88
	    );
	    context.stroke();

	    context.globalCompositeOperation = "source-over";
	    context.shadowBlur = 0;
	    const wearCount = 2 + variant;
	    for (let wearIndex = 0; wearIndex < wearCount; wearIndex += 1) {
	      const wearUnit = 0.2
	        + wearIndex * (0.58 / Math.max(1, wearCount - 1))
	        + parity * 0.022
	        + toneShift * 0.018;
	      const wearAngle = arcStart + (arcEnd - arcStart) * wearUnit;
	      const wearX = Math.cos(wearAngle) * dimensions.width * 0.47;
	      const wearY = Math.sin(wearAngle) * dimensions.height * 0.45;
	      const tangentX = -Math.sin(wearAngle);
	      const tangentY = Math.cos(wearAngle);
	      const wearLength = 0.7 + wearIndex * 0.27 + variantUnit * 0.24;
	      context.globalAlpha = hot ? 0.28 + variantUnit * 0.06 : 0.23 + variantUnit * 0.05;
	      context.strokeStyle = "rgba(4,5,14,0.96)";
	      context.lineWidth = 0.5 + variantUnit * 0.13;
	      context.beginPath();
	      context.moveTo(
	        wearX - tangentX * wearLength,
	        wearY - tangentY * wearLength
	      );
	      context.lineTo(
	        wearX + tangentX * wearLength,
	        wearY + tangentY * wearLength
	      );
	      context.stroke();
	    }
	  }
	  const sprite = { canvas, width, height };
	  chainLinkSpriteCache.set(cacheKey, sprite);
	  return sprite;
	};

	const drawChainLinkArc = (
	  context,
	  sample,
	  linkIndex,
	  definition,
	  alpha,
	  heat,
	  isFront,
	  arcPart,
	  rotationOffset = 0,
	  scale = 1,
	  lengthScale = 1
	) => {
	  if (alpha <= 0.002) return;
	  const simplifiedChain = mobilePerformance || chainTitleBox.width < 420;
	  const parity = linkIndex % 2;
	  const edgeOn = parity === 1;
	  const frameDepth = Number.isFinite(sample.depth) ? sample.depth : 0;
	  const layerAlpha = alpha * (definition.type === "frame"
	    ? (isFront
	        ? 0.82 + Math.max(0, frameDepth) * 0.18
	        : 0.78 + Math.max(0, -frameDepth) * 0.16)
	    : (isFront ? 1 : 0.66));
	  const variantSeed = randomSeed(
	    41011 + definition.id * 701.3 + linkIndex * 43.17 + parity * 17.9
	  );
	  const shapeSeed = randomSeed(
	    52021 + definition.id * 389.7 + linkIndex * 71.11
	  );
	  const variant = Math.min(2, Math.floor(variantSeed * 3));
	  const heatBias = (variantSeed - 0.5) * 0.1;
	  const heatBlend = smootherstep(clamp((heat - heatBias) / 0.96, 0, 1));
	  const heatCap = clamp(
	    (isFront ? 0.84 : 0.78) + variant * 0.03,
	    0,
	    0.92
	  );
	  const resolvedHeat = heatBlend * heatCap;
	  const frameLink = definition.type === "frame";
	  const sizeVariation = frameLink
	    ? 0.97 + shapeSeed * 0.06
	    : 0.92 + shapeSeed * 0.15;
	  const aspectVariation = frameLink
	    ? 0.98 + variantSeed * 0.04
	    : 0.94 + variantSeed * 0.12;
	  const connectorReach = edgeOn
	    ? (frameLink ? lengthScale : 1.08)
	    : 1;
	  const horizontalScale = scale * sizeVariation * aspectVariation * connectorReach;
	  const verticalProfile = edgeOn
	    ? 0.37 + (variantSeed - 0.5) * 0.03
	    : 1.02;
	  const verticalScale = scale * sizeVariation * verticalProfile / aspectVariation;
	  const coldSprite = resolvedHeat < 0.985
	    ? getChainLinkSprite(definition, isFront, arcPart, false, parity, variant)
	    : null;
	  const hotSprite = resolvedHeat > 0.015
	    ? getChainLinkSprite(definition, isFront, arcPart, true, parity, variant)
	    : null;
	  context.save();
	  context.translate(sample.x, sample.y);
	  context.rotate(
	    sample.angle
	      + (edgeOn ? 0.045 : -0.035)
	      + (variantSeed - 0.5) * (frameLink ? 0.03 : 0.085)
	      + rotationOffset
	  );
	  context.scale(horizontalScale, verticalScale);
	  context.imageSmoothingEnabled = true;
	  if (edgeOn && !simplifiedChain) {
	    const dimensions = getChainLinkDimensions(definition);
	    const nearUsesLowerArc = parity === 0;
	    const lowerArc = [-Math.PI * 0.08, Math.PI * 1.08];
	    const upperArc = [Math.PI * 0.92, Math.PI * 2.08];
	    const [arcStart, arcEnd] = arcPart === "near"
	      ? (nearUsesLowerArc ? lowerArc : upperArc)
	      : (nearUsesLowerArc ? upperArc : lowerArc);
	    const sideDepth = (1.9 + variantSeed * 0.9) / Math.max(0.01, verticalScale);
	    const sideMetal = context.createLinearGradient(
	      0,
	      -dimensions.height * 0.48,
	      0,
	      dimensions.height * 0.58
	    );
	    if (resolvedHeat > 0.45) {
	      sideMetal.addColorStop(0, "rgba(21,4,15,0.98)");
	      sideMetal.addColorStop(0.58, "rgba(67,12,35,0.98)");
	      sideMetal.addColorStop(1, "rgba(19,3,14,0.99)");
	    } else {
	      sideMetal.addColorStop(0, "rgba(3,6,15,0.99)");
	      sideMetal.addColorStop(0.58, "rgba(20,29,48,0.98)");
	      sideMetal.addColorStop(1, "rgba(2,5,14,0.99)");
	    }
	    context.save();
	    context.translate(0, sideDepth);
	    context.globalAlpha = layerAlpha * (arcPart === "near" ? 0.9 : 0.62);
	    context.strokeStyle = sideMetal;
	    context.lineWidth = (isFront ? 5.8 : 5.15) * (0.96 + variantSeed * 0.07);
	    context.shadowColor = "rgba(0,0,8,0.82)";
	    context.shadowBlur = isFront ? 1.2 : 0;
	    context.beginPath();
	    context.ellipse(
	      0,
	      0,
	      dimensions.width * 0.5,
	      dimensions.height * 0.5,
	      0,
	      arcStart,
	      arcEnd
	    );
	    context.stroke();
	    if (arcPart === "near") {
	      context.globalCompositeOperation = "source-over";
	      context.globalAlpha = layerAlpha * 0.76;
	      context.strokeStyle = resolvedHeat > 0.45
	        ? "rgba(44,7,25,0.96)"
	        : "rgba(5,11,26,0.96)";
	      context.lineWidth = 1.7 + variantSeed * 0.45;
	      context.beginPath();
	      for (const capAngle of [arcStart, arcEnd]) {
	        const capX = Math.cos(capAngle) * dimensions.width * 0.5;
	        const capY = Math.sin(capAngle) * dimensions.height * 0.5;
	        context.moveTo(capX, capY - sideDepth);
	        context.lineTo(capX, capY);
	      }
	      context.stroke();
	    }
	    context.globalCompositeOperation = "screen";
	    context.globalAlpha = layerAlpha * (arcPart === "near" ? 0.3 : 0.12);
	    context.strokeStyle = resolvedHeat > 0.45
	      ? "rgba(255,145,174,0.82)"
	      : "rgba(173,201,241,0.72)";
	    context.lineWidth = 0.62;
	    context.shadowBlur = 0;
	    context.beginPath();
	    context.ellipse(
	      0,
	      -dimensions.height * 0.02,
	      dimensions.width * 0.455,
	      dimensions.height * 0.42,
	      0,
	      arcStart + (arcEnd - arcStart) * 0.14,
	      arcStart + (arcEnd - arcStart) * 0.72
	    );
	    context.stroke();
	    context.restore();
	  }
	  if (coldSprite) {
	    context.globalAlpha = layerAlpha * (1 - resolvedHeat);
	    context.drawImage(
	      coldSprite.canvas,
	      -coldSprite.width * 0.5,
	      -coldSprite.height * 0.5,
	      coldSprite.width,
	      coldSprite.height
	    );
	  }
	  if (hotSprite) {
	    context.globalAlpha = layerAlpha * resolvedHeat;
	    context.drawImage(
	      hotSprite.canvas,
	      -hotSprite.width * 0.5,
	      -hotSprite.height * 0.5,
	      hotSprite.width,
	      hotSprite.height
	    );
	  }
	  context.restore();
	};

	const drawChainLayer = (context, records, isFront) => {
	  if (mobilePerformance || chainTitleBox.width < 420) {
	    for (const record of records) {
	      drawChainLinkArc(
	        context,
	        record.sample,
	        record.linkIndex,
	        record.definition,
	        record.alpha,
	        record.heat,
	        isFront,
	        record.arcMode === "full" ? "full" : record.arcMode,
	        record.rotationOffset,
	        record.scale,
	        record.lengthScale
	      );
	    }
	    return;
	  }
	  const passes = [
	    { arcPart: "far", edgeOn: false },
	    { arcPart: "far", edgeOn: true },
	    { arcPart: "near", edgeOn: false },
	    { arcPart: "near", edgeOn: true }
	  ];
	  for (const pass of passes) {
	    for (const record of records) {
	      const edgeOn = record.linkIndex % 2 === 1;
	      if (edgeOn !== pass.edgeOn) continue;
	      if (record.arcMode !== "full" && record.arcMode !== pass.arcPart) continue;
	      drawChainLinkArc(
	        context,
	        record.sample,
	        record.linkIndex,
	        record.definition,
	        record.alpha,
	        record.heat,
	        isFront,
	        pass.arcPart,
	        record.rotationOffset,
	        record.scale,
	        record.lengthScale
	      );
	    }
	  }
	};

	const drawChainLeader = (context, leader) => {
	  if (!leader || leader.alpha <= 0.002) return;
	  const { definition, sample, alpha, heat } = leader;
	  const dimensions = getChainLinkDimensions(definition);
	  const forward = definition.direction > 0 ? 1 : -1;
	  context.save();
	  context.translate(sample.x, sample.y);
	  context.rotate(sample.angle + (forward < 0 ? Math.PI : 0));
	  context.globalCompositeOperation = "screen";
	  context.lineCap = "round";
	  const trail = context.createLinearGradient(-dimensions.width * 1.9, 0, -dimensions.width * 0.08, 0);
	  trail.addColorStop(0, "rgba(117,161,255,0)");
	  trail.addColorStop(0.68, "rgba(255,255,255,0.08)");
	  trail.addColorStop(1, "rgba(255,248,252,0.5)");
	  context.globalAlpha = alpha * (0.34 + heat * 0.2);
	  context.strokeStyle = trail;
	  context.lineWidth = 1.05 + Math.abs(velocity) * 15;
	  context.beginPath();
	  context.moveTo(-dimensions.width * 1.9, 0);
	  context.lineTo(-dimensions.width * 0.08, 0);
	  context.stroke();
	  context.lineWidth = 0.95;
	  if (heat < 0.995) {
	    context.globalAlpha = alpha * 0.46 * (1 - heat);
	    context.strokeStyle = "rgba(151,188,255,0.9)";
	    context.beginPath();
	    context.moveTo(-dimensions.width * 0.34, 0);
	    context.lineTo(-dimensions.width * 0.07, 0);
	    context.stroke();
	  }
	  if (heat > 0.005) {
	    context.globalAlpha = alpha * 0.46 * heat;
	    context.strokeStyle = "rgba(255,92,151,0.92)";
	    context.beginPath();
	    context.moveTo(-dimensions.width * 0.34, 0);
	    context.lineTo(-dimensions.width * 0.07, 0);
	    context.stroke();
	  }
	  context.restore();
	};

	const resolveBrokenSegmentMotion = (
	  definition,
	  breakSample,
	  side,
	  dimensions,
	  breakOpen,
	  recoil,
	  snapPulse = 0
	) => {
	  const polarity = definition.id === 1 ? -1 : 1;
	  const gapTravel = dimensions.width
	    * (definition.type === "frame" ? 0.36 : 0.42)
	    * breakOpen;
	  const recoilTravel = chainTitleBox.width
	    * (definition.type === "frame" ? 0.016 : 0.014)
	    * recoil
	    + chainTitleBox.height * 0.018 * snapPulse;
	  const normalTravel = chainTitleBox.height
	    * (0.012 * recoil + 0.022 * snapPulse);
	  return {
	    side,
	    swingAngle: side
	      * polarity
	      * (definition.type === "frame" ? 0.075 : 0.095)
	      * (recoil + snapPulse * 0.26),
	    translateX: breakSample.tangentX * side * (gapTravel + recoilTravel)
	      + breakSample.normalX * side * polarity * normalTravel,
	    translateY: breakSample.tangentY * side * (gapTravel + recoilTravel)
	      + breakSample.normalY * side * polarity * normalTravel
	  };
	};

	const applyBrokenSegmentMotion = (sample, breakSample, motion) => {
	  const relativeX = sample.x - breakSample.x;
	  const relativeY = sample.y - breakSample.y;
	  const cosine = Math.cos(motion.swingAngle);
	  const sine = Math.sin(motion.swingAngle);
	  sample.x = breakSample.x
	    + relativeX * cosine
	    - relativeY * sine
	    + motion.translateX;
	  sample.y = breakSample.y
	    + relativeX * sine
	    + relativeY * cosine
	    + motion.translateY;
	  sample.angle += motion.swingAngle;
	};

	const drawBrokenChainPiece = (
	  context,
	  event,
	  side,
	  visibility,
	  rupturePulse
	) => {
	  const {
	    definition,
	    breakSample,
	    heat,
	    breakOpen,
	    recoil,
	    snapPulse,
	    releaseFade
	  } = event;
	  if (breakOpen <= 0.001) return;
	  const dimensions = getChainLinkDimensions(definition);
	  const motion = resolveBrokenSegmentMotion(
	    definition,
	    breakSample,
	    side,
	    dimensions,
	    breakOpen,
	    recoil,
	    snapPulse
	  );
	  const fragmentProgress = clamp(breakOpen * 0.62 + recoil * 0.38, 0, 1.08);
	  const polarity = definition.id === 1 ? -1 : 1;
	  const center = {
	    x: breakSample.x + breakSample.tangentX * side * dimensions.width * 0.16,
	    y: breakSample.y + breakSample.tangentY * side * dimensions.width * 0.16,
	    angle: breakSample.angle
	  };
	  applyBrokenSegmentMotion(center, breakSample, motion);
	  center.x += breakSample.tangentX
	    * side
	    * dimensions.width
	    * fragmentProgress
	    * (0.42 + snapPulse * 0.24);
	  center.y += breakSample.tangentY
	    * side
	    * dimensions.width
	    * fragmentProgress
	    * (0.42 + snapPulse * 0.24);
	  center.x += breakSample.normalX
	    * side
	    * polarity
	    * dimensions.height
	    * (0.22 + fragmentProgress * 0.48);
	  center.y += breakSample.normalY
	    * side
	    * polarity
	    * dimensions.height
	    * (0.22 + fragmentProgress * 0.48);
	  center.angle += side
	    * polarity
	    * (0.24 + fragmentProgress * 0.78 + snapPulse * 0.18);
	  const pieceAlpha = visibility
	    * smootherstep(clamp(breakOpen / 0.28, 0, 1))
	    * (1 - releaseFade * 0.96);
	  if (pieceAlpha <= 0.002) return;

	  context.save();
	  context.globalCompositeOperation = "source-over";
	  drawChainLinkArc(
	    context,
	    center,
	    side < 0 ? 0 : 1,
	    definition,
	    pieceAlpha,
	    heat,
	    true,
	    side < 0 ? "far" : "near",
	    side * fragmentProgress * 0.34,
	    0.94 + snapPulse * 0.08,
	    1
	  );
	  context.translate(center.x, center.y);
	  context.rotate(center.angle + side * fragmentProgress * 0.34);
	  context.globalCompositeOperation = "screen";
	  context.globalAlpha = pieceAlpha * Math.max(rupturePulse, snapPulse) * 0.92;
	  context.strokeStyle = "rgba(255,244,249,0.98)";
	  context.lineWidth = 0.9 + snapPulse * 0.65;
	  context.shadowColor = "rgba(255,70,138,0.94)";
	  context.shadowBlur = 4 + snapPulse * 5;
	  const cutX = -side * dimensions.width * 0.27;
	  const cutY = side * dimensions.height * 0.18;
	  context.beginPath();
	  context.moveTo(cutX - side * 2.8, cutY - 2.5);
	  context.lineTo(cutX + side * 3.2, cutY + 2.6);
	  context.stroke();
	  context.restore();
	};

	const createHeartPath = (centerX, centerY, size, scale = 1) => {
	  const path = new Path2D();
	  const steps = 52;
	  for (let index = 0; index <= steps; index += 1) {
	    const angle = index / steps * fullTurn;
	    const x = Math.sin(angle) ** 3 * 16;
	    const y = -(
	      13 * Math.cos(angle)
	        - 5 * Math.cos(angle * 2)
	        - 2 * Math.cos(angle * 3)
	        - Math.cos(angle * 4)
	    );
	    const pointX = centerX + x / 17 * size * scale;
	    const pointY = centerY + y / 17 * size * scale;
	    if (index === 0) path.moveTo(pointX, pointY);
	    else path.lineTo(pointX, pointY);
	  }
	  path.closePath();
	  return path;
	};

	const drawChainHeartSeal = (timestamp, intro, events, visibility, isMobile) => {
	  if (!chainBackContext || !chainFrontContext || events.length === 0) return;
	  const build = smootherstep(clamp((intro - 0.49) / 0.16, 0, 1));
	  const fracture = smootherstep(clamp((intro - 0.69) / 0.18, 0, 1));
	  const fade = 1 - smootherstep(clamp((intro - 0.88) / 0.095, 0, 1));
	  const opacity = build * fade * visibility;
	  if (opacity <= 0.001) return;

	  const centerX = (chainGlyphLayout.centerX || chainTitleBox.left + chainTitleBox.width * 0.5)
	    + chainTitleBox.width * 0.012;
	  const centerY = (chainGlyphLayout.centerY || chainTitleBox.top + chainTitleBox.height * 0.52)
	    + chainTitleBox.height * 0.045;
	  const lockPulse = Math.exp(-Math.pow((intro - 0.665) / 0.052, 2));
	  const heartbeat = 0.5 + Math.sin(timestamp * 0.018) * 0.5;
	  const size = clamp(
	    chainTitleBox.height * (isMobile ? 0.205 : 0.19),
	    isMobile ? 15 : 17,
	    isMobile ? 25 : 32
	  ) * (0.82 + build * 0.18 + lockPulse * 0.08);
	  const splitDistance = size * fracture * 0.29;
	  const splitDrop = size * fracture ** 2 * 0.08;
	  const heart = createHeartPath(centerX, centerY, size);
	  const tetherOpacity = opacity * (1 - fracture) * 0.68;

	  if (tetherOpacity > 0.002) {
	    const tetherTargets = [
	      { x: centerX - size * 0.56, y: centerY - size * 0.14 },
	      { x: centerX + size * 0.56, y: centerY - size * 0.14 },
	      { x: centerX, y: centerY + size * 0.72 }
	    ];
	    for (let index = 0; index < events.length; index += 1) {
	      const event = events[index];
	      const target = tetherTargets[index % tetherTargets.length];
	      const controlX = event.breakSample.x
	        + (target.x - event.breakSample.x) * 0.55
	        + event.breakSample.normalX * size * (index - 1) * 0.18;
	      const controlY = event.breakSample.y
	        + (target.y - event.breakSample.y) * 0.42
	        + event.breakSample.normalY * size * (index - 1) * 0.18;
	      chainBackContext.save();
	      chainBackContext.globalCompositeOperation = "source-over";
	      chainBackContext.globalAlpha = tetherOpacity * 0.72;
	      chainBackContext.strokeStyle = "rgba(29,7,30,0.9)";
	      chainBackContext.lineWidth = 3.4;
	      chainBackContext.beginPath();
	      chainBackContext.moveTo(event.breakSample.x, event.breakSample.y);
	      chainBackContext.quadraticCurveTo(controlX, controlY, target.x, target.y);
	      chainBackContext.stroke();
	      chainBackContext.restore();

	      chainFrontContext.save();
	      chainFrontContext.globalCompositeOperation = "screen";
	      chainFrontContext.globalAlpha = tetherOpacity * (0.62 + event.snapPulse * 0.32);
	      chainFrontContext.strokeStyle = index === 1
	        ? "rgba(255,239,247,0.96)"
	        : "rgba(255,83,142,0.94)";
	      chainFrontContext.lineWidth = 0.72 + event.snapPulse * 0.52;
	      chainFrontContext.shadowColor = "rgba(255,54,126,0.84)";
	      chainFrontContext.shadowBlur = 3 + event.snapPulse * 5;
	      chainFrontContext.beginPath();
	      chainFrontContext.moveTo(event.breakSample.x, event.breakSample.y);
	      chainFrontContext.quadraticCurveTo(controlX, controlY, target.x, target.y);
	      chainFrontContext.stroke();
	      chainFrontContext.restore();
	    }
	  }

	  const drawHeartHalf = (context, side, drawMaterial) => {
	    context.save();
	    if (fracture > 0.001) {
	      context.beginPath();
	      context.rect(
	        side < 0 ? centerX - size * 1.7 : centerX,
	        centerY - size * 1.7,
	        size * 1.7,
	        size * 3.4
	      );
	      context.clip();
	      context.translate(centerX, centerY);
	      context.rotate(side * fracture * 0.085);
	      context.translate(-centerX + side * splitDistance, -centerY + splitDrop);
	    }
	    drawMaterial();
	    context.restore();
	  };

	  for (const side of fracture > 0.001 ? [-1, 1] : [0]) {
	    drawHeartHalf(chainBackContext, side, () => {
	      chainBackContext.globalCompositeOperation = "source-over";
	      chainBackContext.globalAlpha = opacity * 0.32;
	      chainBackContext.fillStyle = "rgba(72,8,48,0.72)";
	      chainBackContext.shadowColor = "rgba(255,44,116,0.28)";
	      chainBackContext.shadowBlur = 4 + lockPulse * 4;
	      chainBackContext.fill(heart);
	      chainBackContext.globalAlpha = opacity * 0.72;
	      chainBackContext.strokeStyle = "rgba(27,6,29,0.94)";
	      chainBackContext.lineWidth = 4.4;
	      chainBackContext.stroke(heart);
	    });
	    drawHeartHalf(chainFrontContext, side, () => {
	      chainFrontContext.globalCompositeOperation = "screen";
	      chainFrontContext.globalAlpha = opacity * 0.12;
	      chainFrontContext.fillStyle = "rgba(255,57,124,0.88)";
	      chainFrontContext.shadowColor = "rgba(255,48,118,0.52)";
	      chainFrontContext.shadowBlur = 4 + lockPulse * 4;
	      chainFrontContext.fill(heart);
	      chainFrontContext.globalAlpha = opacity * (0.76 + heartbeat * 0.12);
	      chainFrontContext.strokeStyle = "rgba(255,72,137,0.98)";
	      chainFrontContext.lineWidth = 2.05 + lockPulse * 0.5;
	      chainFrontContext.shadowColor = "rgba(255,50,122,0.88)";
	      chainFrontContext.shadowBlur = 5 + lockPulse * 5;
	      chainFrontContext.stroke(heart);
	      chainFrontContext.globalAlpha = opacity * (0.58 + lockPulse * 0.28);
	      chainFrontContext.strokeStyle = "rgba(255,245,250,0.98)";
	      chainFrontContext.lineWidth = 0.68 + lockPulse * 0.32;
	      chainFrontContext.shadowBlur = 1.6;
	      chainFrontContext.stroke(heart);
	    });
	  }

	  if (fracture > 0.015) {
	    chainFrontContext.save();
	    chainFrontContext.globalCompositeOperation = "screen";
	    chainFrontContext.globalAlpha = opacity * Math.sin(fracture * Math.PI) * 0.9;
	    chainFrontContext.strokeStyle = "rgba(255,248,251,0.98)";
	    chainFrontContext.lineWidth = 0.9 + lockPulse * 0.5;
	    chainFrontContext.shadowColor = "rgba(255,57,128,0.92)";
	    chainFrontContext.shadowBlur = 5;
	    chainFrontContext.beginPath();
	    chainFrontContext.moveTo(centerX - size * 0.02, centerY - size * 0.76);
	    chainFrontContext.lineTo(centerX + size * 0.12, centerY - size * 0.24);
	    chainFrontContext.lineTo(centerX - size * 0.08, centerY + size * 0.12);
	    chainFrontContext.lineTo(centerX + size * 0.04, centerY + size * 0.72);
	    chainFrontContext.stroke();

	    const shardPulse = Math.sin(smootherstep(fracture) * Math.PI);
	    for (let shardIndex = 0; shardIndex < (isMobile ? 5 : 7); shardIndex += 1) {
	      const seed = randomSeed(41021 + shardIndex * 91.7);
	      const angle = -Math.PI * 0.92 + seed * Math.PI * 1.84;
	      const travel = size * fracture * (0.52 + seed * 1.08);
	      const startX = centerX + Math.cos(angle) * size * 0.38;
	      const startY = centerY + Math.sin(angle) * size * 0.3;
	      const endX = startX + Math.cos(angle) * travel;
	      const endY = startY + Math.sin(angle) * travel * 0.72;
	      chainFrontContext.globalAlpha = opacity * shardPulse * (0.38 + seed * 0.48);
	      chainFrontContext.strokeStyle = shardIndex % 3 === 0
	        ? "rgba(229,239,255,0.96)"
	        : "rgba(255,87,145,0.96)";
	      chainFrontContext.lineWidth = 0.6 + seed * 0.9;
	      chainFrontContext.beginPath();
	      chainFrontContext.moveTo(startX, startY);
	      chainFrontContext.lineTo(endX, endY);
	      chainFrontContext.stroke();
	    }
	    chainFrontContext.restore();
	  }
	};

	const drawChainShatterParticles = (context, records, isMobile) => {
	  if (!context || records.length === 0) return;
	  const shardCount = isMobile ? 4 : 6;
	  context.save();
	  context.lineCap = "round";
	  context.lineJoin = "round";
	  for (const record of records) {
	    const born = smootherstep(clamp(record.age / 0.045, 0, 1));
	    const fade = 1 - smootherstep(clamp((record.age - 0.58) / 0.42, 0, 1));
	    const baseAlpha = record.alpha * born * fade;
	    if (baseAlpha <= 0.002) continue;
	    const dimensions = getChainLinkDimensions(record.definition);
	    const outwardX = record.sample.tangentX * record.side;
	    const outwardY = record.sample.tangentY * record.side;
	    const sampleCosine = Math.cos(record.sample.angle);
	    const sampleSine = Math.sin(record.sample.angle);
	    for (let shardIndex = 0; shardIndex < shardCount; shardIndex += 1) {
	      const seedA = randomSeed(record.seed * 701.3 + shardIndex * 53.7 + 17.1);
	      const seedB = randomSeed(record.seed * 977.9 + shardIndex * 89.3 + 31.7);
	      const seedC = randomSeed(record.seed * 1237.1 + shardIndex * 131.9 + 47.3);
	      const rimAngle = seedC * fullTurn;
	      const localRimX = Math.cos(rimAngle)
	        * dimensions.width
	        * (0.28 + seedA * 0.08);
	      const localRimY = Math.sin(rimAngle)
	        * dimensions.height
	        * (0.3 + seedB * 0.08);
	      const originX = record.sample.x
	        + localRimX * sampleCosine
	        - localRimY * sampleSine;
	      const originY = record.sample.y
	        + localRimX * sampleSine
	        + localRimY * sampleCosine;
	      const localRadialLength = Math.max(0.001, Math.hypot(localRimX, localRimY));
	      const localRadialX = localRimX / localRadialLength;
	      const localRadialY = localRimY / localRadialLength;
	      const radialX = localRadialX * sampleCosine - localRadialY * sampleSine;
	      const radialY = localRadialX * sampleSine + localRadialY * sampleCosine;
	      let velocityX = radialX * (0.72 + seedA * 0.88)
	        + outwardX * (0.34 + seedB * 0.74)
	        + record.sample.normalX * (seedC - 0.5) * 1.35;
	      let velocityY = radialY * (0.72 + seedA * 0.88)
	        + outwardY * (0.34 + seedB * 0.74)
	        + record.sample.normalY * (seedC - 0.5) * 1.35;
	      const velocityLength = Math.max(0.001, Math.hypot(velocityX, velocityY));
	      velocityX /= velocityLength;
	      velocityY /= velocityLength;
	      const travel = chainTitleBox.height
	        * (0.085 + seedA * 0.42)
	        * easeOutCubic(record.age);
	      const drift = Math.sin(record.age * Math.PI)
	        * chainTitleBox.height
	        * (seedB - 0.5)
	        * 0.075;
	      const x = originX
	        + velocityX * travel
	        + record.sample.normalX * drift;
	      const y = originY
	        + velocityY * travel
	        + record.sample.normalY * drift
	        + chainTitleBox.height * record.age ** 2 * (seedC - 0.34) * 0.028;
	      const angle = Math.atan2(velocityY, velocityX)
	        + (seedC - 0.5) * record.age * 4.8;
	      const shardLength = (2.3 + seedB * 5.8) * (1 - record.age * 0.32);
	      const shardWidth = (0.85 + seedC * 1.55) * (1 - record.age * 0.24);
	      const directionX = Math.cos(angle);
	      const directionY = Math.sin(angle);
	      const perpendicularX = -directionY;
	      const perpendicularY = directionX;
	      const halfLength = shardLength * 0.5;
	      const halfWidth = shardWidth * 0.5;
	      const shardAlpha = baseAlpha * (0.62 + seedA * 0.36);

	      context.globalCompositeOperation = "source-over";
	      context.globalAlpha = shardAlpha;
	      context.fillStyle = record.heat > 0.52
	        ? "rgba(37,7,23,0.98)"
	        : "rgba(10,15,35,0.98)";
	      context.beginPath();
	      context.moveTo(
	        x + directionX * halfLength,
	        y + directionY * halfLength
	      );
	      context.lineTo(
	        x - directionX * halfLength + perpendicularX * halfWidth,
	        y - directionY * halfLength + perpendicularY * halfWidth
	      );
	      context.lineTo(
	        x - directionX * halfLength - perpendicularX * halfWidth,
	        y - directionY * halfLength - perpendicularY * halfWidth
	      );
	      context.closePath();
	      context.fill();

	      context.globalAlpha = shardAlpha * 0.92;
	      context.strokeStyle = record.heat > 0.52
	        ? "rgba(242,76,132,0.98)"
	        : "rgba(126,166,232,0.98)";
	      context.lineWidth = 0.58 + seedC * 0.64;
	      context.beginPath();
	      context.moveTo(
	        x - directionX * halfLength * 0.82,
	        y - directionY * halfLength * 0.82
	      );
	      context.lineTo(
	        x + directionX * halfLength,
	        y + directionY * halfLength
	      );
	      context.stroke();

	      context.globalCompositeOperation = "screen";
	      context.globalAlpha = shardAlpha * (0.38 + seedB * 0.46);
	      context.fillStyle = shardIndex % 2 === 0
	        ? "rgba(255,239,247,0.96)"
	        : "rgba(255,91,150,0.92)";
	      context.beginPath();
	      context.arc(
	        x + directionX * halfLength,
	        y + directionY * halfLength,
	        0.42 + seedA * 0.78,
	        0,
	        fullTurn
	      );
	      context.fill();
	    }
	  }
	  context.restore();
	};

	const createContractHeartPath = (centerX, centerY, size, scale = 1) => {
	  const radius = size * scale;
	  const path = new Path2D();
	  path.moveTo(centerX, centerY + radius * 0.74);
	  path.bezierCurveTo(
	    centerX - radius * 0.16,
	    centerY + radius * 0.58,
	    centerX - radius * 0.92,
	    centerY + radius * 0.12,
	    centerX - radius * 0.92,
	    centerY - radius * 0.34
	  );
	  path.bezierCurveTo(
	    centerX - radius * 0.92,
	    centerY - radius * 0.73,
	    centerX - radius * 0.48,
	    centerY - radius * 0.92,
	    centerX,
	    centerY - radius * 0.47
	  );
	  path.bezierCurveTo(
	    centerX + radius * 0.48,
	    centerY - radius * 0.92,
	    centerX + radius * 0.92,
	    centerY - radius * 0.73,
	    centerX + radius * 0.92,
	    centerY - radius * 0.34
	  );
	  path.bezierCurveTo(
	    centerX + radius * 0.92,
	    centerY + radius * 0.12,
	    centerX + radius * 0.16,
	    centerY + radius * 0.58,
	    centerX,
	    centerY + radius * 0.74
	  );
	  path.closePath();
	  return path;
	};

	const drawContractHeartImprint = (timestamp, intro, events, visibility, isMobile) => {
	  if (!chainBackContext || !chainFrontContext || events.length === 0) return;
	  const build = smootherstep(clamp((intro - 0.23) / 0.105, 0, 1));
	  const collapse = smootherstep(clamp((intro - 0.68) / 0.105, 0, 1));
	  const fade = 1 - smootherstep(clamp((intro - 0.84) / 0.11, 0, 1));
	  const opacity = build * fade * visibility;
	  if (opacity <= 0.001) return;

	  const centerX = (chainGlyphLayout.centerX || chainTitleBox.left + chainTitleBox.width * 0.5)
	    + chainTitleBox.width * 0.012;
	  const centerY = (chainGlyphLayout.centerY || chainTitleBox.top + chainTitleBox.height * 0.52)
	    + chainTitleBox.height * 0.045;
	  const lockPulse = Math.exp(-Math.pow((intro - 0.36) / 0.042, 2));
	  const heartbeat = 0.5 + Math.sin(timestamp * 0.016) * 0.5;
	  const size = clamp(
	    chainTitleBox.height * (isMobile ? 0.205 : 0.19),
	    isMobile ? 15 : 17,
	    isMobile ? 25 : 32
	  );
	  const heartScale = (0.76 + build * 0.24 + lockPulse * 0.08)
	    * (1 - collapse * 0.56);
	  const heart = createContractHeartPath(centerX, centerY, size, heartScale);
	  const threadStrength = phaseProgress(intro, 0.19, 0.255)
	    * (1 - phaseProgress(intro, 0.39, 0.5));

	  if (threadStrength > 0.001) {
	    chainFrontContext.save();
	    chainFrontContext.globalCompositeOperation = "screen";
	    chainFrontContext.lineCap = "round";
	    for (let index = 0; index < events.length; index += 1) {
	      const event = events[index];
	      const bend = (index - 1) * size * 0.28;
	      chainFrontContext.globalAlpha = visibility * threadStrength * (0.34 + index * 0.08);
	      chainFrontContext.strokeStyle = index === 1
	        ? "rgba(255,240,247,0.94)"
	        : "rgba(255,75,138,0.9)";
	      chainFrontContext.lineWidth = 0.62 + event.snapPulse * 0.36;
	      chainFrontContext.beginPath();
	      chainFrontContext.moveTo(event.breakSample.x, event.breakSample.y);
	      chainFrontContext.quadraticCurveTo(
	        (event.breakSample.x + centerX) * 0.5 + event.breakSample.normalX * bend,
	        (event.breakSample.y + centerY) * 0.5 + event.breakSample.normalY * bend,
	        centerX,
	        centerY
	      );
	      chainFrontContext.stroke();
	    }
	    chainFrontContext.restore();
	  }

	  chainBackContext.save();
	  chainBackContext.globalCompositeOperation = "source-over";
	  chainBackContext.globalAlpha = opacity * (0.3 + lockPulse * 0.08);
	  chainBackContext.fillStyle = "rgba(66,7,43,0.8)";
	  chainBackContext.shadowColor = "rgba(255,43,115,0.3)";
	  chainBackContext.shadowBlur = 4 + lockPulse * 3;
	  chainBackContext.fill(heart);
	  chainBackContext.globalAlpha = opacity * 0.78;
	  chainBackContext.strokeStyle = "rgba(24,5,28,0.96)";
	  chainBackContext.lineWidth = 4.2;
	  chainBackContext.stroke(heart);
	  chainBackContext.restore();

	  chainFrontContext.save();
	  chainFrontContext.globalCompositeOperation = "screen";
	  chainFrontContext.globalAlpha = opacity * (0.24 + lockPulse * 0.16);
	  chainFrontContext.fillStyle = "rgba(255,53,121,0.9)";
	  chainFrontContext.shadowColor = "rgba(255,47,117,0.56)";
	  chainFrontContext.shadowBlur = 4 + lockPulse * 6;
	  chainFrontContext.fill(heart);
	  chainFrontContext.globalAlpha = opacity * (0.82 + heartbeat * 0.1);
	  chainFrontContext.strokeStyle = "rgba(255,72,137,0.99)";
	  chainFrontContext.lineWidth = 2.1 + lockPulse * 0.42;
	  chainFrontContext.stroke(heart);
	  chainFrontContext.globalAlpha = opacity * (0.58 + lockPulse * 0.24);
	  chainFrontContext.strokeStyle = "rgba(255,247,251,0.98)";
	  chainFrontContext.lineWidth = 0.68 + lockPulse * 0.28;
	  chainFrontContext.shadowBlur = 1.4;
	  chainFrontContext.stroke(heart);

	  if (lockPulse > 0.001) {
	    const pulseHeart = createContractHeartPath(
	      centerX,
	      centerY,
	      size,
	      heartScale * (1 + lockPulse * 0.34)
	    );
	    chainFrontContext.globalAlpha = opacity * lockPulse * 0.3;
	    chainFrontContext.strokeStyle = "rgba(255,229,241,0.96)";
	    chainFrontContext.lineWidth = 0.82;
	    chainFrontContext.shadowBlur = 5;
	    chainFrontContext.stroke(pulseHeart);
	  }
	  chainFrontContext.restore();

	  const burst = phaseProgress(intro, 0.695, 0.94);
	  if (burst <= 0.001) return;
	  chainFrontContext.save();
	  chainFrontContext.globalCompositeOperation = "screen";
	  chainFrontContext.lineCap = "round";
	  const particleCount = isMobile ? 10 : 15;
	  for (let index = 0; index < particleCount; index += 1) {
	    const seedA = randomSeed(52021 + index * 73.7);
	    const seedB = randomSeed(62003 + index * 97.1);
	    const age = clamp((burst - seedA * 0.13) / (1 - seedA * 0.13), 0, 1);
	    if (age <= 0.001 || age >= 0.999) continue;
	    const born = smootherstep(clamp(age / 0.12, 0, 1));
	    const particleAlpha = visibility * born * (1 - age) ** 1.45;
	    const angle = seedB * fullTurn - Math.PI * 0.5;
	    const travel = size * (0.44 + seedA * 1.9) * easeOutCubic(age);
	    const x = centerX + Math.cos(angle) * travel;
	    const y = centerY + Math.sin(angle) * travel * 0.78;
	    const length = 0.8 + seedB * 3.2;
	    chainFrontContext.globalAlpha = particleAlpha * (0.46 + seedA * 0.5);
	    chainFrontContext.strokeStyle = index % 3 === 0
	      ? "rgba(226,239,255,0.96)"
	      : "rgba(255,81,143,0.96)";
	    chainFrontContext.lineWidth = 0.55 + seedA * 0.62;
	    chainFrontContext.beginPath();
	    chainFrontContext.moveTo(
	      x - Math.cos(angle) * length,
	      y - Math.sin(angle) * length
	    );
	    chainFrontContext.lineTo(x, y);
	    chainFrontContext.stroke();
	  }
	  const collapseFlash = Math.sin(collapse * Math.PI);
	  if (collapseFlash > 0.001) {
	    const flash = chainFrontContext.createRadialGradient(
	      centerX,
	      centerY,
	      0,
	      centerX,
	      centerY,
	      size * (0.5 + collapseFlash * 0.8)
	    );
	    flash.addColorStop(0, "rgba(255,255,255,0.96)");
	    flash.addColorStop(0.18, "rgba(255,205,226,0.78)");
	    flash.addColorStop(1, "rgba(255,48,119,0)");
	    chainFrontContext.globalAlpha = visibility * collapseFlash * 0.72;
	    chainFrontContext.fillStyle = flash;
	    chainFrontContext.fillRect(
	      centerX - size * 1.4,
	      centerY - size * 1.4,
	      size * 2.8,
	      size * 2.8
	    );
	  }
	  chainFrontContext.restore();
	};

	const drawChainRupture = (timestamp, intro, events, visibility, isMobile) => {
	  if (!chainFrontContext || events.length === 0) return;
	  const stressPulse = Math.sin(phaseProgress(intro, 0.012, 0.145) * Math.PI);
	  const rupturePulse = Math.sin(phaseProgress(intro, 0.1, 0.48) * Math.PI);
	  if (Math.max(stressPulse, rupturePulse) <= 0.001) return;
	  const context = chainFrontContext;
	  context.save();
	  context.lineCap = "round";
	  for (const event of events) {
	    const { breakSample, breakSeed, heat, breakOpen, snapPulse } = event;
	    const dimensions = getChainLinkDimensions(event.definition);
	    context.save();
	    context.globalCompositeOperation = "screen";
	    if (stressPulse > 0.001 && breakOpen < 0.98) {
	      const stressLength = dimensions.width * (0.4 + stressPulse * 0.42);
	      context.globalAlpha = visibility * stressPulse * (1 - breakOpen) * 0.72;
	      context.strokeStyle = heat > 0.5
	        ? "rgba(255,229,240,0.98)"
	        : "rgba(226,238,255,0.96)";
	      context.lineWidth = 0.8 + stressPulse * 1.2;
	      context.shadowColor = heat > 0.5
	        ? "rgba(255,56,128,0.9)"
	        : "rgba(126,166,255,0.78)";
	      context.shadowBlur = 4 + stressPulse * 8;
	      context.beginPath();
	      context.moveTo(
	        breakSample.x - breakSample.tangentX * stressLength,
	        breakSample.y - breakSample.tangentY * stressLength
	      );
	      context.lineTo(
	        breakSample.x + breakSample.tangentX * stressLength,
	        breakSample.y + breakSample.tangentY * stressLength
	      );
	      context.stroke();
	    }

	    if (snapPulse > 0.002) {
	      const coreRadius = dimensions.width * (0.24 + snapPulse * 0.46);
	      const core = context.createRadialGradient(
	        breakSample.x,
	        breakSample.y,
	        0,
	        breakSample.x,
	        breakSample.y,
	        coreRadius
	      );
	      core.addColorStop(0, "rgba(255,255,255,0.98)");
	      core.addColorStop(0.16, "rgba(255,221,235,0.88)");
	      core.addColorStop(0.46, "rgba(255,62,130,0.38)");
	      core.addColorStop(1, "rgba(255,45,119,0)");
	      context.globalAlpha = visibility * snapPulse * 0.96;
	      context.fillStyle = core;
	      context.fillRect(
	        breakSample.x - coreRadius,
	        breakSample.y - coreRadius,
	        coreRadius * 2,
	        coreRadius * 2
	      );

	      context.translate(breakSample.x, breakSample.y);
	      context.rotate(breakSample.angle);
	      context.globalAlpha = visibility * snapPulse * 0.84;
	      context.strokeStyle = heat > 0.5
	        ? "rgba(255,230,240,0.98)"
	        : "rgba(226,240,255,0.98)";
	      context.lineWidth = 0.72 + snapPulse * 0.86;
	      context.shadowColor = "rgba(255,58,132,0.9)";
	      context.shadowBlur = 4 + snapPulse * 7;
	      for (const side of [-1, 1]) {
	        context.beginPath();
	        context.ellipse(
	          side * dimensions.width * 0.07,
	          0,
	          dimensions.width * (0.36 + snapPulse * 0.72),
	          dimensions.height * (0.34 + snapPulse * 0.48),
	          0,
	          side < 0 ? Math.PI * 0.64 : -Math.PI * 0.36,
	          side < 0 ? Math.PI * 1.18 : Math.PI * 0.18
	        );
	        context.stroke();
	      }
	      context.rotate(-breakSample.angle);
	      context.translate(-breakSample.x, -breakSample.y);
	    }

	    if (rupturePulse <= 0.001) {
	      context.restore();
	      continue;
	    }
	    const sparkCount = isMobile ? 5 : 8;
	    for (let sparkIndex = 0; sparkIndex < sparkCount; sparkIndex += 1) {
	      const seed = randomSeed(breakSeed * 1000 + sparkIndex * 37.1);
	      const direction = sparkIndex % 2 === 0 ? -1 : 1;
	      const tangentWeight = (0.52 + seed * 0.82) * direction;
	      const normalWeight = (seed - 0.5) * 1.08;
	      const length = chainTitleBox.height
	        * (0.055 + seed * 0.13)
	        * (0.52 + rupturePulse * 0.48);
	      const bend = (seed - 0.5) * chainTitleBox.height * 0.045;
	      const midX = breakSample.x
	        + (breakSample.tangentX * tangentWeight + breakSample.normalX * normalWeight)
	          * length
	          * 0.52
	        + breakSample.normalX * bend;
	      const midY = breakSample.y
	        + (breakSample.tangentY * tangentWeight + breakSample.normalY * normalWeight)
	          * length
	          * 0.52
	        + breakSample.normalY * bend;
	      const endX = breakSample.x
	        + (breakSample.tangentX * tangentWeight + breakSample.normalX * normalWeight) * length;
	      const endY = breakSample.y
	        + (breakSample.tangentY * tangentWeight + breakSample.normalY * normalWeight) * length;
	      context.globalAlpha = visibility
	        * rupturePulse
	        * (0.46 + seed * 0.48)
	        * (0.74 + snapPulse * 0.26);
	      context.strokeStyle = sparkIndex % 3 === 0
	        ? "rgba(255,251,253,0.98)"
	        : "rgba(255,94,151,0.94)";
	      context.lineWidth = 0.72 + seed * 1.08;
	      context.shadowColor = "rgba(255,51,124,0.9)";
	      context.shadowBlur = 3 + rupturePulse * 6;
	      context.beginPath();
	      context.moveTo(
	        breakSample.x + breakSample.tangentX * tangentWeight * 2,
	        breakSample.y + breakSample.tangentY * tangentWeight * 2
	      );
	      context.quadraticCurveTo(midX, midY, endX, endY);
	      context.stroke();
	    }
	    context.restore();
	  }
	  context.restore();
	};

	const drawTitleChains = (timestamp, fill) => {
	  if (!chainBackCanvas || !chainBackContext || !chainFrontCanvas || !chainFrontContext) return;
	  if (chainCanvasWidth <= 1 || chainCanvasHeight <= 1 || chainTitleBox.width <= 1) {
	    resizeTitleChains();
	  }
	  if (chainCanvasWidth <= 1 || chainCanvasHeight <= 1 || chainTitleBox.width <= 1) return;

	  const intro = clamp(chargeIntroProgress, 0, 1);
	  const activation = phaseProgress(fill, 0.012, 0.11);
	  const introFade = 1 - phaseProgress(intro, 0.955, 1);
	  const burstFade = 1 - phaseProgress(burstProgress, 0.004, 0.045);
	  const visibility = activation * introFade * burstFade;
	  if (visibility <= 0.001) {
	    if (chainFrontCanvas.style.opacity !== "0" || chainBackCanvas.style.opacity !== "0") {
	      clearTitleChains();
	    }
	    return;
	  }

	  const contexts = [chainBackContext, chainFrontContext];
	  const canvases = [chainBackCanvas, chainFrontCanvas];
	  for (let layerIndex = 0; layerIndex < contexts.length; layerIndex += 1) {
	    const context = contexts[layerIndex];
	    const canvas = canvases[layerIndex];
	    context.setTransform(1, 0, 0, 1, 0, 0);
	    context.clearRect(0, 0, canvas.width, canvas.height);
	    context.setTransform(chainPixelRatio, 0, 0, chainPixelRatio, 0, 0);
	  }

	  const isMobile = mobilePerformance || chainTitleBox.width < 420;
	  const releaseFade = phaseProgress(intro, 0.84, 0.985);
	  const layerRecords = { back: [], front: [] };
	  const shatterRecords = [];
	  const ruptureEvents = [];
	  const leaders = [];
	  const colorFront = -0.26
	    + phaseProgress(fill, 0.1, 1) * 1.16
	    + phaseProgress(intro, 0.02, 0.115) * 0.16;
	  const resolveChainHeat = (order, seed = 0.5) => {
	    const localFront = colorFront + (seed - 0.5) * 0.1;
	    return 1 - smootherstep(clamp((order - (localFront - 0.24)) / 0.48, 0, 1));
	  };
	  const edgeMarginX = Math.max(24, chainCanvasWidth * 0.07);
	  const edgeMarginY = Math.max(18, chainCanvasHeight * 0.08);
	  const resolveCanvasEdgeFade = (sample) => {
	    const left = smootherstep(clamp(sample.x / edgeMarginX, 0, 1));
	    const right = smootherstep(clamp((chainCanvasWidth - sample.x) / edgeMarginX, 0, 1));
	    const top = smootherstep(clamp(sample.y / edgeMarginY, 0, 1));
	    const bottom = smootherstep(clamp((chainCanvasHeight - sample.y) / edgeMarginY, 0, 1));
	    return left * right * top * bottom;
	  };

	  for (const definition of chainDefinitions) {
	    const buildStart = isMobile && definition.type === "weave"
	      ? definition.id === 1
	        ? 0.22
	        : 0.56
	      : definition.buildStart;
	    const buildEnd = isMobile && definition.type === "weave"
	      ? definition.id === 1
	        ? 0.82
	        : 1
	      : definition.buildEnd;
	    const build = phaseProgress(fill, buildStart, buildEnd);
	    if (build <= 0.001) continue;
	    const path = resolveTitleChainPath(definition, fill, intro);
	    const spacing = buildTitleChainLinkUnits(definition, isMobile);
	    const frameConnectorLengthScale = definition.type === "frame"
	      ? clamp(
	          (
	            spacing.totalLength
	              / Math.max(1, spacing.records.length)
	              * 2
	              / Math.max(1, getChainLinkDimensions(definition).width)
	          ) - 0.58,
	          0.62,
	          0.82
	        )
	      : 1;
	    const breakDelay = definition.id * 0.016;
	    const breakStart = 0.105 + breakDelay * 0.58;
	    const definitionBreakLinear = clamp((intro - breakStart) / 0.05, 0, 1);
	    const definitionBreakOpen = easeOutCubic(definitionBreakLinear);
	    const definitionSnapLinear = clamp((intro - breakStart) / 0.09, 0, 1);
	    const definitionSnapPulse = Math.sin(definitionSnapLinear * Math.PI) ** 0.72;
	    const definitionRecoilUnit = clamp(
	      (intro - (breakStart + 0.018)) / 0.19,
	      0,
	      1
	    );
	    const definitionRecoil = clamp(
	      easeOutCubic(definitionRecoilUnit)
	        + Math.sin(definitionRecoilUnit * Math.PI)
	          * Math.exp(-definitionRecoilUnit * 1.8)
	          * 0.16,
	      0,
	      1.08
	    );
	    const breakDistanceUnit = spacing.distanceAtUnit(definition.breakT);
	    let breakLinkIndex = 0;
	    let nearestBreakDistance = Infinity;
	    for (let index = 0; index < spacing.records.length; index += 1) {
	      const distance = Math.abs(spacing.records[index].distanceUnit - breakDistanceUnit);
	      if (distance < nearestBreakDistance) {
	        nearestBreakDistance = distance;
	        breakLinkIndex = index;
	      }
	    }
	    const travel = easeOutCubic(build);
	    const travelSpan = 1 + definition.entryOverscan;
	    const travelOffset = definition.direction > 0
	      ? travel * travelSpan - travelSpan
	      : travelSpan - travel * travelSpan;
	    const sealMotion = resolveSealMotion(fill, intro);
	    const scrollDrivenFrameFeed = definition.type === "frame"
	      ? smootherstep(phaseProgress(fill, definition.buildEnd, 1)) * 0.46
	      : 0;
	    const tighteningFrameFeed = (
	      sealMotion.takeUp * 0.17
	        + sealMotion.lock * 0.055
	        + sealMotion.lockKick * 0.018
	    ) * (1 - phaseProgress(intro, 0.12, 0.17));
	    const frameDistanceFeed = definition.type === "frame"
	      ? definition.direction * (
	          scrollDrivenFrameFeed + tighteningFrameFeed
	        )
	      : 0;
	    const normalizeFrameDistance = (distanceUnit) => {
	      const wrapped = distanceUnit % 1;
	      return wrapped < 0 ? wrapped + 1 : wrapped;
	    };
	    const breakTravelUnit = definition.type === "frame"
	      ? normalizeFrameDistance(breakDistanceUnit + frameDistanceFeed)
	      : breakDistanceUnit;
	    const breakSample = sampleTitleChainTravel(
	      definition,
	      path,
	      breakTravelUnit,
	      spacing,
	      fill,
	      intro,
	      timestamp
	    );
	    const breakSeed = randomSeed(18001 + definition.id * 47.9);
	    const breakOrder = definition.direction > 0
	      ? breakDistanceUnit
	      : 1 - breakDistanceUnit;
	    const breakHeat = resolveChainHeat(breakOrder, breakSeed);
	    ruptureEvents.push({
	      breakSample,
	      breakSeed,
	      definition,
	      heat: breakHeat,
	      breakOpen: definitionBreakOpen,
	      recoil: definitionRecoil,
	      snapPulse: definitionSnapPulse,
	      releaseFade
	    });
	    const leaderUnit = definition.direction > 0
	      ? -definition.entryOverscan + travel * travelSpan
	      : 1 + definition.entryOverscan - travel * travelSpan;
	    const leaderTravelUnit = leaderUnit
	      + frameDistanceFeed * phaseProgress(build, 0.84, 0.995);
	    const leaderSample = sampleTitleChainTravel(
	      definition,
	      path,
	      leaderTravelUnit,
	      spacing,
	      fill,
	      intro,
	      timestamp
	    );
	    const leaderOrder = definition.direction > 0 ? leaderUnit : 1 - leaderUnit;
	    const leaderHeat = resolveChainHeat(leaderOrder, breakSeed * 0.73);
	    const leaderAlpha = visibility
	      * phaseProgress(build, 0.06, 0.13)
	      * (1 - phaseProgress(build, 0.82, 0.99))
	      * (1 - releaseFade)
	      * resolveCanvasEdgeFade(leaderSample);
	    if (leaderAlpha > 0.002) {
	      leaders.push({
	        definition,
	        sample: leaderSample,
	        alpha: leaderAlpha,
	        heat: leaderHeat
	      });
	    }
	    for (let linkIndex = 0; linkIndex < spacing.records.length; linkIndex += 1) {
	      const { unit, distanceUnit } = spacing.records[linkIndex];
	      let travelUnit = distanceUnit + travelOffset;
	      if (definition.type === "frame") {
	        const feedBlend = phaseProgress(build, 0.84, 1);
	        travelUnit += frameDistanceFeed * feedBlend;
	        if (build >= 0.9995 && Math.abs(travelOffset) <= 0.001) {
	          travelUnit = normalizeFrameDistance(travelUnit);
	        }
	      }
	      if (travelUnit < -0.42 || travelUnit > 1.42) continue;
	      const sample = sampleTitleChainTravel(
	        definition,
	        path,
	        travelUnit,
	        spacing,
	        fill,
	        intro,
	        timestamp
	      );
	      const outside = Math.max(0, -travelUnit, travelUnit - 1);
	      const ingressFade = 1 - smootherstep(clamp((outside - 0.02) / 0.11, 0, 1));
	      let alpha = visibility * phaseProgress(build, 0.02, 0.07) * ingressFade;
	      const order = definition.direction > 0 ? distanceUnit : 1 - distanceUnit;
	      const heatSeed = randomSeed(
	        39019 + definition.id * 191.7 + linkIndex * 29.13
	      );
	      const heat = resolveChainHeat(order, heatSeed);
	      let rotationOffset = 0;
	      let shatterAge = 0;
	      let shatterSide = linkIndex <= breakLinkIndex ? -1 : 1;
	      if (definitionBreakOpen > 0.001) {
	        const side = shatterSide;
	        if (linkIndex === breakLinkIndex) alpha *= Math.max(0, 1 - definitionBreakOpen);
	        const sideSpan = Math.max(
	          0.08,
	          side < 0 ? breakDistanceUnit : 1 - breakDistanceUnit
	        );
	        const distanceFromBreak = Math.abs(distanceUnit - breakDistanceUnit);
	        const shatterOrder = clamp(distanceFromBreak / sideSpan, 0, 1);
	        const shatterSeed = randomSeed(
	          23003
	            + definition.id * 307.1
	            + linkIndex * 43.7
	            + (side > 0 ? 19.3 : 0)
	        );
	        const shatterStart = breakStart
	          + 0.008
	          + shatterOrder * 0.17
	          + shatterSeed * 0.014;
	        shatterAge = clamp((intro - shatterStart) / 0.52, 0, 1);
	        if (shatterAge > 0.001) {
	          const particleAlpha = visibility
	            * phaseProgress(build, 0.02, 0.07)
	            * ingressFade
	            * (1 - releaseFade * 0.34)
	            * resolveCanvasEdgeFade(sample);
	          if (particleAlpha > 0.002) {
	            shatterRecords.push({
	              sample: { ...sample },
	              side,
	              definition,
	              heat,
	              age: shatterAge,
	              seed: shatterSeed + definition.id * 0.137,
	              alpha: particleAlpha
	            });
	          }
	          alpha *= 1 - smootherstep(clamp(shatterAge / 0.035, 0, 1));
	        }
	      }
	      alpha *= (1 - releaseFade * 0.96) * resolveCanvasEdgeFade(sample);
	      const record = {
	        sample,
	        linkIndex,
	        definition,
	        alpha,
	        heat,
	        rotationOffset,
	        scale: definition.type === "frame"
	          ? 0.96 + sample.depth * 0.06
	          : 1,
	        lengthScale: definition.type === "frame" && linkIndex % 2 === 1
	          ? frameConnectorLengthScale
	          : 1,
	        arcMode: "full"
	      };
	      if (sample.crossing) {
	        layerRecords.back.push({ ...record, arcMode: "far" });
	        layerRecords.front.push({ ...record, arcMode: "near" });
	      } else {
	        layerRecords[sample.plane].push(record);
	      }
	    }
	  }

	  const backFrameRecords = layerRecords.back.filter(
	    (record) => record.definition.type === "frame"
	  );
	  const backWeaveRecords = layerRecords.back.filter(
	    (record) => record.definition.type !== "frame"
	  );
	  const frontFrameRecords = layerRecords.front.filter(
	    (record) => record.definition.type === "frame"
	  );
	  const frontWeaveRecords = layerRecords.front.filter(
	    (record) => record.definition.type !== "frame"
	  );
	  drawChainLayer(chainBackContext, backFrameRecords, false);
	  drawChainLayer(chainBackContext, backWeaveRecords, false);
	  drawChainLayer(chainFrontContext, frontWeaveRecords, true);
	  drawChainLayer(chainFrontContext, frontFrameRecords, true);
	  for (const leader of leaders.filter((leader) => leader.definition.type !== "frame")) {
	    drawChainLeader(chainFrontContext, leader);
	  }
	  for (const leader of leaders.filter((leader) => leader.definition.type === "frame")) {
	    drawChainLeader(chainFrontContext, leader);
	  }
	  drawChainShatterParticles(chainFrontContext, shatterRecords, isMobile);
	  drawChainRupture(timestamp, intro, ruptureEvents, visibility, isMobile);
	  drawContractHeartImprint(timestamp, intro, ruptureEvents, visibility, isMobile);

	  chainBackCanvas.style.opacity = Math.min(1, visibility * 0.88).toFixed(3);
	  chainFrontCanvas.style.opacity = Math.min(1, visibility).toFixed(3);
	};

	const resize = (force = false) => {
		if (disposed) return;
		mobilePerformance = window.innerWidth < 680 || window.matchMedia("(pointer: coarse)").matches;
		resizeTitleChains(force);
	};

	const render = (timestamp, frame) => {
		if (disposed) return resolveState(frame.fill, frame.intro);
		chargeIntroProgress = clamp(frame.intro ?? 0, 0, 1);
		burstProgress = clamp(frame.burst ?? 0, 0, 1);
		velocity = frame.velocity ?? 0;
		burstVelocity = frame.burstVelocity ?? 0;
		const fill = clamp(frame.fill ?? 0, 0, 1);
		drawTitleChains(timestamp, fill);
		const state = resolveState(fill, chargeIntroProgress);
		for (const canvas of [chainBackCanvas, chainFrontCanvas]) {
			canvas.dataset.chainProgress = fill.toFixed(3);
			canvas.dataset.chainIntro = chargeIntroProgress.toFixed(3);
			canvas.dataset.chainState = state;
			canvas.dataset.chainSource = "yuimi-direct-port";
		}
		root.dataset.chainSource = "yuimi-direct-port";
		root.dataset.chainState = state;
		return state;
	};

	resize(true);
	return {
		resize,
		render,
		destroy() {
			disposed = true;
			chainLinkUnitCache.clear();
			chainLinkSpriteCache.clear();
			clearTitleChains();
		},
	};
}
