"""Load or refresh canonical reference data.

Idempotent: rows are matched on ``(slug, owner IS NULL)`` and updated in place,
so re-running after a fixture grows does not duplicate anything and does not
disturb the foreign keys users' coffees already hold.

Only canonical rows are touched. A user's custom entries are never read or
written here.
"""

import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from coffeenut.catalog.models import (
    BrewMethod,
    Country,
    ProcessMethod,
    Region,
    TastingNote,
    Varietal,
)
from coffeenut.common.models import ReferenceSource

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _load(name: str) -> list[dict[str, Any]]:
    path = FIXTURES / name
    if not path.exists():
        raise CommandError(f"Missing fixture: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


class Command(BaseCommand):
    help = "Load or refresh canonical catalog reference data."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--quiet", action="store_true", help="Only report the final summary.")

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        quiet = options["quiet"]
        counts: dict[str, tuple[int, int]] = {}

        counts["countries"] = self._seed_countries()
        counts["regions"] = self._seed_regions()
        counts["processes"] = self._seed_simple(ProcessMethod, "processes.json", ("category",))
        counts["brew methods"] = self._seed_simple(
            BrewMethod, "brew_methods.json", ("parameter_schema",)
        )
        counts["varietals"] = self._seed_self_referencing(Varietal, "varietals.json", ())
        counts["tasting notes"] = self._seed_self_referencing(
            TastingNote, "tasting_notes.json", ("color",)
        )

        if not quiet:
            for label, (created, updated) in counts.items():
                self.stdout.write(f"  {label:<15} {created:>4} created  {updated:>4} updated")
        total = sum(c + u for c, u in counts.values())
        self.stdout.write(self.style.SUCCESS(f"Catalog seeded: {total} canonical rows."))

        # Roasters and producers are intentionally not seeded. Curating them
        # needs sourcing we have not done yet (docs/architecture.md §11), and a
        # half-complete canonical list is worse than none: users would trust it,
        # miss their roaster, and create a duplicate anyway.

    def _upsert(self, model: Any, slug: str, defaults: dict[str, Any]) -> tuple[Any, bool]:
        obj, created = model.objects.update_or_create(
            slug=slug,
            owner=None,
            defaults={**defaults, "source": ReferenceSource.SEED},
        )
        return obj, created

    def _seed_countries(self) -> tuple[int, int]:
        created = updated = 0
        for row in _load("countries.json"):
            _, was_created = self._upsert(
                Country,
                slugify(row["name"])[:220],
                {
                    "name": row["name"],
                    "iso_alpha2": row["iso_alpha2"],
                    "iso_alpha3": row["iso_alpha3"],
                },
            )
            created, updated = (created + 1, updated) if was_created else (created, updated + 1)
        return created, updated

    def _seed_regions(self) -> tuple[int, int]:
        countries = {c.iso_alpha2: c for c in Country.objects.canonical()}
        created = updated = 0
        for row in _load("regions.json"):
            country = countries.get(row["country"])
            if country is None:
                raise CommandError(
                    f"Region {row['name']!r} references unknown country {row['country']!r}"
                )
            _, was_created = self._upsert(
                Region,
                slugify(row["name"])[:220],
                {
                    "name": row["name"],
                    "country": country,
                    "altitude_min_masl": row.get("altitude_min_masl"),
                    "altitude_max_masl": row.get("altitude_max_masl"),
                },
            )
            created, updated = (created + 1, updated) if was_created else (created, updated + 1)
        return created, updated

    def _seed_simple(self, model: Any, filename: str, extra: tuple[str, ...]) -> tuple[int, int]:
        created = updated = 0
        for row in _load(filename):
            defaults = {"name": row["name"], **{k: row[k] for k in extra if k in row}}
            _, was_created = self._upsert(model, slugify(row["name"])[:220], defaults)
            created, updated = (created + 1, updated) if was_created else (created, updated + 1)
        return created, updated

    def _seed_self_referencing(
        self, model: Any, filename: str, extra: tuple[str, ...]
    ) -> tuple[int, int]:
        """Two passes: rows first, then parents.

        A fixture may name a parent that appears later in the file, so linking
        cannot happen during the first pass.
        """
        rows = _load(filename)
        created = updated = 0
        for row in rows:
            defaults = {"name": row["name"], **{k: row[k] for k in extra if k in row}}
            _, was_created = self._upsert(model, slugify(row["name"])[:220], defaults)
            created, updated = (created + 1, updated) if was_created else (created, updated + 1)

        by_slug = {obj.slug: obj for obj in model.objects.canonical()}
        for row in rows:
            parent_slug = row.get("parent")
            if not parent_slug:
                continue
            child = by_slug[slugify(row["name"])[:220]]
            parent = by_slug.get(parent_slug)
            if parent is None:
                raise CommandError(f"{row['name']!r} references unknown parent {parent_slug!r}")
            if child.parent_id != parent.id:
                child.parent = parent
                child.save(update_fields=["parent", "updated_at"])
        return created, updated
