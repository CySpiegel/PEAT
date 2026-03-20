from __future__ import annotations

from collections import ChainMap
from collections.abc import Callable
from operator import attrgetter
from typing import Any

from peat import PeatError, config, log, utils

from .base_model import BaseModel


class DeepChainMap(ChainMap):
    """
    Variant of :class:`collections.ChainMap` that supports edits of
    nested :class:`dict` objects.

    In PEAT, this is used for providing nested sets of device and protocol
    options (configurations) with the ability the modify the underlying
    sources (e.g. a set of global runtime defaults) and still preserve
    the order of precedence and transparent overriding (e.g. options
    configured at runtime for a specific device will still override the
    global defaults, even though the global defaults were also modified
    at runtime).

    Nested objects can override keys at various levels without overriding
    the parent structure. This is best explained via examples.

    .. code-block:: python

       >>> from peat.data.data_utils import DeepChainMap
       >>> layer1 = {}
       >>> layer2 = {"key": 9999}
       >>> layer3 = {"deep_object": {"deep_key": "The Deep"}}
       >>> deep_map = DeepChainMap(layer1, layer2, layer3)
       >>> deep_map["key"]
       9999
       >>> layer1["key"] = -1111
       >>> deep_map["key"]
       -1111
       >>> layer2["key"]
       9999
       >>> deep_map["deep_object"]["deep_key"]
       'The Deep'
       >>> layer1["deep_object"] = {"another_key": "another_value"}
       >>> deep_map["deep_object"]["deep_key"]
       'The Deep'
       >>> deep_map["deep_object"]["another_key"]
       'another_value'
    """

    def __getitem__(self, key):
        values = []
        for mapping in self.maps:
            try:
                values.append(mapping[key])
            except KeyError:
                pass
        if not values:
            return self.__missing__(key)
        first = values.pop(0)
        rv = first
        if isinstance(first, dict):
            values = [x for x in values if isinstance(x, dict)]
            if values:
                values.insert(0, first)
                rv = self.__class__(*values)
        return rv

    def to_dict(self, to_convert: DeepChainMap | None = None) -> dict:
        """Create a copy of the object as a normal :class:`dict`."""
        if to_convert is None:
            to_convert = self

        converted = {}

        for key, value in dict(to_convert).items():
            if isinstance(value, DeepChainMap):
                converted[key] = self.to_dict(value)
            else:
                converted[key] = value

        return converted


def lookup_by_str(container: list[BaseModel], value: BaseModel, lookup: str) -> int | None:
    """
    String of attribute to search for, e.g. ``"ip"`` to lookup interfaces
    using ``Interface.ip`` attribute on the value.
    """
    if not container:
        return None

    if hasattr(value, lookup) and not value.is_default(lookup):
        value_to_find = getattr(value, lookup)
        if value_to_find not in [None, ""]:
            return find_position(container, lookup, value_to_find)

    return None


def find_position(obj: list[BaseModel], key: str, value: Any) -> int | None:
    """Find if and where an object with a given value is in a :class:`list`."""
    for index, item in enumerate(obj):
        if getattr(item, key, None) == value:
            return index

    return None


def match_all(obj_list: list[BaseModel], value: dict[str, Any]) -> int | None:
    """Search the list for objects where all values in value match."""
    if not value:
        return None

    for loc, item in enumerate(obj_list):
        # If all the values match their corresponding entries in item
        # then return it's location
        vals = item.dict(exclude_defaults=True, exclude_none=True)
        if all(vals.get(key) == value[key] for key in value.keys()):
            return loc

    return None


def strip_empty_and_private(
    obj: dict, strip_empty: bool = True, strip_private: bool = True
) -> dict:
    """Recursively removes empty values and keys starting with ``_``."""
    new = {}
    for key, value in obj.items():
        if strip_private and _is_private(key):
            continue

        elif strip_empty:
            # NOTE: checking type is required to prevent stripping "False", "-1", etc.
            if _is_empty(value):
                continue

            if isinstance(value, dict):
                stripped = strip_empty_and_private(value, strip_empty, strip_private)

                if strip_empty and not stripped:
                    continue
                else:
                    new[key] = stripped
            elif isinstance(value, list):
                # NOTE: lists are not recursively stripped
                new[key] = [
                    (
                        strip_empty_and_private(v, strip_empty, strip_private)
                        if isinstance(v, dict)
                        else v
                    )
                    for v in value
                    if not _is_empty(v)
                ]
            elif isinstance(value, set):
                for empty_val in ["", None]:
                    if empty_val in value:
                        value.remove(empty_val)

                if value:
                    new[key] = value
            else:
                new[key] = value
        else:
            new[key] = value

    return new


def _is_empty(v: Any | None) -> bool:
    return bool(v is None or (isinstance(v, (str, bytes, dict, list, set)) and not v))


def _is_private(key: Any) -> bool:
    return bool(isinstance(key, str) and key.startswith("_"))


def strip_key(obj: dict, bad_key: str) -> dict:
    """
    Recursively removes all matching keys from a :class:`dict`.

    .. warning::
       This will NOT strip values out of a :class:`list` of :class:`dict`!
    """
    new = {}

    for key, value in obj.items():
        if key != bad_key:
            if isinstance(value, dict):
                new[key] = strip_key(value, bad_key)
            else:
                new[key] = value

    return new


def only_include_keys(obj: dict, allowed_keys: str | list[str]) -> dict:
    """
    Filters any keys that don't match the allowed list of keys.
    """
    new = {}
    if isinstance(allowed_keys, str):
        allowed_keys = [allowed_keys]

    for key, value in obj.items():
        if key in allowed_keys:
            new[key] = value

    return new


def compare_dicts(d1: dict | None, d2: dict | None, keys: list[str]) -> bool:
    if not d1 or not d2 or not keys:
        raise PeatError("bad compare_dicts args")

    for key in keys:
        if d1.get(key) is None or d2.get(key) is None:
            continue
        if d1.get(key) != d2.get(key):
            return False

    return True


def _make_hashable(value: Any) -> Any:
    """Convert a value to a hashable representation for deduplication."""
    if isinstance(value, dict):
        return tuple(sorted((k, _make_hashable(v)) for k, v in value.items()))
    elif isinstance(value, (list, tuple)):
        return tuple(_make_hashable(v) for v in value)
    elif isinstance(value, set):
        return tuple(sorted(str(v) for v in value))
    return value


def dedupe_model_list(current: list[BaseModel]) -> list[BaseModel]:
    """
    Deduplicates a :class:`list` of :class:`~peat.data.base_model.BaseModel`
    objects while preserving the original order.

    Models that are a subset of another (contains some keys and values)
    will be merged together and their values combined.

    Uses hash-based exact duplicate removal (O(n)) followed by key-set
    grouping for subset detection, avoiding the previous O(n^2) pairwise
    comparison.

    Args:
        current: list of models to deduplicate

    Returns:
        List of deduplicated items
    """

    # Don't bother with empty or single-element lists
    if not current or len(current) < 2:
        return current

    if not isinstance(current[0], BaseModel):
        raise PeatError(f"expected BaseModel for dedupe_model_list, got {type(current[0])}")

    model_type = current[0].__repr_name__()  # type: str
    original_len = len(current)

    # Phase 1: Convert models to dicts once and remove exact duplicates via hashing.
    # This is O(n) and handles the most common case.
    seen_hashes = {}  # type: dict[tuple, int]
    unique = []  # type: list[tuple[BaseModel, dict]]

    for m in current:
        d = m.dict(exclude_defaults=True, exclude_none=True)
        h = _make_hashable(d)
        if h not in seen_hashes:
            seen_hashes[h] = len(unique)
            unique.append((m, d))

    # Phase 2: Subset merging.
    # Group items by their key-set (frozenset of dict keys). Subset relationships
    # can only exist between items whose key-sets have a strict subset relationship,
    # so we only compare across groups where one key-set is a subset of another.
    merged = set()  # type: set[int]

    # Group by key-set
    keyset_groups = {}  # type: dict[frozenset, list[int]]
    for i, (_, d) in enumerate(unique):
        ks = frozenset(d.keys())
        keyset_groups.setdefault(ks, []).append(i)

    # Sort key-sets by size (ascending) so smaller sets are checked as
    # potential subsets of larger sets
    keysets = sorted(keyset_groups.keys(), key=len)

    for ki, small_ks in enumerate(keysets):
        for kj in range(ki + 1, len(keysets)):
            large_ks = keysets[kj]
            if not small_ks < large_ks:
                continue

            # small_ks is a strict subset of large_ks.
            # Check each item in the small group against items in the large group.
            for si in keyset_groups[small_ks]:
                if si in merged:
                    continue
                _, small_dict = unique[si]

                for li in keyset_groups[large_ks]:
                    if li in merged:
                        continue
                    large_model, large_dict = unique[li]

                    # All of the smaller dict's key-value pairs must exist in the larger
                    if all(large_dict.get(k) == v for k, v in small_dict.items()):
                        merge_models(large_model, unique[si][0])
                        # Update cached dict after merge
                        new_dict = large_model.dict(exclude_defaults=True, exclude_none=True)
                        unique[li] = (large_model, new_dict)
                        merged.add(si)
                        break

    # Service model special case: status-based merging that doesn't follow
    # normal subset rules. Index by (port, protocol) for efficient lookup.
    if model_type == "Service":
        # Build index of items by (port, protocol) for fast candidate lookup
        port_proto_index = {}  # type: dict[tuple, list[int]]
        for i, (_, d) in enumerate(unique):
            if i in merged:
                continue
            key = (d.get("port"), d.get("protocol"))
            port_proto_index.setdefault(key, []).append(i)

        for i, (item_model, item_dict) in enumerate(unique):
            if i in merged:
                continue

            key = (item_dict.get("port"), item_dict.get("protocol"))
            candidates = port_proto_index.get(key, [])

            for j in candidates:
                if j == i or j in merged:
                    continue
                comp_model, comp_dict = unique[j]

                if (
                    comp_dict.get("status") == "verified"
                    or (comp_dict.get("status") == "open" and item_dict.get("status") == "closed")
                ) and compare_dicts(item_dict, comp_dict, ["port", "protocol"]):
                    merge_models(comp_model, item_model)
                    new_dict = comp_model.dict(exclude_defaults=True, exclude_none=True)
                    unique[j] = (comp_model, new_dict)
                    merged.add(i)
                    break

    deduped = [model for i, (model, _) in enumerate(unique) if i not in merged]  # type: list[BaseModel]

    removed = original_len - len(deduped)
    if removed and config.DEBUG:
        log.trace(
            f"Removed {removed} duplicates from list of {original_len} "
            f"{model_type} items ({len(deduped)} items remaining in list)"
        )

    return deduped


def none_aware_attrgetter(attrs: tuple[str]) -> Callable:
    """
    Variant of ``operator.attrgetter()`` that
    handles values that may be :obj:`None`.
    """

    def g(obj) -> tuple:
        pairs = []

        for attr in attrs:
            value = getattr(obj, attr)
            pairs.append(value is None)
            pairs.append(value)

        return tuple(pairs)

    return g


def sort_model_list(model_list: list[BaseModel]) -> None:
    """
    In-place sort of a :class:`list` of models.

    The attribute ``_sort_by_fields`` on the first model
    in the list is used to sort the models.

    Raises:
        PeatError: invalid type in list or ``_sort_by_fields``
        is undefined on the model being sorted
    """
    if not model_list or len(model_list) < 2:
        return

    if not isinstance(model_list[0], BaseModel):
        raise PeatError(f"expected BaseModel for sort_model_list, got {type(model_list[0])}")

    if not getattr(model_list[0], "_sort_by_fields", None):
        raise PeatError(
            f"No '_sort_by_fields' attribute on model class "
            f"'{model_list[0].__repr_name__()}' to use for sorting"
        )

    if config.DEBUG >= 3:
        log.debug(f"Sorting '{model_list[0].__repr_name__()}' list with {len(model_list)} items")

    model_list.sort(key=none_aware_attrgetter(model_list[0]._sort_by_fields))


def merge_models(dest: BaseModel, source: BaseModel) -> None:
    """
    Copy values from one model to another.
    """
    if not dest or not source:
        return

    if not isinstance(source, BaseModel):
        raise PeatError(f"non-model source: {source}")

    dst_type = dest.__repr_name__()  # type: str
    src_type = source.__repr_name__()  # type: str

    if dst_type != src_type:
        raise PeatError(f"merge_models: '{dst_type}' != '{src_type}'")

    # TODO: hack to make DeviceData merging work
    if dst_type == "DeviceData":
        if source.module:
            for mod_to_merge in source.module:
                # If there's an existing module in same slot, merge the contents
                for curr_mod in dest.module:
                    if (
                        curr_mod.slot and mod_to_merge.slot and curr_mod.slot == mod_to_merge.slot
                    ) or (
                        curr_mod.serial_number
                        and mod_to_merge.serial_number
                        and curr_mod.serial_number == mod_to_merge.serial_number
                    ):
                        merge_models(curr_mod, mod_to_merge)
                        break
                # Append the module
                else:
                    dest.module.append(mod_to_merge)
            dest.module.sort(key=attrgetter("slot"))  # Sort modules by Slot ID

    # WARNING: do NOT call source.dict(...) here!
    # dict(source) converts just the top-level model to a dict, not sub-models.
    # source.dict(...) will convert all sub-models to dicts, which is no bueno.
    source_dict = dict(source)

    overwrite = False

    if dst_type == "Service" and (
        source_dict.get("status") == "verified"
        or (source_dict.get("status") == "open" and dest.status == "closed")
    ):
        overwrite = True

    for attr, new_value in source_dict.items():
        # If it's None for some reason (e.g. a default), we don't care
        if new_value is None:
            continue

        if not hasattr(dest, attr):
            raise PeatError(f"No attribute for key '{attr}'. Value: {new_value}")

        # !! hack to make DeviceData merging work !!
        if dst_type == "DeviceData" and attr == "module":
            continue

        current_value = getattr(dest, attr)

        # Skip if the values match
        # Skip if the source is a default model
        if new_value == current_value or (
            isinstance(source, BaseModel) and source.is_default(attr)
        ):
            continue

        # If they're models (e.g., "Hardware"), use merge_models to handle the merging
        elif isinstance(current_value, BaseModel):
            merge_models(current_value, new_value)

        # Merge dicts, preserving existing values
        # NOTE: this is usually ".extra" fields
        elif isinstance(current_value, dict):
            utils.merge(current_value, new_value, no_copy=True)

        # Sets automatically remove duplicate values
        elif isinstance(current_value, set):
            current_value.update(new_value)

        # Combine, deduplicate, and sort lists
        elif isinstance(current_value, list):
            if current_value and new_value:
                if isinstance(current_value[0], BaseModel):
                    combined = current_value + list(new_value)
                    deduped = dedupe_model_list(combined)
                    sort_model_list(deduped)
                    setattr(dest, attr, deduped)
                else:
                    for new_item in new_value:
                        if not any(new_item == c for c in current_value):
                            current_value.append(new_item)
            elif new_value:
                setattr(dest, attr, new_value)

        # If the destination value is a default value, then copy the value
        # This won't overwriting existing values on destination
        # NOTE: using setattr() will also trigger value validation by Pydantic
        elif dest.is_default(attr):
            setattr(dest, attr, new_value)

        elif overwrite:
            msg = (
                f"Changed existing value for field '{attr}' with "
                f"'{new_value}' (old value: '{current_value}')"
            )
            if attr == "status":
                log.debug(msg)
            else:
                log.warning(msg)

            setattr(dest, attr, new_value)

        elif config.DEBUG >= 4:
            log.warning(
                f"Skipping merge of existing non-default attribute '{attr}' for "
                f"'{dest.__class__.__name__}' model (new_value={new_value} "
                f"current_value={current_value})"
            )
