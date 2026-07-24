from __future__ import annotations

from typing import cast

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Table, UniqueConstraint

from app.db.models.asset_instrument import AssetInstrument
from app.db.models.provider_instrument_mapping import ProviderInstrumentMapping


def test_asset_instrument_model_has_provider_independent_catalog_columns() -> None:
    table = cast(Table, AssetInstrument.__table__)

    assert table.name == "asset_instruments"
    assert table.c.id.primary_key is True
    assert table.c.slug.unique is True
    assert table.c.id.type.__class__.__name__ == "UUID"
    required_columns = {"asset_class", "market_type", "calendar_kind", "metadata_version"}
    assert required_columns <= set(table.c.keys())
    assert not {"provider_symbol", "provider_key", "credential", "api_key"} & set(table.c.keys())


def test_provider_mapping_model_has_business_constraints_and_restricted_delete() -> None:
    table = cast(Table, ProviderInstrumentMapping.__table__)
    unique_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    check_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    foreign_keys = [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]

    assert table.name == "provider_instrument_mappings"
    assert {
        "uq_provider_mapping_instrument_provider",
        "uq_provider_mapping_provider_symbol",
    } <= unique_names
    assert {
        "ck_provider_mapping_priority_positive",
        "ck_provider_mapping_version_positive",
    } <= check_names
    assert len(foreign_keys) == 1
    assert foreign_keys[0].elements[0].ondelete == "RESTRICT"
    assert not {"credential", "api_key", "url", "payload"} & set(table.c.keys())


def test_mapping_partial_enabled_priority_index_is_declared() -> None:
    table = cast(Table, ProviderInstrumentMapping.__table__)
    partial_index = next(
        index for index in table.indexes if index.name == "uq_provider_mapping_enabled_priority"
    )

    assert partial_index.unique is True
    predicate = partial_index.dialect_options["postgresql"]["where"]
    assert str(predicate) == "is_enabled"
