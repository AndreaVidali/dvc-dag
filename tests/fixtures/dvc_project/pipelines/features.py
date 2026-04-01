"""Fixture commands for house-price feature engineering."""

from __future__ import annotations

import json

from pathlib import Path
from typing import cast

import typer


JsonScalar = str | int | float
Record = dict[str, JsonScalar]
RecordMap = dict[str, Record]

DATA_DIR = Path("data")
app = typer.Typer()


def load_records(path: Path) -> RecordMap:
    """Load a nested JSON mapping from disk."""
    with path.open() as file:
        return cast("RecordMap", json.load(file))


def write_json(path: Path, payload: object) -> None:
    """Write a JSON object to disk."""
    with path.open("w") as file:
        json.dump(payload, file, indent=4)


@app.command()
def build_location_features() -> None:
    """Build location-oriented features from market context."""
    market_context = load_records(DATA_DIR / "market_context.json")

    location_features = {
        listing_id: {
            "neighborhood_quality": round(
                int(record["school_score"]) * 0.65 + int(record["transit_score"]) * 0.35,
                2,
            ),
            "market_heat": round(
                float(record["pricing_pressure"]) * 10
                + (35 - int(record["recent_days_on_market"])),
                2,
            ),
        }
        for listing_id, record in market_context.items()
    }

    write_json(DATA_DIR / "location_features.json", location_features)


@app.command()
def build_property_features() -> None:
    """Build property-oriented features from market context."""
    market_context = load_records(DATA_DIR / "market_context.json")

    property_features = {
        listing_id: {
            "size_score": round(int(record["sqft"]) / 400, 2),
            "layout_balance": round(float(record["bath_to_bed_ratio"]) * 8, 2),
            "pricing_alignment": round(
                12 - abs(float(record["price_gap_to_comps"])) / 8,
                2,
            ),
            "age_penalty": round(int(record["listing_age"]) / 10, 2),
        }
        for listing_id, record in market_context.items()
    }

    write_json(DATA_DIR / "property_features.json", property_features)


@app.command()
def assemble_feature_matrix() -> None:
    """Assemble the final modeling feature matrix."""
    location_features = load_records(DATA_DIR / "location_features.json")
    property_features = load_records(DATA_DIR / "property_features.json")

    feature_matrix = {
        listing_id: location_features[listing_id] | property_features[listing_id]
        for listing_id in location_features
    }

    write_json(DATA_DIR / "feature_matrix.json", feature_matrix)


if __name__ == "__main__":
    app()
