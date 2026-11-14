from datetime import date

from sqlalchemy.orm import Session

from ..models import AgriculturalSource
from ._helpers import get_or_create


SOURCES = (
    {
        "organization": "The University of Agriculture, Peshawar",
        "title": "Faculty of Crop Production Sciences",
        "publication_url": (
            "https://www.aup.edu.pk/faculty/faculty-of-crop-production-sciences"
        ),
        "source_type": "Institutional faculty webpage",
        "geographic_applicability": (
            "The faculty is based in Peshawar; the page does not validate "
            "crop-specific geographic applicability."
        ),
        "evidence_class": "Institutional context",
        "review_status": "UNREVIEWED",
        "limitations": (
            "Institutional scope and activities only. The page names no crop "
            "varieties or agronomic values; it is not used as crop-fact evidence."
        ),
    },
    {
        "organization": "Pakistan Agricultural Research Council",
        "title": (
            "Chairman PARC chairing the inaugural ceremony of annual wheat "
            "planning and Review Meeting 2026"
        ),
        "publication_url": (
            "https://www.parc.gov.pk/NewsDetail/"
            "YzZmNTE3MWUtMDUzNS00ZDMxLThlYTQtMWFmN2JmMWQ0YzY0"
        ),
        "publication_date": date(2026, 11, 3),
        "source_type": "Institutional news",
        "geographic_applicability": (
            "The page reports a meeting at NARC Islamabad; it does not "
            "establish geographic applicability of agronomic advice."
        ),
        "evidence_class": "Institutional context",
        "review_status": "UNREVIEWED",
        "limitations": (
            "Meeting announcement only. It contains no crop-specific "
            "recommendations used by these seeds."
        ),
    },
    {
        "organization": "Food and Agriculture Organization of the United Nations",
        "title": "FAO in Pakistan",
        "publication_url": "https://www.fao.org/pakistan/en/",
        "source_type": "Country office webpage",
        "geographic_applicability": (
            "Pakistan country-office context only; no local crop applicability "
            "is inferred."
        ),
        "evidence_class": "Institutional context",
        "review_status": "UNREVIEWED",
        "limitations": (
            "Country office landing page only. No crop-specific factual claim "
            "is populated from this page."
        ),
    },
)


def seed_sources(session: Session) -> int:
    created = 0
    for source_values in SOURCES:
        _, was_created = get_or_create(
            session,
            AgriculturalSource,
            lookup={"publication_url": source_values["publication_url"]},
            values=source_values,
        )
        created += int(was_created)
    return created
