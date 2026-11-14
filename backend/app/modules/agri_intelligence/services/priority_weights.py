from ..schemas.recommendations import FarmerPriority, PriorityWeights


def provisional_default_weights() -> PriorityWeights:
    return PriorityWeights()


def normalize_priorities(priorities: list[FarmerPriority]) -> list[str]:
    return list(dict.fromkeys(priority.value for priority in priorities))
