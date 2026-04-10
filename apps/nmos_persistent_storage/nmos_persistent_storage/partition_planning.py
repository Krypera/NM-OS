from __future__ import annotations

MIN_CREATE_BYTES = 1024 * 1024 * 1024
ALIGNMENT_BYTES = 1024 * 1024
SUPPORTED_PARTITION_LABELS = {"gpt"}


def boot_disk_is_supported(transport: str | None, removable: bool, hotplug: bool) -> bool:
    del hotplug
    return transport == "usb" or removable


def align_up(value: int, alignment: int) -> int:
    if alignment <= 0:
        return value
    remainder = value % alignment
    if remainder == 0:
        return value
    return value + alignment - remainder


def next_partition_number(partitions: list[dict]) -> int:
    numbers = [int(partition.get("number", 0)) for partition in partitions if partition.get("number")]
    return max(numbers, default=0) + 1


def partition_table_label_is_supported(label: str | None) -> bool:
    return str(label or "").lower() in SUPPORTED_PARTITION_LABELS


def plan_trailing_partition(
    *,
    device_size_bytes: int,
    partitions: list[dict],
    minimum_free_bytes: int = MIN_CREATE_BYTES,
    alignment_bytes: int = ALIGNMENT_BYTES,
) -> dict:
    last_end = 0
    for partition in partitions:
        start = int(partition.get("start_bytes", 0))
        size = int(partition.get("size_bytes", 0))
        last_end = max(last_end, start + size)

    start_bytes = max(alignment_bytes, align_up(last_end, alignment_bytes))
    free_bytes = max(0, device_size_bytes - start_bytes)
    return {
        "partition_number": next_partition_number(partitions),
        "start_bytes": start_bytes,
        "free_bytes": free_bytes,
        "can_create": free_bytes >= minimum_free_bytes,
        "reason": "ready" if free_bytes >= minimum_free_bytes else "no_free_space",
    }
