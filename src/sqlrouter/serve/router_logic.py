"""Routing decision logic and cost estimation."""


def decide_route(
    score: float,
    threshold: float,
    mode: str,
) -> tuple[str, str]:
    """Make routing decision based on uncertainty score.
    
    Args:
        score: Uncertainty score from probe (higher = more uncertain)
        threshold: Threshold for escalation
        mode: Routing mode ("auto", "local", or "api")
        
    Returns:
        Tuple of (route, reason) where:
        - route is "local" or "api"
        - reason is human-readable explanation
    """
    if mode == "local":
        return "local", "You forced the local model."
    
    if mode == "api":
        return "api", "You forced the frontier API."
    
    # Auto mode: use the probe
    if score <= threshold:
        return "local", (
            f"Uncertainty {score:.2f} is at or below the threshold {threshold:.2f}, "
            f"so the local model answers."
        )
    else:
        return "api", (
            f"Uncertainty {score:.2f} is above the threshold {threshold:.2f}, "
            f"so the question goes to the frontier API."
        )


def estimate_cost(
    costs: dict,
    route: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> float:
    """Estimate cost for a query.
    
    Args:
        costs: Cost dict from config
        route: "local" or "api"
        input_tokens: API input tokens (if known)
        output_tokens: API output tokens (if known)
        
    Returns:
        Estimated cost in USD
    """
    # Probe always runs (prefill)
    cost = costs["c_prefill"]
    
    if route == "local":
        # Add decode cost
        cost += costs["c_decode"]
    else:
        # API call
        if input_tokens > 0 and output_tokens > 0:
            # Use actual token counts
            cost += (
                input_tokens * costs["api_in_per_tok"]
                + output_tokens * costs["api_out_per_tok"]
            )
        else:
            # Use average estimate
            cost += costs["c_api"]
    
    return cost


def estimate_always_api_cost(costs: dict) -> float:
    """Estimate cost if query went to API.
    
    Args:
        costs: Cost dict from config
        
    Returns:
        Estimated cost in USD
    """
    return costs["c_api"]
