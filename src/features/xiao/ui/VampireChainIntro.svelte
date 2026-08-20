<script lang="ts">
import { onMount } from "svelte";
import { gsap } from "gsap";
import type { VampireIntroConfig } from "@/config/xiaoConfig";
import { mountVampireChainCanvas } from "../client/vampire-chain-canvas-direct";
import { VAMPIRE_INTRO_TIMINGS, type VampireIntroPhase } from "../model/vampire-intro-timeline";

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
	const subtitle = root.querySelector<HTMLElement>("[data-intro-subtitle]");
	const status = root.querySelector<HTMLElement>("[data-chain-status]");
	const flash = root.querySelector<HTMLElement>("[data-intro-flash]");
	const controller = mountVampireChainCanvas({ back: chainBack, front: chainFront, root, anchor: titleAnchor });
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
				const fill = clamp((elapsedMs - chainStart) / Math.max(1, sealStart - chainStart));
				const intro = clamp((elapsedMs - sealStart) / Math.max(1, config.revealAtMs - sealStart)) * 0.94;
				const postReveal = clamp((elapsedMs - config.revealAtMs) / 620);
				const resolvedIntro = Math.min(1, intro + postReveal * 0.06);
				const burst = clamp((elapsedMs - config.revealAtMs - 280) / 700) * 0.05;
				chainState = controller.render(performance.now(), {
					fill,
					intro: resolvedIntro,
					burst,
					velocity: elapsedMs >= chainStart && elapsedMs <= sealStart ? 1 / Math.max(1, sealStart - chainStart) : 0,
					burstVelocity: postReveal > 0 && postReveal < 1 ? 1 / 620 : 0,
				});
				root.dataset.chainState = chainState;
				root.style.setProperty("--vampire-fill", `${(fill * 100).toFixed(3)}%`);
				root.style.setProperty("--vampire-tide-opacity", clamp(fill * 1.18).toFixed(3));
				root.style.setProperty("--vampire-enchant-opacity", clamp((resolvedIntro - 0.02) / 0.35).toFixed(3));
				root.style.setProperty("--vampire-enchant-progress", clamp((resolvedIntro - 0.02) / 0.7).toFixed(3));
				root.style.setProperty("--vampire-gloss-position", `${(-18 + clamp((fill - 0.66) / 0.34) * 136).toFixed(2)}%`);
				root.style.setProperty("--vampire-gloss-opacity", Math.sin(clamp((fill - 0.6) / 0.4) * Math.PI).toFixed(3));
			},
			onComplete: () => finish("ended"),
		});

		timeline
			.fromTo(video, { scale: 1.035 }, { scale: 1.09, duration: 4.6, ease: "none" }, 0)
			.to(video, { filter: "contrast(1.3) saturate(.64) brightness(.64)", duration: 0.18 }, 2.48)
			.to(video, { filter: "contrast(1.08) saturate(.78) brightness(.72)", duration: 0.24 }, 2.66)
			.call(() => (phase = "title"), [], VAMPIRE_INTRO_TIMINGS.framesEndMs / 1_000)
			.to(titleStage, { autoAlpha: 1, scale: 1, duration: 0.52 }, VAMPIRE_INTRO_TIMINGS.framesEndMs / 1_000)
			.fromTo(title, { filter: "blur(8px) brightness(1.8)" }, { filter: "blur(0px) brightness(1)", duration: 0.44 }, 4.62)
			.fromTo(subtitle, { autoAlpha: 0, y: 7 }, { autoAlpha: 0.8, y: 0, duration: 0.42 }, 4.78)
			.to(title, { x: 8, duration: 0.045, repeat: 5, yoyo: true, ease: "steps(1)" }, 5.34)
			.call(() => (phase = "chain"), [], VAMPIRE_INTRO_TIMINGS.titleEndMs / 1_000)
			.to(status, { autoAlpha: 1, duration: 0.18 }, VAMPIRE_INTRO_TIMINGS.titleEndMs / 1_000)
			.to(titleStage, { scaleX: 0.965, duration: 0.18, repeat: 1, yoyo: true, ease: "power4.inOut" }, 7.2)
			.call(() => (phase = "locked"), [], VAMPIRE_INTRO_TIMINGS.chainEndMs / 1_000)
			.to(flash, { autoAlpha: 0.35, duration: 0.055, repeat: 1, yoyo: true }, 8.2)
			.to(title, { filter: "brightness(.72) contrast(1.2)", duration: 1.7 }, 8.55)
			.to(flash, { autoAlpha: 0.96, duration: 0.12, ease: "power4.in" }, 10.64)
			.call(reveal, [], config.revealAtMs / 1_000)
			.set(staticLayer, { autoAlpha: 0 }, config.revealAtMs / 1_000)
			.to(flash, { autoAlpha: 0, duration: 0.48 }, config.revealAtMs / 1_000)
			.to(title, { x: -7, duration: 0.055, repeat: 5, yoyo: true, ease: "steps(1)" }, 11.76)
			.call(() => (phase = "exit"), [], VAMPIRE_INTRO_TIMINGS.exitMs / 1_000)
			.to([titleStage, status], { autoAlpha: 0, y: -18, filter: "blur(8px)", duration: 1.35, ease: "power2.in" }, VAMPIRE_INTRO_TIMINGS.exitMs / 1_000)
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
	<section class="vampire-title-stage" data-title-stage aria-labelledby="vampire-intro-title">
		<span class="vampire-title-reset vampire-title-base" aria-hidden="true">VAMPIRE</span>
		<h1 id="vampire-intro-title" class="vampire-title" data-intro-title aria-label="VAMPIRE">
			<canvas bind:this={chainBack} class="vampire-title-chain vampire-title-chain--back" data-chain-canvas="back" width="1400" height="420" aria-hidden="true"></canvas>
			<span bind:this={titleAnchor} class="vampire-title-base" aria-hidden="true">VAMPIRE</span>
			<span class="vampire-title-tide" aria-hidden="true" data-text="VAMPIRE">VAMPIRE</span>
			<canvas bind:this={chainFront} class="vampire-title-chain vampire-title-chain--front" data-chain-canvas="front" width="1400" height="420" aria-hidden="true"></canvas>
			<span class="vampire-title-enchant" aria-hidden="true">VAMPIRE</span>
			<span class="vampire-title-gloss" aria-hidden="true">VAMPIRE</span>
		</h1>
		<p class="vampire-intro__subtitle" data-intro-subtitle>{config.subtitle}</p>
	</section>
	<div class="vampire-intro__status" data-chain-status aria-hidden="true"><span>CHAIN SYSTEM / YUIMI DIRECT PORT</span><strong>{chainState}</strong></div>
	<div class="vampire-intro__flash" data-intro-flash aria-hidden="true"></div>
	<button type="button" class="vampire-intro__skip" onclick={() => finish("skipped")} disabled={!ready}>跳过</button>
</div>

<style>
.vampire-intro{--vampire-fill:0%;--vampire-tide-opacity:0;--vampire-enchant-opacity:0;--vampire-enchant-progress:0;--vampire-gloss-position:-18%;--vampire-gloss-opacity:0;position:absolute;z-index:120;inset:0;isolation:isolate;overflow:hidden;background:transparent;color:#f7f3f4;font-family:Georgia,"Times New Roman",serif}
.vampire-intro__static,.vampire-intro__poster,.vampire-intro__video,.vampire-intro__vignette,.vampire-intro__chromatic,.vampire-intro__scanlines,.vampire-intro__flash{position:absolute;inset:0}
.vampire-intro__static{z-index:0;overflow:hidden;background:#030205}.vampire-intro__poster,.vampire-intro__video{display:block;width:100%;height:100%;object-fit:cover;object-position:center}.vampire-intro__poster{filter:brightness(.64) contrast(1.1)}.vampire-intro__video{filter:contrast(1.08) saturate(.78) brightness(.72);will-change:transform,filter}.vampire-intro__vignette{background:radial-gradient(circle at 50% 46%,transparent 20%,rgb(2 0 4/.35) 62%,rgb(0 0 0/.92) 100%);box-shadow:inset 0 0 18vmax rgb(0 0 0/.58)}
.vampire-intro__chromatic{position:absolute;z-index:1;inset:0;pointer-events:none;background:linear-gradient(90deg,rgb(26 107 145/.14),transparent 42% 58%,rgb(187 22 71/.16));mix-blend-mode:screen}.vampire-intro__scanlines{z-index:8;pointer-events:none;opacity:.12;background-image:linear-gradient(transparent 0 2px,rgb(0 0 0/.55) 2px 3px,transparent 3px);background-size:100% 4px}
.vampire-title-stage{position:absolute;z-index:5;top:50%;left:50%;display:grid;place-items:center;isolation:isolate;width:min(1120px,94vw);transform:translate(-50%,-50%);font-size:clamp(4.25rem,12.2vw,11rem);font-weight:700;line-height:.86;letter-spacing:0;text-align:center;pointer-events:none}.vampire-title-stage>.vampire-title,.vampire-title-stage>.vampire-title-reset{grid-area:1/1}.vampire-title{position:relative;z-index:1;display:grid;isolation:isolate;margin:0;font:inherit;letter-spacing:0;transform-origin:50% 50%;will-change:transform,filter,opacity}.vampire-title>span,.vampire-title-reset{position:relative;z-index:1;grid-area:1/1;display:block;color:transparent;-webkit-text-fill-color:transparent;background-clip:text;-webkit-background-clip:text;-webkit-text-stroke:2px rgb(235 239 255/.24);text-shadow:0 12px 30px rgb(5 8 28/.4)}
.vampire-title-base{background-image:linear-gradient(45deg,transparent 0,transparent calc(var(--vampire-fill) - 2%),rgb(11 16 30/.34) calc(var(--vampire-fill) + 5.5%),transparent calc(var(--vampire-fill) + 13%)),repeating-linear-gradient(103deg,rgb(216 226 236/.025) 0 1px,rgb(19 27 46/.105) 1px 2px,transparent 2px 11px),linear-gradient(180deg,#a6b1bf 0%,#6d7b91 38%,#44516b 72%,#2b3449 100%);background-blend-mode:multiply,soft-light,normal;filter:saturate(.52) brightness(.8) contrast(.94)}.vampire-title-reset{z-index:0;opacity:.28}
.vampire-title-tide{opacity:var(--vampire-tide-opacity);background-image:radial-gradient(ellipse at 18% 19%,rgb(255 218 207/.22) 0 .9%,transparent 4.6%),linear-gradient(124deg,transparent 0 19%,rgb(255 218 210/.13) 19.4% 20.1%,transparent 20.7% 69%,rgb(232 149 157/.095) 69.4% 70.1%,transparent 70.7%),linear-gradient(180deg,#8f535e 0%,#772b3f 39%,#52142a 72%,#2f0719 100%);background-clip:text;-webkit-background-clip:text;mask-image:linear-gradient(45deg,#000 0,#000 calc(var(--vampire-fill) - 6.5%),transparent calc(var(--vampire-fill) + 6.8%),transparent 100%)}.vampire-title-tide::before,.vampire-title-tide::after{content:attr(data-text);position:absolute;inset:0;display:block;color:transparent;-webkit-text-fill-color:transparent;background-clip:text;-webkit-background-clip:text}.vampire-title-tide::before{background-image:linear-gradient(180deg,#d9909b 0%,#bd3f5e 54%,#831d3d 100%);opacity:.62}.vampire-title-tide::after{background-image:repeating-linear-gradient(113deg,transparent 0 17%,rgb(171 55 78/.34) 18.2% 19.4%,transparent 20.6% 41%);opacity:.72;mix-blend-mode:multiply}
.vampire-title-enchant{z-index:3;opacity:var(--vampire-enchant-opacity);background-image:linear-gradient(112deg,transparent 31%,rgb(126 170 255/.38) 41%,#fff 50%,rgb(255 76 136/.9) 54%,transparent 71%),linear-gradient(180deg,#fff8fb,#ff7da1 48%,#7fa8ff);clip-path:circle(calc(4% + var(--vampire-enchant-progress)*126%) at 53% 57%);mix-blend-mode:screen;text-shadow:0 0 14px rgb(255 55 121/.72)}.vampire-title-gloss{z-index:4;opacity:var(--vampire-gloss-opacity);background-image:linear-gradient(180deg,#fff,#fff8fb 38%,#ffb0c2 72%,#ff7894);clip-path:polygon(calc(var(--vampire-gloss-position) - 9%) 100%,calc(var(--vampire-gloss-position) + 2%) 100%,calc(var(--vampire-gloss-position) + 11%) 0,var(--vampire-gloss-position) 0);mix-blend-mode:screen}
.vampire-title-chain{position:absolute;inset:-38% -32%;width:164%;height:176%;pointer-events:none;opacity:0;transform:translateZ(0);mask-image:linear-gradient(90deg,transparent 0,#000 8%,#000 92%,transparent 100%);will-change:opacity,transform}.vampire-title-chain--back{z-index:0;filter:saturate(.82) brightness(.7) drop-shadow(0 4px 8px rgb(5 7 29/.64))}.vampire-title-chain--front{z-index:5;filter:saturate(.9) contrast(1.12) drop-shadow(0 5px 9px rgb(7 8 28/.72))}
.vampire-intro__subtitle{position:absolute;top:calc(100% + 24px);margin:0;font:700 12px/1.2 Arial,sans-serif;letter-spacing:0;color:rgb(255 122 163/.86);text-shadow:0 0 9px rgb(230 39 98/.76)}.vampire-intro__status{position:absolute;z-index:7;top:max(24px,env(safe-area-inset-top));left:max(24px,env(safe-area-inset-left));display:grid;gap:5px;font-family:Consolas,monospace;letter-spacing:0;pointer-events:none}.vampire-intro__status span{font-size:9px;color:rgb(192 211 232/.58)}.vampire-intro__status strong{font-size:11px;color:#f16b9b;text-shadow:0 0 7px rgb(235 37 100/.75)}
.vampire-intro__flash{z-index:20;background:#f3edf0;opacity:0;pointer-events:none}.vampire-intro__skip{position:absolute;z-index:30;right:max(18px,env(safe-area-inset-right));bottom:max(18px,env(safe-area-inset-bottom));height:38px;padding:0 16px;border:1px solid rgb(255 255 255/.32);border-radius:4px;background:rgb(5 5 8/.78);color:#fff;font:600 12px/1 Arial,sans-serif;cursor:pointer;backdrop-filter:blur(10px)}.vampire-intro__skip:hover,.vampire-intro__skip:focus-visible{border-color:#e0366c;outline:2px solid rgb(224 54 108/.4);outline-offset:2px}.vampire-intro__skip:disabled{cursor:wait;opacity:.58}
@media(max-width:800px){.vampire-title-stage{font-size:clamp(3.6rem,13.6vw,6rem)}}@media(max-width:480px){.vampire-title-stage{width:96vw;font-size:3.25rem}.vampire-intro__subtitle{top:calc(100% + 16px);font-size:10px}.vampire-intro__status{top:16px;left:16px}}@media(prefers-reduced-motion:reduce){.vampire-intro{display:none}}
</style>
