"""Fixture commands for analytics-base assembly and preprocessing."""

from __future__ import annotations

import json

from pathlib import Path
from typing import cast

import typer


JsonScalar = str | int | float
Record = dict[str, JsonScalar]
RecordMap = dict[str, Record]

DATA_DIR = Path("data")
CURRENT_YEAR = 2026
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
def build_analytics_base() -> None:
    """Build a project-level analytics base from synced datasets."""
    listings = load_records(DATA_DIR / "listings.json")
    neighborhood_profiles = load_records(DATA_DIR / "neighborhood_profiles.json")
    market_comps = load_records(DATA_DIR / "market_comps.json")

    analytics_base = {}
    for listing_id, listing in listings.items():
        neighborhood = str(listing["neighborhood"])
        profile = neighborhood_profiles[neighborhood]
        comps = market_comps[neighborhood]
        list_price_per_sqft = round(int(listing["list_price"]) / int(listing["sqft"]), 2)
        analytics_base[listing_id] = {
            "neighborhood": neighborhood,
            "sqft": int(listing["sqft"]),
            "beds": int(listing["beds"]),
            "baths": int(listing["baths"]),
            "listing_age": CURRENT_YEAR - int(listing["year_built"]),
            "school_score": int(profile["school_score"]),
            "transit_score": int(profile["transit_score"]),
            "median_price_per_sqft": float(profile["median_price_per_sqft"]),
            "list_price_per_sqft": list_price_per_sqft,
            "price_gap_to_neighborhood": round(
                list_price_per_sqft - float(profile["median_price_per_sqft"]),
                2,
            ),
            "price_gap_to_comps": round(
                list_price_per_sqft - float(comps["sale_price_per_sqft"]),
                2,
            ),
        }

    write_json(DATA_DIR / "analytics_base.json", analytics_base)


@app.command()
def normalize_listings() -> None:
    """Derive stable listing-level signals."""
    listings = load_records(DATA_DIR / "listings.json")

    listings_normalized = {
        listing_id: {
            "neighborhood": str(listing["neighborhood"]),
            "sqft": int(listing["sqft"]),
            "listing_age": CURRENT_YEAR - int(listing["year_built"]),
            "list_price_per_sqft": round(int(listing["list_price"]) / int(listing["sqft"]), 2),
            "bath_to_bed_ratio": round(int(listing["baths"]) / int(listing["beds"]), 2),
        }
        for listing_id, listing in listings.items()
    }

    write_json(DATA_DIR / "listings_normalized.json", listings_normalized)


@app.command()
def normalize_comps() -> None:
    """Derive market signals from comparable sales."""
    market_comps = load_records(DATA_DIR / "market_comps.json")

    market_comps_normalized = {
        neighborhood: {
            "sale_price_per_sqft": float(comp["sale_price_per_sqft"]),
            "recent_days_on_market": int(comp["recent_days_on_market"]),
            "pricing_pressure": round(
                (45 - int(comp["recent_days_on_market"])) / 10,
                2,
            ),
        }
        for neighborhood, comp in market_comps.items()
    }

    write_json(DATA_DIR / "market_comps_normalized.json", market_comps_normalized)


@app.command()
def join_market_context() -> None:
    """Join listing and market signals into the modeling context table."""
    analytics_base = load_records(DATA_DIR / "analytics_base.json")
    listings_normalized = load_records(DATA_DIR / "listings_normalized.json")
    market_comps_normalized = load_records(DATA_DIR / "market_comps_normalized.json")

    market_context = {}
    for listing_id, listing in listings_normalized.items():
        neighborhood = str(listing["neighborhood"])
        base = analytics_base[listing_id]
        comps = market_comps_normalized[neighborhood]
        market_context[listing_id] = {
            "sqft": int(listing["sqft"]),
            "listing_age": int(listing["listing_age"]),
            "bath_to_bed_ratio": float(listing["bath_to_bed_ratio"]),
            "list_price_per_sqft": float(listing["list_price_per_sqft"]),
            "school_score": int(base["school_score"]),
            "transit_score": int(base["transit_score"]),
            "median_price_per_sqft": float(base["median_price_per_sqft"]),
            "price_gap_to_neighborhood": float(base["price_gap_to_neighborhood"]),
            "price_gap_to_comps": float(base["price_gap_to_comps"]),
            "recent_days_on_market": int(comps["recent_days_on_market"]),
            "pricing_pressure": float(comps["pricing_pressure"]),
        }

    write_json(DATA_DIR / "market_context.json", market_context)


if __name__ == "__main__":
    app()
