
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
        cum_left = sum(probabilities[:selected_index])
        cum_right = cum_left + probabilities[selected_index]
        return False, cum_left, cum_right
    
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
    
    range_width = max_cum_left - min_cum_left
    threshold = Decimal(1) / total_mass
    is_robust = range_width <= threshold
    
    return is_robust, nom_cum_left, nom_cum_right
