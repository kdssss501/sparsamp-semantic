<script lang="ts">
import { gsap } from "gsap";
import { onMount } from "svelte";
import type { VampireIntroConfig } from "@/config/xiaoConfig";
import { mountVampireChainCanvas } from "../client/vampire-chain-canvas-direct";
import {
	VAMPIRE_INTRO_TIMINGS,
	type VampireIntroPhase,
} from "../model/vampire-intro-timeline";

interface Props {
	config: VampireIntroConfig;
	onReveal: () => void;
	onComplete: (reason: "ended" | "skipped") => void;
}

let { config, onReveal, onComplete }: Props = $props();
let root: HTMLElement;
let video: HTMLVideoElement;
let chainBack: HTMLCanvasElement;
let chainFront: HTMLCanvasElement;
let titleAnchor: HTMLElement;
let phase = $state<VampireIntroPhase>("frames");
let chainState = $state("SEAL CHAINS / DORMANT");
let timeline: gsap.core.Timeline | null = null;
let revealed = false;
let finished = false;
let ready = $state(false);

const clamp = (value: number) => Math.min(1, Math.max(0, value));

function reveal() {
	if (revealed) return;
	revealed = true;
	phase = "revealed";
	onReveal();
}

function finish(reason: "ended" | "skipped") {
	if (finished) return;
	finished = true;
	if (reason === "skipped") reveal();
	timeline?.kill();
	timeline = null;
	video?.pause();
	phase = "complete";
	onComplete(reason);
}

onMount(() => {
	ready = true;
	const staticLayer = root.querySelector<HTMLElement>("[data-static-layer]");
	const titleStage = root.querySelector<HTMLElement>("[data-title-stage]");
	const title = root.querySelector<HTMLElement>("[data-intro-title]");
	const status = root.querySelector<HTMLElement>("[data-chain-status]");
	const flash = root.querySelector<HTMLElement>("[data-intro-flash]");
	const controller = mountVampireChainCanvas({
		back: chainBack,
		front: chainFront,
		root,
		anchor: titleAnchor,
	});
	const resizeObserver = new ResizeObserver(() => controller.resize());
	resizeObserver.observe(root);
	resizeObserver.observe(titleAnchor);
	void video.play().catch(() => {
		if (root?.isConnected && !finished) root.dataset.videoAutoplay = "blocked";
	});

	const context = gsap.context(() => {
		gsap.set(titleStage, { autoAlpha: 0, scale: 1.08 });
		gsap.set([status], { autoAlpha: 0 });
		gsap.set(flash, { autoAlpha: 0 });

		timeline = gsap.timeline({
			defaults: { ease: "power3.out" },
			onUpdate: () => {
				if (!root?.isConnected || finished) return;
				const elapsedMs = Math.round((timeline?.time() ?? 0) * 1_000);
				root.dataset.introElapsedMs = String(elapsedMs);
				const chainStart = VAMPIRE_INTRO_TIMINGS.titleEndMs;
				const sealStart = VAMPIRE_INTRO_TIMINGS.chainEndMs;
				const fill = clamp(
					(elapsedMs - chainStart) / Math.max(1, sealStart - chainStart),
				);
				const intro =
					clamp(
						(elapsedMs - sealStart) /
							Math.max(1, config.revealAtMs - sealStart),
					) * 0.94;
				const postReveal = clamp((elapsedMs - config.revealAtMs) / 620);
				const resolvedIntro = Math.min(1, intro + postReveal * 0.06);
				const burstDuration = Math.max(
					1,
					VAMPIRE_INTRO_TIMINGS.exitMs - config.revealAtMs - 280,
				);
				const burst = clamp(
					(elapsedMs - config.revealAtMs - 280) / burstDuration,
				);
				const fillVelocity =
					elapsedMs >= chainStart && elapsedMs <= sealStart
						? 1 / Math.max(1, sealStart - chainStart)
						: 0;
				chainState = controller.render(performance.now(), {
					fill,
					intro: resolvedIntro,
					burst,
					velocity: fillVelocity,
					burstVelocity: burst > 0 && burst < 1 ? 1 / burstDuration : 0,
				});
				root.dataset.chainState = chainState;
				const introEnchant = clamp((resolvedIntro - 0.02) / 0.7);
				const glossSweep = clamp((burst - 0.01) / 0.29);
				const glossOpacity =
					Math.sin(glossSweep * Math.PI) *
					(1 - clamp((burst - 0.3) / 0.18)) *
					0.98;
				const boundaryOpacity =
					fill <= 0.002 || fill >= 0.998
						? 0
						: Math.min(
								0.74,
								0.38 +
									Math.sin(fill * Math.PI) * 0.1 +
									Math.abs(fillVelocity) * 24,
							);
				const gateState =
					elapsedMs < chainStart
						? "idle"
						: elapsedMs < sealStart
							? "charging"
							: elapsedMs < config.revealAtMs
								? "sealing"
								: elapsedMs < VAMPIRE_INTRO_TIMINGS.exitMs
									? "release"
									: "opening";
				root.dataset.gateState = gateState;
				root.style.setProperty("--kisara-fill", `${(fill * 100).toFixed(3)}%`);
				root.style.setProperty(
					"--kisara-tide-opacity",
					fill > 0.002 ? "1" : "0",
				);
				root.style.setProperty(
					"--kisara-tide-energy-opacity",
					(0.025 + fill * 0.38).toFixed(4),
				);
				root.style.setProperty(
					"--kisara-tide-brightness",
					(0.76 + fill * 0.34).toFixed(4),
				);
				root.style.setProperty(
					"--kisara-tide-saturation",
					(0.68 + fill * 0.52).toFixed(4),
				);
				root.style.setProperty(
					"--kisara-boundary-opacity",
					boundaryOpacity.toFixed(3),
				);
				root.style.setProperty(
					"--kisara-boundary-offset",
					`${Math.min(1.45, fillVelocity * 320).toFixed(3)}%`,
				);
				root.style.setProperty(
					"--kisara-enchant-progress",
					introEnchant.toFixed(4),
				);
				root.style.setProperty(
					"--kisara-enchant-opacity",
					clamp((resolvedIntro - 0.02) / 0.35).toFixed(3),
				);
				root.style.setProperty(
					"--kisara-enchant-pulse",
					Math.max(0, Math.sin(resolvedIntro * Math.PI * 4)).toFixed(3),
				);
				root.style.setProperty(
					"--kisara-enchant-flow",
					`${(resolvedIntro * 240).toFixed(3)}%`,
				);
				root.style.setProperty(
					"--kisara-gloss-position",
					`${(118 - glossSweep * 136).toFixed(3)}%`,
				);
				root.style.setProperty(
					"--kisara-gloss-opacity",
					glossOpacity.toFixed(3),
				);
			},
			onComplete: () => finish("ended"),
		});

		timeline
			.fromTo(
				video,
				{ scale: 1.035 },
				{ scale: 1.09, duration: 4.6, ease: "none" },
				0,
			)
			.to(
				video,
				{
					filter: "contrast(1.3) saturate(.64) brightness(.64)",
					duration: 0.18,
				},
				2.48,
			)
			.to(
				video,
				{
					filter: "contrast(1.08) saturate(.78) brightness(.72)",
					duration: 0.24,
				},
				2.66,
			)
			.call(
				() => (phase = "title"),
				[],
				VAMPIRE_INTRO_TIMINGS.framesEndMs / 1_000,
			)
			.to(
				titleStage,
				{ autoAlpha: 1, scale: 1, duration: 0.52 },
				VAMPIRE_INTRO_TIMINGS.framesEndMs / 1_000,
			)
			.fromTo(
				title,
				{ filter: "blur(8px) brightness(1.8)" },
				{ filter: "blur(0px) brightness(1)", duration: 0.44 },
				4.62,
			)
			.to(
				title,
				{ x: 8, duration: 0.045, repeat: 5, yoyo: true, ease: "steps(1)" },
				5.34,
			)
			.call(
				() => (phase = "chain"),
				[],
				VAMPIRE_INTRO_TIMINGS.titleEndMs / 1_000,
			)
			.to(
				status,
				{ autoAlpha: 1, duration: 0.18 },
				VAMPIRE_INTRO_TIMINGS.titleEndMs / 1_000,
			)
			.to(
				titleStage,
				{
					scaleX: 0.965,
					duration: 0.18,
					repeat: 1,
					yoyo: true,
					ease: "power4.inOut",
				},
				7.2,
			)
			.call(
				() => (phase = "locked"),
				[],
				VAMPIRE_INTRO_TIMINGS.chainEndMs / 1_000,
			)
			.to(
				flash,
				{ autoAlpha: 0.35, duration: 0.055, repeat: 1, yoyo: true },
				8.2,
			)
			.to(
				title,
				{ filter: "brightness(.72) contrast(1.2)", duration: 1.7 },
				8.55,
			)
			.to(flash, { autoAlpha: 0.96, duration: 0.12, ease: "power4.in" }, 10.64)
			.call(reveal, [], config.revealAtMs / 1_000)
			.set(staticLayer, { autoAlpha: 0 }, config.revealAtMs / 1_000)
			.to(flash, { autoAlpha: 0, duration: 0.48 }, config.revealAtMs / 1_000)
			.to(
				title,
				{ x: -7, duration: 0.055, repeat: 5, yoyo: true, ease: "steps(1)" },
				11.76,
			)
			.call(() => (phase = "exit"), [], VAMPIRE_INTRO_TIMINGS.exitMs / 1_000)
			.to(
				[titleStage, status],
				{
					autoAlpha: 0,
					y: -18,
					filter: "blur(8px)",
					duration: 1.35,
					ease: "power2.in",
				},
				VAMPIRE_INTRO_TIMINGS.exitMs / 1_000,
			)
			.to(root, { autoAlpha: 0, duration: 0.45, ease: "power2.in" }, 14.55);
	}, root);

	return () => {
		finished = true;
		video.pause();
		timeline?.kill();
		timeline = null;
		resizeObserver.disconnect();
		controller.destroy();
		context.revert();
	};
});
</script>

<div bind:this={root} class="vampire-intro" data-vampire-intro data-intro-phase={phase} data-chain-source="yuimi-direct-port" role="dialog" aria-label="吸血鬼片头">
	<div class="vampire-intro__static" data-static-layer aria-hidden="true">
		<img class="vampire-intro__poster" src={config.posterPath} alt="" />
		<video bind:this={video} class="vampire-intro__video" data-intro-video src={config.videoPath} poster={config.posterPath} muted autoplay playsinline preload="auto"></video>
		<div class="vampire-intro__vignette"></div>
	</div>
	<div class="vampire-intro__chromatic" aria-hidden="true"></div>
	<div class="vampire-intro__scanlines" aria-hidden="true"></div>
	<div class="kisara-title-stage" data-title-stage>
		<span class="kisara-title-reset-underlay kisara-title-base" aria-hidden="true">VAMPIRE</span>
		<h1 id="vampire-intro-title" class="kisara-title" data-intro-title aria-label="VAMPIRE">
			<canvas bind:this={chainBack} class="kisara-title-chain-canvas kisara-title-chain-canvas-back" data-chain-canvas="back" width="1400" height="420" aria-hidden="true"></canvas>
			<span bind:this={titleAnchor} class="kisara-title-base" aria-hidden="true">VAMPIRE</span>
			<span class="kisara-title-tide" aria-hidden="true">VAMPIRE</span>
			<canvas bind:this={chainFront} class="kisara-title-chain-canvas kisara-title-chain-canvas-front" data-chain-canvas="front" width="1400" height="420" aria-hidden="true"></canvas>
			<span class="kisara-title-enchant" aria-hidden="true">VAMPIRE</span>
			<span class="kisara-title-gloss" aria-hidden="true">VAMPIRE</span>
		</h1>
	</div>
	<p class="kisara-contract-state" data-chain-status aria-hidden="true">{chainState}</p>
	<div class="vampire-intro__flash" data-intro-flash aria-hidden="true"></div>
	<button type="button" class="kisara-gate-skip" onclick={() => finish("skipped")} disabled={!ready}>跳过</button>
</div>

<style>
.vampire-intro {
	--kisara-fill: 0%;
	--kisara-gloss-position: -18%;
	--kisara-gloss-opacity: 0;
	--kisara-enchant-progress: 0;
	--kisara-enchant-opacity: 0;
	--kisara-enchant-pulse: 0;
	--kisara-enchant-flow: 0%;
	--kisara-tide-energy-opacity: 0.025;
	--kisara-tide-brightness: 0.76;
	--kisara-tide-saturation: 0.68;
	--kisara-boundary-opacity: 0;
	--kisara-boundary-offset: 0%;
	--kisara-title-impact-x: 0px;
	--kisara-title-impact-y: 0px;
	--kisara-title-source-opacity: 1;
	--kisara-title-blur: 0px;
	--kisara-screen-shake-x: 0px;
	--kisara-screen-shake-y: 0px;
	--kisara-impact-scale: 1;
	--kisara-warning-monochrome: 0;
	--kisara-warning-saturation: 1;
	--kisara-warning-contrast: 1;
	--kisara-warning-brightness: 1;
	--kisara-title-return-current-opacity: 1;
	--kisara-title-return-underlay-opacity: 0;
	--kisara-title-return-blur: 0px;
	--kisara-title-return-saturation: 1;
	position: absolute;
	z-index: 120;
	inset: 0;
	display: grid;
	place-items: center;
	align-content: center;
	box-sizing: border-box;
	min-height: 100%;
	padding: 110px 24px 70px;
	overflow: hidden;
	isolation: isolate;
	background: transparent;
	color: #f7f3f4;
	font-family: Georgia, "Times New Roman", serif;
}

.vampire-intro__static,
.vampire-intro__poster,
.vampire-intro__video,
.vampire-intro__vignette,
.vampire-intro__chromatic,
.vampire-intro__scanlines,
.vampire-intro__flash {
	position: absolute;
	inset: 0;
}

.vampire-intro__static { z-index: 0; overflow: hidden; background: #030205; }
.vampire-intro__poster,
.vampire-intro__video { display: block; width: 100%; height: 100%; object-fit: cover; object-position: center; }
.vampire-intro__poster { filter: brightness(0.64) contrast(1.1); }
.vampire-intro__video { filter: contrast(1.08) saturate(0.78) brightness(0.72); will-change: transform, filter; }
.vampire-intro__vignette { background: radial-gradient(circle at 50% 46%, transparent 20%, rgb(2 0 4 / 35%) 62%, rgb(0 0 0 / 92%) 100%); box-shadow: inset 0 0 18vmax rgb(0 0 0 / 58%); }
.vampire-intro__chromatic { z-index: 1; pointer-events: none; background: linear-gradient(90deg, rgb(26 107 145 / 14%), transparent 42% 58%, rgb(187 22 71 / 16%)); mix-blend-mode: screen; }
.vampire-intro__scanlines { z-index: 8; pointer-events: none; opacity: 0.12; background-image: linear-gradient(transparent 0 2px, rgb(0 0 0 / 55%) 2px 3px, transparent 3px); background-size: 100% 4px; }
.vampire-intro__flash { z-index: 20; pointer-events: none; background: #f3edf0; opacity: 0; }

.kisara-title-stage {
  position: relative;
  display: grid;
  place-items: center;
  isolation: isolate;
  font-family: Georgia, "Times New Roman", serif;
  font-size: clamp(3.15rem, 12vw, 11rem);
  font-weight: 700;
  line-height: 0.86;
  letter-spacing: 0;
}

.kisara-title-stage > .kisara-title,
.kisara-title-stage > .kisara-title-reset-underlay {
  grid-area: 1 / 1;
}

.kisara-title {
  position: relative;
  z-index: 1;
  display: grid;
  isolation: isolate;
  margin: 0;
  font: inherit;
  letter-spacing: 0;
  opacity: var(--kisara-title-return-current-opacity);
  transform: translate3d(
      calc(var(--kisara-screen-shake-x) + var(--kisara-title-impact-x)),
      calc(var(--kisara-screen-shake-y) + var(--kisara-title-impact-y)),
      0
    )
    scale(var(--kisara-impact-scale));
  transform-origin: 50% 50%;
  filter:
    grayscale(var(--kisara-warning-monochrome))
    saturate(var(--kisara-warning-saturation))
    contrast(var(--kisara-warning-contrast))
    brightness(var(--kisara-warning-brightness))
    blur(var(--kisara-title-return-blur))
    saturate(var(--kisara-title-return-saturation));
  will-change: transform, filter, opacity;
}

.kisara-title > span,
.kisara-title-reset-underlay {
  position: relative;
  z-index: 1;
  grid-area: 1 / 1;
  display: block;
  opacity: var(--kisara-title-source-opacity);
  color: transparent;
  -webkit-text-fill-color: transparent;
  background-color: transparent;
  -webkit-text-stroke: 2px rgba(235, 239, 255, 0.24);
  background-clip: text;
  -webkit-background-clip: text;
  filter: blur(var(--kisara-title-blur));
  -webkit-filter: blur(var(--kisara-title-blur));
  text-shadow: 0 12px 30px rgba(5, 8, 28, 0.4);
  transition: text-shadow 260ms ease, transform 260ms ease;
  will-change: transform, filter;
}

.kisara-title-base {
  background-image:
    linear-gradient(
      45deg,
      transparent 0%,
      transparent calc(var(--kisara-fill) - 2%),
      rgba(15, 20, 35, 0.1) calc(var(--kisara-fill) + 1.5%),
      rgba(11, 16, 30, 0.34) calc(var(--kisara-fill) + 5.5%),
      rgba(36, 42, 57, 0.16) calc(var(--kisara-fill) + 9%),
      transparent calc(var(--kisara-fill) + 13%),
      transparent 100%
    ),
    radial-gradient(ellipse at 17% 18%, rgba(207, 218, 228, 0.12) 0 1%, transparent 5.8%),
    radial-gradient(ellipse at 74% 72%, rgba(18, 27, 48, 0.31) 0 1.8%, transparent 7%),
    linear-gradient(
      121deg,
      transparent 0 13%,
      rgba(13, 20, 35, 0.25) 13.4% 15.1%,
      transparent 15.7% 37%,
      rgba(192, 203, 216, 0.055) 37.5% 38%,
      transparent 38.6% 61%,
      rgba(25, 34, 52, 0.22) 61.5% 62.8%,
      transparent 63.4% 78%,
      rgba(178, 190, 207, 0.045) 78.4% 79%,
      transparent 79.6% 100%
    ),
    repeating-linear-gradient(
      103deg,
      rgba(216, 226, 236, 0.025) 0 1px,
      rgba(19, 27, 46, 0.105) 1px 2px,
      transparent 2px 11px
    ),
    repeating-linear-gradient(
      1deg,
      rgba(218, 226, 235, 0.015) 0 1px,
      rgba(20, 29, 47, 0.07) 1px 2px,
      transparent 2px 10px
    ),
    linear-gradient(
      180deg,
      rgba(166, 177, 191, 0.82) 0%,
      rgba(109, 123, 145, 0.84) 38%,
      rgba(68, 81, 107, 0.87) 72%,
      rgba(43, 52, 73, 0.91) 100%
    );
  background-size: 100% 100%, 128% 118%, 118% 126%, 100% 100%, 15px 100%, 100% 11px, 100% 100%;
  background-position: 0 0, 6% 0, 62% 18%, 0 0, 0 0, 0 0, 0 0;
  background-blend-mode: multiply, screen, multiply, multiply, soft-light, multiply, normal;
  -webkit-text-stroke-color: rgba(176, 188, 207, 0.12);
  filter: blur(var(--kisara-title-blur)) saturate(0.52) brightness(0.8) contrast(0.94);
  -webkit-filter: blur(var(--kisara-title-blur)) saturate(0.52) brightness(0.8) contrast(0.94);
  text-shadow: 0 10px 24px rgba(4, 7, 18, 0.3);
}

.kisara-title-reset-underlay {
  z-index: 0;
  --kisara-fill: 0%;
  --kisara-title-blur: 0px;
  --kisara-title-source-opacity: 1;
  opacity: var(--kisara-title-return-underlay-opacity);
  pointer-events: none;
}

.kisara-gate:is(
  .is-opening-title-bridge-dissolving,
  .is-opening-title-bridge-handoff
) .kisara-title-reset-underlay {
  will-change: opacity;
}

.kisara-title-tide {
  pointer-events: none;
  -webkit-mask-repeat: no-repeat;
  mask-repeat: no-repeat;
  -webkit-mask-position: 0 0;
  mask-position: 0 0;
  -webkit-mask-size: 100% 100%;
  mask-size: 100% 100%;
  -webkit-mask-mode: alpha;
  mask-mode: alpha;
}

.kisara-title > .kisara-title-tide {
  position: relative;
  opacity: min(var(--kisara-tide-opacity, 0), var(--kisara-title-source-opacity));
  background-image:
    radial-gradient(ellipse at 18% 19%, rgba(255, 218, 207, 0.22) 0 0.9%, transparent 4.6%),
    radial-gradient(ellipse at 72% 68%, rgba(42, 3, 18, 0.24) 0 1.2%, transparent 5.4%),
    linear-gradient(
      124deg,
      transparent 0 19%,
      rgba(255, 218, 210, 0.13) 19.4% 20.1%,
      transparent 20.7% 46%,
      rgba(45, 3, 20, 0.2) 46.5% 47.3%,
      transparent 47.9% 69%,
      rgba(232, 149, 157, 0.095) 69.4% 70.1%,
      transparent 70.7% 100%
    ),
    radial-gradient(
      ellipse at 43% 57%,
      rgba(181, 52, 79, 0.14) 0 4%,
      rgba(96, 19, 44, 0.08) 8%,
      transparent 17%
    ),
    conic-gradient(
      from 198deg at 35% 54%,
      transparent 0 43%,
      rgba(43, 3, 20, 0.24) 45% 50%,
      transparent 52% 75%,
      rgba(211, 112, 123, 0.075) 77% 81%,
      transparent 83% 100%
    ),
    conic-gradient(
      from 24deg at 78% 39%,
      transparent 0 60%,
      rgba(131, 35, 60, 0.2) 62% 70%,
      transparent 73% 100%
    ),
    linear-gradient(
      171deg,
      transparent 0 28%,
      rgba(255, 205, 198, 0.045) 30% 31.5%,
      transparent 33% 61%,
      rgba(41, 3, 19, 0.18) 63% 68%,
      transparent 70% 100%
    ),
    linear-gradient(
      180deg,
      rgba(143, 83, 94, 0.99) 0%,
      rgba(119, 43, 63, 1) 39%,
      rgba(82, 20, 42, 1) 72%,
      rgba(47, 7, 25, 1) 100%
    );
  background-size: 126% 116%, 118% 124%, 100% 100%, 100% 100%, 100% 100%, 100% 100%, 100% 100%, 100% 100%;
  background-position: 8% 0, 58% 22%, 0 0, 0 0, 0 0, 0 0, 0 0, 0 0;
  background-repeat: no-repeat;
  background-blend-mode: screen, multiply, soft-light, screen, multiply, soft-light, multiply, normal;
  -webkit-text-stroke-color: transparent;
  filter:
    brightness(var(--kisara-tide-brightness))
    saturate(var(--kisara-tide-saturation));
  -webkit-filter:
    brightness(var(--kisara-tide-brightness))
    saturate(var(--kisara-tide-saturation));
  text-shadow: none;
  -webkit-mask-image: linear-gradient(
    45deg,
    #000 0%,
    #000 calc(var(--kisara-fill) - 6.5%),
    rgba(0, 0, 0, 0.96) calc(var(--kisara-fill) - 3.8%),
    rgba(0, 0, 0, 0.8) calc(var(--kisara-fill) - 1.1%),
    rgba(0, 0, 0, 0.52) calc(var(--kisara-fill) + 1.5%),
    rgba(0, 0, 0, 0.2) calc(var(--kisara-fill) + 4.1%),
    transparent calc(var(--kisara-fill) + 6.8%),
    transparent 100%
  );
  mask-image: linear-gradient(
    45deg,
    #000 0%,
    #000 calc(var(--kisara-fill) - 6.5%),
    rgba(0, 0, 0, 0.96) calc(var(--kisara-fill) - 3.8%),
    rgba(0, 0, 0, 0.8) calc(var(--kisara-fill) - 1.1%),
    rgba(0, 0, 0, 0.52) calc(var(--kisara-fill) + 1.5%),
    rgba(0, 0, 0, 0.2) calc(var(--kisara-fill) + 4.1%),
    transparent calc(var(--kisara-fill) + 6.8%),
    transparent 100%
  );
}

.kisara-title-tide::before,
.kisara-title-tide::after {
  content: "VAMPIRE";
  position: absolute;
  inset: 0;
  display: block;
  pointer-events: none;
  color: transparent;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  -webkit-background-clip: text;
}

.kisara-title-tide::before {
  background-image:
    radial-gradient(ellipse at 34% 16%, rgba(255, 226, 220, 0.2) 0 1%, transparent 5.4%),
    radial-gradient(
      ellipse at 64% 68%,
      rgba(226, 63, 91, 0.14) 0 4%,
      rgba(122, 18, 49, 0.09) 8%,
      transparent 16%
    ),
    linear-gradient(
      122deg,
      transparent 0 34%,
      rgba(255, 214, 218, 0.12) 39%,
      transparent 45% 100%
    ),
    conic-gradient(
      from 214deg at 47% 51%,
      transparent 0 42%,
      rgba(255, 181, 187, 0.12) 44% 47%,
      transparent 49% 70%,
      rgba(111, 12, 44, 0.18) 72% 75%,
      transparent 77% 100%
    ),
    linear-gradient(180deg, #d9909b 0%, #bd3f5e 54%, #831d3d 100%);
  background-size: 122% 112%, 100% 100%, 100% 100%, 100% 100%, 100% 100%;
  background-position: 10% 0, 0 0, 0 0, 0 0, 0 0;
  background-repeat: no-repeat;
  background-blend-mode: screen, screen, soft-light, soft-light, normal;
  opacity: var(--kisara-tide-energy-opacity);
  filter: none;
  -webkit-filter: none;
  text-shadow: none;
  will-change: opacity;
}

.kisara-title-tide::after {
  background-image:
    conic-gradient(
      from 26deg at 50% 50%,
      transparent 0 67%,
      rgba(156, 45, 71, 0.68) 70% 78%,
      transparent 81% 100%
    ),
    conic-gradient(
      from 211deg at 50% 50%,
      transparent 0 70%,
      rgba(68, 55, 87, 0.52) 73% 82%,
      transparent 85% 100%
    ),
    conic-gradient(
      from 142deg at 50% 50%,
      transparent 0 65%,
      rgba(178, 57, 78, 0.56) 68% 75%,
      transparent 78% 100%
    ),
    conic-gradient(
      from 304deg at 50% 50%,
      transparent 0 72%,
      rgba(55, 39, 67, 0.46) 75% 83%,
      transparent 86% 100%
    ),
    conic-gradient(
      from 72deg at 50% 50%,
      transparent 0 68%,
      rgba(139, 43, 67, 0.58) 71% 79%,
      transparent 82% 100%
    ),
    linear-gradient(
      113deg,
      transparent 0 17%,
      rgba(171, 55, 78, 0.34) 18.2% 19.4%,
      transparent 20.6% 41%,
      rgba(72, 55, 88, 0.28) 42.3% 43.2%,
      transparent 44.5% 69%,
      rgba(158, 47, 72, 0.3) 70.3% 71.6%,
      transparent 73% 100%
    ),
    linear-gradient(
      31deg,
      transparent 0 29%,
      rgba(87, 66, 99, 0.26) 30.5% 31.4%,
      transparent 32.8% 54%,
      rgba(163, 50, 74, 0.28) 55.2% 56.5%,
      transparent 58% 81%,
      rgba(54, 39, 69, 0.24) 82.2% 83.2%,
      transparent 84.5% 100%
    );
  background-size: 18% 42%, 20% 34%, 17% 46%, 22% 38%, 16% 40%, 100% 100%, 100% 100%;
  background-position:
    5% 38%,
    24% 19%,
    43% 48%,
    62% 25%,
    82% 41%,
    0 0,
    0 0;
  background-repeat: no-repeat;
  background-blend-mode: normal, multiply, normal, multiply, normal, soft-light, multiply;
  opacity: var(--kisara-boundary-opacity);
  mix-blend-mode: normal;
  filter: none;
  -webkit-filter: none;
  text-shadow: none;
  -webkit-mask-image: linear-gradient(
    45deg,
    transparent 0%,
    transparent calc(var(--kisara-fill) + var(--kisara-boundary-offset) - 10%),
    rgba(0, 0, 0, 0.24) calc(var(--kisara-fill) + var(--kisara-boundary-offset) - 8%),
    rgba(0, 0, 0, 0.88) calc(var(--kisara-fill) + var(--kisara-boundary-offset) - 5.4%),
    #000 calc(var(--kisara-fill) + var(--kisara-boundary-offset) - 2.2%),
    rgba(0, 0, 0, 0.7) calc(var(--kisara-fill) + var(--kisara-boundary-offset) + 0.8%),
    rgba(0, 0, 0, 0.18) calc(var(--kisara-fill) + var(--kisara-boundary-offset) + 3.6%),
    transparent calc(var(--kisara-fill) + var(--kisara-boundary-offset) + 6.2%),
    transparent 100%
  );
  mask-image: linear-gradient(
    45deg,
    transparent 0%,
    transparent calc(var(--kisara-fill) + var(--kisara-boundary-offset) - 10%),
    rgba(0, 0, 0, 0.24) calc(var(--kisara-fill) + var(--kisara-boundary-offset) - 8%),
    rgba(0, 0, 0, 0.88) calc(var(--kisara-fill) + var(--kisara-boundary-offset) - 5.4%),
    #000 calc(var(--kisara-fill) + var(--kisara-boundary-offset) - 2.2%),
    rgba(0, 0, 0, 0.7) calc(var(--kisara-fill) + var(--kisara-boundary-offset) + 0.8%),
    rgba(0, 0, 0, 0.18) calc(var(--kisara-fill) + var(--kisara-boundary-offset) + 3.6%),
    transparent calc(var(--kisara-fill) + var(--kisara-boundary-offset) + 6.2%),
    transparent 100%
  );
}

.kisara-title > .kisara-title-enchant {
  z-index: 3;
  opacity: min(var(--kisara-enchant-opacity, 0), var(--kisara-title-source-opacity));
  color: transparent;
  -webkit-text-fill-color: transparent;
  background-image:
    linear-gradient(
      112deg,
      transparent 31%,
      rgba(126, 170, 255, 0.38) 41%,
      rgba(255, 235, 244, 0.94) 48%,
      rgba(255, 255, 255, 1) 50%,
      rgba(255, 76, 136, 0.9) 54%,
      rgba(255, 75, 137, 0.28) 62%,
      transparent 71%
    ),
    repeating-linear-gradient(
      112deg,
      rgba(255, 255, 255, 0) 0 7%,
      rgba(255, 244, 248, 0.92) 8% 9.2%,
      rgba(255, 77, 135, 0.46) 10.2% 12.5%,
      rgba(255, 255, 255, 0) 14% 22%
    ),
    linear-gradient(180deg, #fff8fb 0%, #ff7da1 48%, #7fa8ff 100%);
  background-size: 100% 100%, 240% 100%, 100% 100%;
  background-position: center, var(--kisara-enchant-flow, 0%) 50%, center;
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-stroke: 1px rgba(255, 236, 244, 0.62);
  clip-path: circle(calc(4% + var(--kisara-enchant-progress, 0) * 126%) at 53% 57%);
  mix-blend-mode: screen;
  filter: none;
  -webkit-filter: none;
  text-shadow:
    0 0 calc(5px + var(--kisara-enchant-pulse, 0) * 7px) rgba(255, 246, 250, 0.94),
    0 0 calc(14px + var(--kisara-enchant-pulse, 0) * 20px) rgba(255, 55, 121, 0.72),
    0 0 calc(24px + var(--kisara-enchant-pulse, 0) * 28px) rgba(103, 151, 255, 0.46);
  will-change: opacity, clip-path, background-position;
}

.kisara-title > .kisara-title-gloss {
  z-index: 4;
  opacity: var(--kisara-gloss-opacity, 0);
  color: transparent;
  -webkit-text-fill-color: transparent;
  background-color: transparent;
  background-image: linear-gradient(
    180deg,
    #ffffff 0%,
    #fff8fb 38%,
    #ffb0c2 72%,
    #ff7894 100%
  );
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-stroke: 1px rgba(255, 255, 255, 0.72);
  clip-path: polygon(
    calc(var(--kisara-gloss-position, -18%) - 9%) 100%,
    calc(var(--kisara-gloss-position, -18%) + 2%) 100%,
    calc(var(--kisara-gloss-position, -18%) + 11%) 0%,
    var(--kisara-gloss-position, -18%) 0%
  );
  mix-blend-mode: screen;
  filter: none;
  -webkit-filter: none;
  text-shadow: 0 0 10px rgba(255, 247, 250, 0.98), 0 0 26px rgba(255, 82, 117, 0.78);
  transition: opacity 120ms linear;
  will-change: opacity, clip-path;
}

.kisara-title-chain-canvas {
  position: absolute;
  inset: -38% -32%;
  width: 164%;
  height: 176%;
  pointer-events: none;
  opacity: 0;
  transform: translateZ(0);
  -webkit-mask-image: linear-gradient(
    90deg,
    transparent 0,
    #000 8%,
    #000 92%,
    transparent 100%
  );
  mask-image: linear-gradient(
    90deg,
    transparent 0,
    #000 8%,
    #000 92%,
    transparent 100%
  );
  will-change: opacity, transform;
}

.kisara-title-chain-canvas-back {
  z-index: 0;
  filter:
    saturate(0.82)
    brightness(0.7)
    drop-shadow(0 4px 8px rgba(5, 7, 29, 0.64));
}

.kisara-title-chain-canvas-front {
  z-index: 5;
  filter:
    saturate(0.9)
    contrast(1.12)
    drop-shadow(0 5px 9px rgba(7, 8, 28, 0.72));
}

.kisara-title-stage {
	z-index: 5;
	transform: translateY(-3px);
	text-shadow: 0 14px 34px rgba(255, 54, 95, 0.2);
	pointer-events: none;
}

.kisara-contract-state {
	z-index: 7;
	margin: 30px 0 0;
	min-width: 20ch;
	width: min(42ch, calc(100vw - 48px));
	max-width: calc(100vw - 48px);
	min-height: 1.2em;
	overflow: hidden;
	color: #ff7891;
	font: 800 0.7rem/1.2 "Courier New", Courier, monospace;
	letter-spacing: 0;
	text-align: center;
	text-overflow: clip;
	white-space: nowrap;
	text-shadow: 0 0 12px rgba(255, 77, 113, 0.5);
	pointer-events: none;
}

.kisara-gate-skip {
	position: absolute;
	z-index: 30;
	right: max(48px, env(safe-area-inset-right));
	bottom: max(28px, env(safe-area-inset-bottom));
	padding: 5px 0;
	border: 0;
	border-bottom: 1px solid rgba(170, 190, 242, 0.48);
	background: transparent;
	color: rgba(170, 190, 242, 0.62);
	font: 800 0.66rem/1 Arial, sans-serif;
	opacity: 0.72;
	isolation: isolate;
	cursor: pointer;
	transition: color 180ms ease, border-color 180ms ease, opacity 180ms ease, filter 180ms ease;
	animation: kisara-skip-breathe 2.8s ease-in-out infinite;
}
.kisara-gate-skip::after { content: ""; position: absolute; z-index: -1; right: -4px; bottom: -1px; left: -4px; height: 1px; background: linear-gradient(90deg, transparent, rgba(255, 120, 145, 0.95), transparent); opacity: 0; transform: translateX(-24%) scaleX(0.22); transform-origin: center; animation: kisara-skip-scan 2.8s ease-in-out infinite; pointer-events: none; }
.kisara-gate-skip:hover,
.kisara-gate-skip:focus-visible { color: #ff7891; border-bottom-color: rgba(255, 120, 145, 0.82); opacity: 1; outline: 0; filter: drop-shadow(0 0 8px rgba(255, 120, 145, 0.48)); animation-play-state: paused; }
.kisara-gate-skip:disabled { cursor: wait; opacity: 0.45; }

@keyframes kisara-skip-breathe {
	0%, 100% { opacity: 0.62; filter: drop-shadow(0 0 0 rgba(255, 120, 145, 0)); }
	50% { opacity: 0.94; filter: drop-shadow(0 0 7px rgba(255, 120, 145, 0.34)); }
}
@keyframes kisara-skip-scan {
	0%, 18% { opacity: 0; transform: translateX(-24%) scaleX(0.22); }
	42% { opacity: 0.82; }
	72%, 100% { opacity: 0; transform: translateX(24%) scaleX(0.72); }
}

@media (max-width: 480px) {
	.vampire-intro { padding-inline: 12px; }
	.kisara-title-stage { font-size: clamp(2.85rem, 13vw, 3.25rem); }
	.kisara-contract-state { margin-top: 22px; font-size: 0.61rem; }
	.kisara-gate-skip { right: 24px; bottom: max(78px, calc(58px + env(safe-area-inset-bottom))); }
}

@media (prefers-reduced-motion: reduce) {
	.vampire-intro { display: none; }
}
</style>
