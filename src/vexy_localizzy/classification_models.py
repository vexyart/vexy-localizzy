# this_file: src/vexy_localizzy/classification_models.py
"""Model policy parsing and bounded individual classification requests."""

from collections.abc import Callable, Sequence

from vexy_localizzy.classification import parse_votes
from vexy_localizzy.provider_errors import ModelResponse, ProviderUnavailable

Request = Callable[[str, str, str], str | ModelResponse]


def assign_models(
    chains: Sequence[Sequence[str]],
    identities: dict[str, str] | None = None,
    *,
    initial: dict[int, str] | None = None,
) -> dict[int, str]:
    """Extend an existing valid assignment, reassigning slots only when needed."""
    identities = identities or {}
    owners = {
        identities.get(model, model): (slot, model)
        for slot, model in (initial or {}).items()
    }

    def assign(slot: int, seen: set[str]) -> bool:
        for model in chains[slot]:
            identity = identities.get(model, model)
            if identity not in owners:
                owners[identity] = (slot, model)
                return True
        for model in chains[slot]:
            identity = identities.get(model, model)
            if identity not in seen:
                seen.add(identity)
                if assign(owners[identity][0], seen):
                    owners[identity] = (slot, model)
                    return True
        return False

    for slot in range(len(chains)):
        if slot not in {owner for owner, _ in owners.values()}:
            assign(slot, set())
    return {slot: model for slot, model in owners.values()}


def model_chains(
    models: Sequence[str], fallbacks: dict[str, Sequence[str]] | None
) -> tuple[tuple[str, ...], ...]:
    if (
        isinstance(models, str)
        or len(models) != 3
        or len(set(models)) != 3
        or any(not isinstance(m, str) or not m for m in models)
    ):
        raise ValueError("Three distinct model identities are required")
    fallbacks = fallbacks or {}
    if set(fallbacks) - set(models):
        raise ValueError("Invalid fallback model policy")
    for values in fallbacks.values():
        if (
            isinstance(values, str)
            or any(not isinstance(value, str) or not value for value in values)
            or len(set(values)) != len(values)
        ):
            raise ValueError("Invalid fallback model policy")
    return tuple(
        tuple(dict.fromkeys((model, *fallbacks.get(model, ())))) for model in models
    )


def request_votes(
    request: Request,
    model: str,
    prompt: str,
    payload: str,
    count: int,
    parser: Callable = parse_votes,
) -> tuple[
    list[tuple[str, str | None]], str | None, ProviderUnavailable | None, str | None
]:
    """Retry malformed output at most three times; immediately defer known outages."""
    attempts = []
    for _ in range(3):
        response = ""
        try:
            reply = request(model, prompt, payload)
            if not isinstance(reply, (str, ModelResponse)):
                raise ValueError("Provider response must be text or ModelResponse")
            response = reply.content if isinstance(reply, ModelResponse) else reply
            reported = (
                reply.reported_model if isinstance(reply, ModelResponse) else None
            )
            parser(response, count)
            attempts.append((response, None))
            return attempts, response, None, reported
        except ProviderUnavailable as error:
            attempts.append((response, error.reason))
            return attempts, None, error, None
        except Exception as error:
            attempts.append((response, type(error).__name__))
    return attempts, None, None, None
