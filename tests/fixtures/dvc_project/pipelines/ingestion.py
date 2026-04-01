"""Fixture commands for raw data ingestion."""

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
def sync_listings() -> None:
    """Normalize the raw listings export into stable records."""
    listings_raw = load_records(DATA_DIR / "listings_raw.json")

    listings = {
        listing_id: {
            "neighborhood": str(record["neighborhood"]),
            "sqft": int(record["sqft"]),
            "beds": int(record["beds"]),
            "baths": int(record["baths"]),
            "year_built": int(record["year_built"]),
            "list_price": int(record["list_price"]),
        }
        for listing_id, record in listings_raw.items()
    }

    write_json(DATA_DIR / "listings.json", listings)


@app.command()
def sync_neighborhood_profiles() -> None:
    """Normalize neighborhood profiles into reusable reference data."""
    profiles_raw = load_records(DATA_DIR / "neighborhood_profiles_raw.json")

    neighborhood_profiles = {
        neighborhood: {
            "median_price_per_sqft": float(record["median_price_per_sqft"]),
            "school_score": int(record["school_score"]),
            "transit_score": int(record["transit_score"]),
        }
        for neighborhood, record in profiles_raw.items()
    }

    write_json(DATA_DIR / "neighborhood_profiles.json", neighborhood_profiles)


@app.command()
def sync_market_comps() -> None:
    """Normalize recent comparable sales by neighborhood."""
    market_comps_raw = load_records(DATA_DIR / "market_comps_raw.json")

    market_comps = {
        neighborhood: {
            "recent_sale_price": int(record["recent_sale_price"]),
            "recent_sale_sqft": int(record["recent_sale_sqft"]),
            "recent_days_on_market": int(record["recent_days_on_market"]),
            "sale_price_per_sqft": round(
                int(record["recent_sale_price"]) / int(record["recent_sale_sqft"]),
                2,
            ),
        }
        for neighborhood, record in market_comps_raw.items()
    }

    write_json(DATA_DIR / "market_comps.json", market_comps)


if __name__ == "__main__":
    app()
