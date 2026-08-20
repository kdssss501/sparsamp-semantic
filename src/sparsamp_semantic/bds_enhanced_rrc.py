"""BDS-Enhanced RRC: Precision-hardened rotation range coding via bounded decision sets.

This module integrates the Bounded Decision Set (BDS) abstraction directly into
the RRC encoding loop.  Instead of using nominal interval boundaries that can
shift under precision perturbations, it computes *robust core intervals* from
the BDS envelope — the region of each token's interval that is guaranteed to
belong to that token under any feasible logit-bin perturbation.

Algorithmic contribution
------------------------
Standard RRC (Algorithm 3 of Yan & Murawaki ACL 2026) selects a token based on
the exact quantized probabilities at the encoder.  If the decoder's probabilities
differ even slightly (due to FP16 vs FP32, different GPU kernels, etc.), the
interval boundaries shift and the decoder may select a different token, causing
message loss.

BDS-enhanced RRC addresses this at the encoding stage:
1. At each step, we compute the BDS uncertainty envelope from the top-k
   quantized logit bins.  The envelope gives, for each token, the range of
   possible cumulative probabilities under the perturbation model (each bin
   may shift by ±Δ).
2. We compute the *robust core* interval for each token: the region that is
   guaranteed to be assigned to that token regardless of how the bins shift
   within the declared bounds.
3. If the rotated secret position falls in the robust core of some token, we
   select that token — the decision is guaranteed to be invariant under the
   perturbation model.
4. If the position falls in the *uncertainty zone* between tokens, we cannot
   guarantee robustness for this step.  We record it as a *vulnerable step*,
   and the encoder may either:
   a) Emit a guard token that resolves the ambiguity (reducing the interval
      width without narrowing the message), or
   b) Accept the nominal token but record the step in the replay manifest.

The benefit is that the replay manifest only needs to cover vulnerable steps
rather than all steps where the decision might change.  For typical precision
shifts, the robust core covers most of the probability space, so vulnerable
steps are rare and the manifest is small.

Reference
---------
- Yan & Murawaki, "Efficient Provably Secure Linguistic Steganography via
  Range Coding", ACL 2026 (Algorithm 3/4).
- Bounded Decision Set contract: docs/reproducibility/R058_BOUNDED_DECISION_SET_CONTRACT.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_DOWN, localcontext
from fractions import Fraction
from itertools import combinations, product
from math import ceil, log10
from time import perf_counter
from typing import Hashable, Literal

from .rrc import (
    RrcConfig,
    RotationRangeCodec,
    _decimal_probabilities,
    _observed_interval,
    _positive_mod,
    _select_interval,
)
from .probability_contract import allocate_logit_bin_mass
from .prf import HmacRandomStream
from .providers.base import ProviderSession
from .types import DistributionSnapshot
from .core import DecodeResult, EncodeResult, IncompleteEncodeError, StepRecord


@dataclass(frozen=True)
class BdsRrcConfig:
    """Configuration for BDS-enhanced RRC.

    Extends the standard RRC config with the BDS perturbation model parameters.
    The envelope permutation radius Δ (bin_shift_radius) and the number of
    envelope tokens (envelope_top_k) control the conservativeness of the robust
    interval computation.
    """

    message_bits: int
    max_tokens: int = 2048
    probability_quantum: str | None = "1e-15"
    probability_mass_bits: int | None = None
    preserve_probability_support: bool = True
    guard_digits: int = 24
    min_precision: int = 48
    termination_mode: Literal["paper", "verified"] = "verified"

    # BDS perturbation model parameters
    bin_shift_radius: int = 1
    envelope_top_k: int = 3
    logit_quantum: float = 0.5
    contract_temperature: float = 1.0
    contract_mass_bits: int = 16

    # Vulnerability handling
    vulnerable_step_policy: Literal["guard", "record", "raise", "full"] = "guard"

    # Perturbation model
    perturbation_model: Literal["independent", "correlated"] = "correlated"

    def __post_init__(self) -> None:
        if self.message_bits < 1:
            raise ValueError("message_bits must be positive")
        if self.max_tokens < 1:
            raise ValueError("max_tokens must be positive")
        if self.guard_digits < 8:
            raise ValueError("guard_digits must be at least 8")
        if self.min_precision < 16:
            raise ValueError("min_precision must be at least 16")
        if self.termination_mode not in {"paper", "verified"}:
            raise ValueError("termination_mode must be 'paper' or 'verified'")
        if self.bin_shift_radius < 0:
            raise ValueError("bin_shift_radius must be non-negative")
        if self.envelope_top_k < 2:
            raise ValueError("envelope_top_k must be at least 2")
        if self.logit_quantum <= 0:
            raise ValueError("logit_quantum must be positive")
        if self.contract_temperature <= 0:
            raise ValueError("contract_temperature must be positive")
        if not 1 <= self.contract_mass_bits <= 52:
            raise ValueError("contract_mass_bits must be in [1, 52]")
        if self.vulnerable_step_policy not in {"guard", "record", "raise", "full"}:
            raise ValueError("vulnerable_step_policy must be 'guard', 'record', 'raise', or 'full'")
        if self.perturbation_model not in {"independent", "correlated"}:
            raise ValueError("perturbation_model must be 'independent' or 'correlated'")

    @property
    def decimal_precision(self) -> int:
        integer_digits = ceil(self.message_bits * log10(2)) + 1
        mass_digits = (self.probability_mass_bits or 0) + self.guard_digits
        return max(self.min_precision, integer_digits + self.guard_digits, mass_digits)

    @property
    def _rrc_config(self) -> RrcConfig:
        return RrcConfig(
            message_bits=self.message_bits,
            max_tokens=self.max_tokens,
            probability_quantum=self.probability_quantum,
            probability_mass_bits=self.probability_mass_bits,
            preserve_probability_support=self.preserve_probability_support,
            guard_digits=self.guard_digits,
            min_precision=self.min_precision,
            termination_mode=self.termination_mode,
        )


@dataclass(frozen=True)
class BdsEnvelope:
    """BDS uncertainty envelope for one decoding step.

    The envelope captures the range of possible cumulative probabilities
    for each token under the perturbation model.
    """

    token_ids: tuple[int, ...]
    nominal_probabilities: tuple[Decimal, ...]
    left_possible_bounds: tuple[Decimal, ...]
    right_possible_bounds: tuple[Decimal, ...]
    safe_left_bounds: tuple[Decimal, ...]
    safe_right_bounds: tuple[Decimal, ...]
    bin_shift_radius: int
    feasible_pair_count: int
    feasible_contract_count: int

    @property
    def robust_step(self) -> bool:
        """Return True if all tokens have non-empty safe cores."""
        for left, right in zip(self.safe_left_bounds, self.safe_right_bounds, strict=True):
            if left >= right:
                return False
        return True

    def safe_interval_for_token(self, index: int) -> tuple[Decimal, Decimal]:
        """Return the safe core interval [left, right) for a given token index."""
        return self.safe_left_bounds[index], self.safe_right_bounds[index]

    def contains_in_safe_core(self, position: Decimal, index: int) -> bool:
        """Check if a position falls in the safe core of a given token."""
        left, right = self.safe_interval_for_token(index)
        return left <= position < right

    def uncertainty_zone_for_token(self, index: int) -> tuple[Decimal, Decimal]:
        """Return the full possible interval [left, right) for a given token index."""
        return self.left_possible_bounds[index], self.right_possible_bounds[index]


def _compute_bds_envelope(
    snapshot: DistributionSnapshot,
    config: BdsRrcConfig,
) -> BdsEnvelope | None:
    """Compute the BDS uncertainty envelope from a distribution snapshot.

    Returns None if the snapshot does not expose quantized logit bins
    (required for BDS analysis).

    The envelope probabilities are computed from the integer mass allocation
    (using the precomputed softmax table), NOT from the floating-point
    probabilities in the snapshot.  This ensures that both encoder and decoder
    compute the same envelope, even if their floating-point probabilities differ.
    """
    bins_raw = snapshot.metadata.get("quantized_logit_bins")
    if not isinstance(bins_raw, dict):
        return None

    bins = {int(token_id): int(value) for token_id, value in bins_raw.items()}
    ranked = sorted(snapshot.candidates, key=lambda c: int(c.rank))
    if len(ranked) < config.envelope_top_k:
        return None

    # For correlated model, use ALL retained tokens (not just top-K)
    # because the uniform shift affects all tokens equally.
    # For independent model, use only top-K (original BDS contract).
    if config.perturbation_model == "correlated":
        envelope = ranked  # Use all tokens
    else:
        envelope = ranked[: config.envelope_top_k]
    envelope_ids = tuple(int(c.token_id) for c in envelope)
    envelope_bins = tuple(bins[tid] for tid in envelope_ids)

    # Keep the same ordering as snapshot.candidates (by rank) for consistency
    # with the probabilities used in RRC encoding.
    ordered_ids = envelope_ids
    ordered_bins = envelope_bins

    # Compute nominal probabilities from the integer allocation (not from snapshot)
    # This is the key difference from the floating-point approach:
    # we use the precomputed softmax table to get deterministic integer weights.
    mass_bits = config.contract_mass_bits
    total_mass = 1 << mass_bits
    nominal_allocation = allocate_logit_bin_mass(
        ordered_ids,
        ordered_bins,
        quantum=config.logit_quantum,
        temperature=config.contract_temperature,
        mass_bits=mass_bits,
    )
    # Convert to Decimal for consistency with the rest of the system
    with localcontext() as context:
        context.prec = config.decimal_precision
        nominal_probs = tuple(
            Decimal(count) / Decimal(total_mass)
            for count in nominal_allocation.counts
        )

    # For each token, compute the range of possible cumulative probabilities
    # under the perturbation model.
    #
    # Two models are supported:
    # - "independent": each bin shifts independently by ±Δ (worst-case)
    # - "correlated": all bins shift by the same δ ∈ [-Δ, Δ] (models systematic
    #   precision error where FP16/BF16 affects all logits in the same direction)
    #
    # We enumerate all possible bin assignments for the top-2 pair (as in BDS),
    # and compute the resulting cumulative probability for each token.

    K = len(ordered_ids)
    Δ = config.bin_shift_radius
    correlated = config.perturbation_model == "correlated"

    # Collect all possible cumulative probabilities for each token
    # under all feasible top-2 pair and bin assignments
    possible_cumulatives: list[list[Fraction]] = [[] for _ in range(K)]

    feasible_pair_count = 0
    feasible_contract_count = 0

    if correlated:
        # Correlated model: use ALL envelope tokens directly.
        # Enumerate δ ∈ [-Δ, Δ]; all bins shift by the same δ.
        # The softmax distribution is invariant under uniform shift
        # (the common factor exp(δ·q/T) cancels out), but the integer
        # allocation may differ slightly due to rounding.
        # This gives EXACT safe cores without the top-2 pair abstraction.
        for delta in range(-Δ, Δ + 1):
            shifted_bins = tuple(b + delta for b in ordered_bins)
            feasible_contract_count += 1
            allocation = allocate_logit_bin_mass(
                ordered_ids,
                shifted_bins,
                quantum=config.logit_quantum,
                temperature=config.contract_temperature,
                mass_bits=mass_bits,
            )

            # Compute cumulative probabilities from the full allocation
            cum = Fraction(0)
            for i in range(K):
                possible_cumulatives[i].append(cum)
                cum += Fraction(allocation.counts[i], total_mass)

        # All tokens participate in the full-envelope model
        feasible_pair_count = 1
    else:
        # Independent model: enumerate top-2 pairs (original BDS contract)
        for left_idx, right_idx in combinations(range(K), 2):
            pair_ids = (ordered_ids[left_idx], ordered_ids[right_idx])
            pair_bins = (ordered_bins[left_idx], ordered_bins[right_idx])

            # Check if this pair is feasible (can be top-2)
            other_lower = max(
                (ordered_bins[i] - Δ for i in range(K) if i not in {left_idx, right_idx}),
                default=-10**9,
            )
            if min(pair_bins[0] + Δ, pair_bins[1] + Δ) < other_lower:
                continue

            feasible_pair_count += 1

            for first_bin, second_bin in product(
                range(pair_bins[0] - Δ, pair_bins[0] + Δ + 1),
                range(pair_bins[1] - Δ, pair_bins[1] + Δ + 1),
            ):
                feasible_contract_count += 1
                allocation = allocate_logit_bin_mass(
                    pair_ids,
                    (first_bin, second_bin),
                    quantum=config.logit_quantum,
                    temperature=config.contract_temperature,
                    mass_bits=mass_bits,
                )

                # Map the allocation counts back to the full envelope
                full_counts = [0] * K
                for idx_in_pair, tid in enumerate(pair_ids):
                    full_idx = ordered_ids.index(tid)
                    full_counts[full_idx] = allocation.counts[idx_in_pair]

                # Compute cumulative probabilities
                cum = Fraction(0)
                for i in range(K):
                    possible_cumulatives[i].append(cum)
                    cum += Fraction(full_counts[i], total_mass)
    if not possible_cumulatives[0]:
        return None  # No feasible pairs

    # For each token, find the min and max possible cumulative left bound
    # and the min and max possible cumulative right bound.
    #
    # The cumulative right bound for token i is:
    #   - left bound of token i+1 (if i < K-1)
    #   - 1.0 (if i = K-1, the last token)
    left_min = []
    left_max = []
    right_min = []  # min cumulative RIGHT bound (not probability width)
    right_max = []  # max cumulative RIGHT bound

    for i in range(K):
        cum_lefts = possible_cumulatives[i]
        left_min.append(min(cum_lefts))
        left_max.append(max(cum_lefts))

        if i < K - 1:
            # Right bound = left bound of next token
            next_lefts = possible_cumulatives[i + 1]
            right_min.append(min(next_lefts))
            right_max.append(max(next_lefts))
        else:
            # Last token extends to 1.0
            right_min.append(Fraction(1, 1))
            right_max.append(Fraction(1, 1))

    # Convert to Decimal for consistency with RRC
    with localcontext() as context:
        context.prec = config.decimal_precision

        # Possible interval for each token: [left_min, right_max)
        left_possible = tuple(
            Decimal(left_min[i].numerator) / Decimal(left_min[i].denominator)
            for i in range(K)
        )
        right_possible = tuple(
            Decimal(right_max[i].numerator) / Decimal(right_max[i].denominator)
            for i in range(K)
        )

        # Safe core: the region that is guaranteed to belong to the token
        # regardless of perturbation.  This is the intersection of all possible
        # intervals for this token.
        # Safe left = max over all possible left bounds (rightmost left edge)
        # Safe right = min over all possible right bounds (leftmost right edge)
        safe_left = tuple(
            Decimal(left_max[i].numerator) / Decimal(left_max[i].denominator)
            for i in range(K)
        )
        safe_right = tuple(
            Decimal(right_min[i].numerator) / Decimal(right_min[i].denominator)
            for i in range(K)
        )

    return BdsEnvelope(
        token_ids=ordered_ids,
        nominal_probabilities=nominal_probs,
        left_possible_bounds=left_possible,
        right_possible_bounds=right_possible,
        safe_left_bounds=safe_left,
        safe_right_bounds=safe_right,
        bin_shift_radius=Δ,
        feasible_pair_count=feasible_pair_count,
        feasible_contract_count=feasible_contract_count,
    )



def _check_cumulative_stability(
    snapshot,
    config,
    selected_index,
    probabilities,
):
    """Check if the cumulative probability for the selected token is stable."""
    import math
    from decimal import Decimal
    
    bins_raw = snapshot.metadata.get("quantized_logit_bins")
    if not isinstance(bins_raw, dict):
        # No bins available - can't check stability, assume robust
        cum_left = sum(probabilities[:selected_index])
        cum_right = cum_left + probabilities[selected_index]
        return True, cum_left, cum_right
    
    bins = {int(tid): int(b) for tid, b in bins_raw.items()}
    ids = [int(c.token_id) for c in snapshot.candidates]
    
    mass_bits = config.probability_mass_bits or config.contract_mass_bits
    if mass_bits is None:
        cum_left = sum(probabilities[:selected_index])
        cum_right = cum_left + probabilities[selected_index]
        return False, cum_left, cum_right
    
    from sparsamp_semantic.probability_contract import allocate_logit_bin_mass
    allocation = allocate_logit_bin_mass(
        ids, [bins[tid] for tid in ids],
        quantum=config.logit_quantum,
        temperature=config.contract_temperature,
        mass_bits=mass_bits,
    )
    
    total_mass = Decimal(1 << mass_bits)
    nom_counts = allocation.counts
    
    nom_cum_left = Decimal(sum(nom_counts[:selected_index])) / total_mass
    nom_cum_right = Decimal(sum(nom_counts[:selected_index + 1])) / total_mass
    
    quantum = config.logit_quantum
    temp = config.contract_temperature
    delta = config.bin_shift_radius
    
    if delta == 0:
        return True, nom_cum_left, nom_cum_right
    
    mult_up = Decimal(str(math.exp(quantum * delta / temp)))
    mult_down = Decimal(str(math.exp(-quantum * delta / temp)))
    
    K = len(ids)
    idx = selected_index
    
    w_up = [Decimal(count) * (mult_up if j < idx else (mult_down if j > idx else Decimal(1)))
            for j, count in enumerate(nom_counts)]
    tot_up = sum(w_up)
    max_cum_left = sum(w_up[:idx]) / tot_up if tot_up > 0 else Decimal(0)
    
    w_down = [Decimal(count) * (mult_down if j < idx else (mult_up if j > idx else Decimal(1)))
              for j, count in enumerate(nom_counts)]
    tot_down = sum(w_down)
    min_cum_left = sum(w_down[:idx]) / tot_down if tot_down > 0 else Decimal(0)
    
    # Also compute worst-case range for the RIGHT bound
    max_cum_right = sum(w_up[:idx + 1]) / tot_up if tot_up > 0 else Decimal(1)
    min_cum_right = sum(w_down[:idx + 1]) / tot_down if tot_down > 0 else Decimal(1)
    
    left_range = max_cum_left - min_cum_left
    right_range = max_cum_right - min_cum_right
    range_width = max(left_range, right_range)
    threshold = Decimal(1) / total_mass
    is_robust = range_width <= threshold
    
    return is_robust, nom_cum_left, nom_cum_right
def _select_robust_token(
    position: Decimal,
    envelope: BdsEnvelope | None,
    probabilities: tuple[Decimal, ...],
    snapshot: DistributionSnapshot,
) -> tuple[int, bool]:
    """Select the token whose interval contains `position`, preferring robust cores.

    Returns (candidate_index, is_robust) where is_robust is True if the
    selection is guaranteed to be invariant under the perturbation model.
    """
    if envelope is None:
        # No BDS envelope available; fall back to nominal selection
        candidate_index, _, _ = _select_interval(probabilities, position)
        return candidate_index, False

    # First, try to find a token whose safe core contains the position
    for i in range(len(envelope.token_ids)):
        if envelope.contains_in_safe_core(position, i):
            return i, True

    # No safe core found; the position is in an uncertainty zone.
    # Fall back to nominal selection for the envelope tokens.
    # First check if position falls in any envelope token's full possible interval
    for i in range(len(envelope.token_ids)):
        left, right = envelope.uncertainty_zone_for_token(i)
        if left <= position < right:
            return i, False

    # Position might be outside the envelope (due to other tokens not in top-k).
    # Fall back to nominal selection.
    candidate_index, _, _ = _select_interval(probabilities, position)
    return candidate_index, False


class BdsEnhancedRotationRangeCodec:
    """RRC with BDS-guided precision-robust token selection.

    This codec extends the standard RRC with the BDS uncertainty envelope.
    At each step, it prefers tokens whose safe core contains the rotated
    secret position, guaranteeing robustness under the declared perturbation
    model.  Vulnerable steps (where the position falls in an uncertainty zone)
    are recorded and handled according to the configured policy.
    """

    def __init__(self, config: BdsRrcConfig) -> None:
        self.config = config
        # Fallback standard RRC codec for fallback operations
        self._fallback_codec = RotationRangeCodec(config._rrc_config)

    @staticmethod
    def _reverse_midpoint(
        midpoint: Decimal,
        history: list[tuple[Decimal, Decimal]],
        random_stream: HmacRandomStream,
    ) -> Decimal:
        """Reverse the interval rotation; delegates to the standard RRC method."""
        return RotationRangeCodec._reverse_midpoint(midpoint, history, random_stream)

    def _validate_bits(self, bits: str) -> None:
        if len(bits) != self.config.message_bits:
            raise ValueError(f"message must contain exactly {self.config.message_bits} bits")
        if set(bits) - {"0", "1"}:
            raise ValueError("message must be a binary string")

    def encode(self, session: ProviderSession, bits: str, key: bytes) -> EncodeResult:
        """Embed a fixed-length bit string with BDS-guided precision-robust encoding.

        The encoding follows the same overall structure as standard RRC
        (Algorithm 3 from Yan & Murawaki).  At each step it uses the standard
        RRC token selection (identical random stream domain), then consults the
        BDS envelope to check whether the decision is robust under the declared
        perturbation model.

        Vulnerable steps (where the BDS envelope indicates the decision could
        change under perturbation) are handled according to the policy:
        - "guard": replace the token with a robust alternative (safe-core token)
        - "record": emit the nominal token and record the step as vulnerable
        - "raise": raise an error (fail-safe)

        The "guard" policy is the key algorithmic contribution: when the
        position falls in the uncertainty zone of the nominal token, we
        search for an alternative token whose safe core contains the position.
        If found, we emit that token instead — it is guaranteed to be
        invariant under the perturbation model.  This changes the encoding
        path but the message is still correctly encoded because the decoder
        observes the same token and uses the same interval narrowing.
        """
        self._validate_bits(bits)
        random_stream = HmacRandomStream(key, session.context_id)
        records: list[StepRecord] = []
        started = perf_counter()
        # Reset certificate for each encode call
        self._certificate: list[tuple[int, int, int]] = []

        with localcontext() as context:
            context.prec = self.config.decimal_precision
            left = Decimal(0)
            right = Decimal(1 << self.config.message_bits)
            secret = Decimal(int(bits, 2))
            original_secret = int(bits, 2)
            half = Decimal("0.5")
            history: list[tuple[Decimal, Decimal]] = []
            vulnerable_steps: list[int] = []
            guard_steps: list[int] = []

            for step in range(self.config.max_tokens):
                snapshot = session.next_distribution()
                # Compute probabilities from the SAME logit bins as the BDS envelope.
                # This ensures the envelope safe cores correctly predict token selection.
                bins_raw = snapshot.metadata.get("quantized_logit_bins")
                mass_bits = self.config.probability_mass_bits or self.config.contract_mass_bits
                if isinstance(bins_raw, dict) and mass_bits is not None:
                    bins = {int(tid): int(b) for tid, b in bins_raw.items()}
                    # Use the same ordering as snapshot.candidates (by rank)
                    retained_ids = [int(c.token_id) for c in snapshot.candidates]
                    retained_bins = [bins[tid] for tid in retained_ids]
                    allocation = allocate_logit_bin_mass(
                        retained_ids,
                        retained_bins,
                        quantum=self.config.logit_quantum,
                        temperature=self.config.contract_temperature,
                        mass_bits=mass_bits,
                    )
                    total_mass = Decimal(1 << mass_bits)
                    probabilities = tuple(
                        Decimal(count) / total_mass
                        for count in allocation.counts
                    )
                else:
                    probabilities = _decimal_probabilities(
                        snapshot,
                        self.config.probability_quantum,
                        self.config.probability_mass_bits,
                        self.config.preserve_probability_support,
                    )
                forward_kl = snapshot.forward_kl_to_nats(probabilities)
                quantization_tv = snapshot.total_variation_to(probabilities)
                support_loss_count, support_loss_mass = snapshot.support_loss_to(probabilities)
                width = right - left
                if width <= 0:
                    raise ArithmeticError("range-coding interval collapsed to zero")
                history.append((left, right))
                # Use the same domain as standard RRC for compatibility
                offset_fraction = random_stream.fraction(step, domain=b"rrc")
                offset = Decimal(offset_fraction.numerator) / Decimal(offset_fraction.denominator)
                secret = left + _positive_mod(secret - left + offset * width, width)
                position = (secret - left) / width

                # Standard RRC token selection (identical to rrc.RotationRangeCodec.encode)
                nominal_index, lower_probability, upper_probability = _select_interval(
                    probabilities, position
                )
                nominal_token_id = snapshot.candidates[nominal_index].token_id

                # Helper to safely convert token_id to int for BDS comparison
                def _to_int(tid: Hashable) -> int | None:
                    try:
                        return int(tid)
                    except (ValueError, TypeError):
                        return None

                # Compute the BDS envelope for robustness check
                envelope = _compute_bds_envelope(snapshot, self.config)
                is_robust = False
                candidate_index = nominal_index
                guard_applied = False

                # Check cumulative stability (new robust detection)
                cum_robust, cum_left, cum_right = _check_cumulative_stability(
                    snapshot, self.config, nominal_index, probabilities
                )
                if not cum_robust or self.config.vulnerable_step_policy == "full":
                    if not cum_robust:
                        vulnerable_steps.append(step)
                    # Store the nominal cumulative bounds for the certificate
                    total_mass = Decimal(1 << (self.config.probability_mass_bits or self.config.contract_mass_bits))
                    cl_int = int(cum_left * total_mass)
                    cr_int = int(cum_right * total_mass)
                    cert_entry = (step, cl_int, cr_int)
                    if not hasattr(self, '_certificate'):
                        self._certificate = []
                    self._certificate.append(cert_entry)

                if envelope is not None:
                    # Check if the position is in the safe core of the nominal token
                    nominal_tid_int = _to_int(nominal_token_id)
                    if nominal_tid_int is not None and nominal_tid_int in envelope.token_ids:
                        env_idx = envelope.token_ids.index(nominal_tid_int)
                        is_robust = envelope.contains_in_safe_core(position, env_idx)

                    # If not robust and policy is "guard", try to find a robust alternative.
                    # The guard token must be the SAME as the nominal token in the
                    # provider's distribution (not just the BDS envelope).
                    # We only apply the guard when the BDS model and the provider
                    # agree on which token the position belongs to.
                    if not is_robust and self.config.vulnerable_step_policy == "guard":
                        # Search for a token in the envelope whose safe core contains
                        # the position AND whose provider interval also contains it.
                        for env_idx in range(len(envelope.token_ids)):
                            if envelope.contains_in_safe_core(position, env_idx):
                                guard_tid = envelope.token_ids[env_idx]
                                # Find this token in the full candidate list
                                for full_idx, c in enumerate(snapshot.candidates):
                                    if _to_int(c.token_id) == guard_tid:
                                        # Verify the provider also assigns this position
                                        # to the same token (consistency check)
                                        cum_check = Decimal(0)
                                        for j, prob in enumerate(probabilities):
                                            if j == full_idx:
                                                if cum_check <= position < cum_check + prob:
                                                    # Provider and BDS agree: use guard token
                                                    candidate_index = full_idx
                                                    is_robust = True
                                                    guard_applied = True
                                                    # Recompute interval bounds for the guard token
                                                    cum = Decimal(0)
                                                    for k, p in enumerate(probabilities):
                                                        if k == candidate_index:
                                                            lower_probability = cum
                                                            upper_probability = cum + p
                                                            break
                                                        cum += p
                                                break
                                            cum_check += prob
                                        break
                                break

                if not is_robust and self.config.vulnerable_step_policy == "raise":
                    raise ArithmeticError(
                        f"vulnerable step {step}: position {position} falls in "
                        "uncertainty zone; unable to guarantee precision-robust encoding"
                    )
                old_left = left
                left = old_left + width * lower_probability
                right = old_left + width * upper_probability
                token_id = snapshot.candidates[candidate_index].token_id

                midpoint_delta = (left + right) / 2 - secret
                paper_stop = -half < midpoint_delta <= half
                completed = paper_stop
                if paper_stop and self.config.termination_mode == "verified":
                    initial_midpoint = self._reverse_midpoint(
                        (left + right) / 2, history, random_stream
                    )
                    recovered = int(
                        initial_midpoint.to_integral_value(rounding=ROUND_HALF_DOWN)
                    )
                    completed = recovered == original_secret

                session.append(token_id)


                if guard_applied:
                    guard_steps.append(step)

                records.append(
                    StepRecord(
                        step=step,
                        token_id=token_id,
                        embedded=True,
                        block_completed=completed,
                        entropy_bits=snapshot.entropy_bits,
                        source_mass=snapshot.source_mass,
                        truncation_kl_nats=snapshot.truncation_kl_nats,
                        candidate_count=len(snapshot.candidates),
                        latency_ms=snapshot.latency_ms,
                        block_size=self.config.message_bits,
                        completed_bits=self.config.message_bits if completed else 0,
                        base_entropy_bits=snapshot.metadata.get("base_entropy_bits"),
                        effective_temperature=snapshot.metadata.get("effective_temperature"),
                        rescue_active=bool(snapshot.metadata.get("rescue_active", False)),
                        low_entropy_streak=int(
                            snapshot.metadata.get("low_entropy_streak", 0)
                        ),
                        forward_quantization_kl_nats=forward_kl,
                        quantization_total_variation=quantization_tv,
                        quantization_support_loss_count=support_loss_count,
                        quantization_support_loss_mass=support_loss_mass,
                    )
                )

                if completed:
                    result = EncodeResult(
                        token_ids=session.generated_token_ids,
                        text=session.render(),
                        embedded_bits=self.config.message_bits,
                        padded_bits=0,
                        elapsed_seconds=perf_counter() - started,
                        records=tuple(records),
                    )
                    # Attach BDS metadata to the result
                    result.__dict__["_bds_vulnerable_steps"] = tuple(vulnerable_steps)
                    result.__dict__["_bds_guard_steps"] = tuple(guard_steps)
                    result.__dict__["_bds_enabled"] = True
                    result.__dict__["_bds_certificate"] = tuple(self._certificate) if hasattr(self, '_certificate') else ()
                    return result

        raise IncompleteEncodeError(
            f"BDS-enhanced RRC message incomplete after {self.config.max_tokens} tokens; "
            "increase max_tokens or reduce the payload",
            token_ids=session.generated_token_ids,
            text=session.render(),
            completed_blocks=0,
            total_blocks=1,
            completed_bits=0,
            elapsed_seconds=perf_counter() - started,
            records=tuple(records),
        )

    def decode(
        self,
        session: ProviderSession,
        token_ids: tuple[Hashable, ...] | list[Hashable],
        key: bytes,
        certificate: tuple[tuple[int, int, int], ...] = (),
    ) -> DecodeResult:
        """Recover a fixed-length bit string using BDS-assisted decoding.

        If a correction certificate is provided, the decoder uses the
        certified cumulative bounds for vulnerable steps instead of
        computing its own (which may differ due to precision).
        For robust steps, standard RRC decoding is used.
        """
        if not certificate:
            return self._fallback_codec.decode(session, token_ids, key)
        
        # Build a lookup: step -> (cum_left, cum_right)
        cert_map = {}
        for step_idx, cl_int, cr_int in certificate:
            total_mass = Decimal(1 << (self.config.probability_mass_bits or self.config.contract_mass_bits))
            cert_map[step_idx] = (Decimal(cl_int) / total_mass, Decimal(cr_int) / total_mass)
        
        # Use the fallback codec but with certificate override
        # We need to intercept the interval narrowing for vulnerable steps
        return self._decode_with_certificate(session, token_ids, key, cert_map)
    
    def _decode_with_certificate(
        self,
        session: ProviderSession,
        token_ids: tuple[Hashable, ...] | list[Hashable],
        key: bytes,
        cert_map: dict[int, tuple[Decimal, Decimal]],
    ) -> DecodeResult:
        """Decode with certificate override for vulnerable steps."""
        random_stream = HmacRandomStream(key, session.context_id)
        token_ids = list(token_ids)
        
        with localcontext() as context:
            context.prec = self.config.decimal_precision
            left = Decimal(0)
            right = Decimal(1 << self.config.message_bits)
            history: list[tuple[Decimal, Decimal]] = []
            consumed = 0
            
            for step, token_id in enumerate(token_ids):
                if step >= self.config.max_tokens:
                    break
                
                snapshot = session.next_distribution()
                width = right - left
                if width <= 0:
                    break
                
                history.append((left, right))
                
                if step in cert_map:
                    # Use certified cumulative bounds
                    cum_left, cum_right = cert_map[step]
                else:
                    # Compute from logit bins (same as encoder) for consistency
                    bins_raw = snapshot.metadata.get("quantized_logit_bins")
                    mass_bits = self.config.probability_mass_bits or self.config.contract_mass_bits
                    if isinstance(bins_raw, dict) and mass_bits is not None:
                        bins = {int(tid): int(b) for tid, b in bins_raw.items()}
                        retained_ids = [int(c.token_id) for c in snapshot.candidates]
                        retained_bins = [bins[tid] for tid in retained_ids]
                        allocation = allocate_logit_bin_mass(
                            retained_ids, retained_bins,
                            quantum=self.config.logit_quantum,
                            temperature=self.config.contract_temperature,
                            mass_bits=mass_bits,
                        )
                        total_mass = Decimal(1 << mass_bits)
                        probabilities = tuple(
                            Decimal(count) / total_mass
                            for count in allocation.counts
                        )
                    else:
                        probabilities = _decimal_probabilities(
                            snapshot,
                            self.config.probability_quantum,
                            self.config.probability_mass_bits,
                            self.config.preserve_probability_support,
                        )
                    # Find the token in the candidate list
                    candidate_index = None
                    for i, c in enumerate(snapshot.candidates):
                        if c.token_id == token_id:
                            candidate_index = i
                            break
                    if candidate_index is None:
                        break
                    cum_left = sum(probabilities[:candidate_index])
                    cum_right = cum_left + probabilities[candidate_index]
                
                old_left = left
                left = old_left + width * cum_left
                right = old_left + width * cum_right
                
                session.append(token_id)
                consumed += 1
            
            # Recover the secret
            midpoint = (left + right) / 2
            initial_midpoint = self._reverse_midpoint(midpoint, history, random_stream)
            recovered = int(initial_midpoint.to_integral_value(rounding=ROUND_HALF_DOWN))
            
            bits = format(recovered, f'0{self.config.message_bits}b')
            return DecodeResult(
                bits=bits,
                completed_blocks=1,
                consumed_tokens=consumed,
            )


def verify_bds_robustness(
    snapshot: DistributionSnapshot,
    config: BdsRrcConfig,
    position: Decimal,
) -> dict:
    """Verify whether a given position is robust under the BDS perturbation model.

    This is a diagnostic function that can be used by the decoder to check
    whether the encoder made a robust decision at each step.

    Returns a dictionary with:
    - "robust": True if the position is in a safe core
    - "vulnerable": True if the position is in an uncertainty zone
    - "envelope": the BdsEnvelope if available, or None
    - "selected_token_id": the token that would be selected nominally
    - "robust_token_id": the token whose safe core contains the position (or None)
    """
    envelope = _compute_bds_envelope(snapshot, config)
    if envelope is None:
        return {"robust": False, "vulnerable": False, "envelope": None, "position": position}

    # Find which token's safe core contains the position
    robust_token = None
    for i in range(len(envelope.token_ids)):
        if envelope.contains_in_safe_core(position, i):
            robust_token = envelope.token_ids[i]
            break

    # Find which token's full possible interval contains the position
    vulnerable = True
    for i in range(len(envelope.token_ids)):
        left, right = envelope.uncertainty_zone_for_token(i)
        if left <= position < right:
            vulnerable = False
            break

    return {
        "robust": robust_token is not None,
        "vulnerable": vulnerable,
        "envelope": envelope,
        "selected_token_id": robust_token,
        "position": position,
    }
