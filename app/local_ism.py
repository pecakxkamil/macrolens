"""Local ISM document source, separate from FRED and ALFRED."""
from app.database.connection import get_connection

ATTRIBUTION = "Institute for Supply Management (ISM), via PR Newswire. Local personal use; public display/export rights require verification. Document revisions are not a full PIT history."
SERIES = {
    "ISM_MANUFACTURING_PMI": {"name": "ISM Manufacturing PMI", "short_name": "Manufacturing PMI", "category": "growth", "frequency": "monthly", "unit": "index", "source": "ism", "source_url": "https://www.ismworld.org/", "attribution": ATTRIBUTION, "description": "Manufacturing diffusion index. Local ISM release-table history; no percentage transformation or ratio indexing. Document publication dates are not first-release dates for historical observations."},
    "ISM_SERVICES_PMI": {"name": "ISM Services PMI", "short_name": "Services PMI", "category": "growth", "frequency": "monthly", "unit": "index", "source": "ism", "source_url": "https://www.ismworld.org/", "attribution": ATTRIBUTION, "description": "Services diffusion index. Local ISM release-table history; no percentage transformation or ratio indexing. Document publication dates are not first-release dates for historical observations."},
}
HISTORY_SQL = """
SELECT DISTINCT ON (v.observation_date) v.observation_date, v.value,
       d.published_at, d.source_url, d.retrieved_at, d.raw_hash
FROM ism_observations v JOIN ism_documents d ON d.id = v.document_id
WHERE d.series_id = %s
  AND (%s::date IS NULL OR v.observation_date >= %s)
  AND (%s::date IS NULL OR v.observation_date <= %s)
ORDER BY v.observation_date, d.published_at DESC, d.retrieved_at DESC, d.id DESC
"""

def load_history(series_id, start=None, end=None):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(HISTORY_SQL, (series_id, start, start, end, end))
            rows = cursor.fetchall()
    finally:
        connection.close()
    observations = [{"observation_date": day, "value": float(value), "document_published_at": published.isoformat(),
                     "source_url": url, "retrieved_at": retrieved.isoformat(), "raw_hash": digest}
                    for day, value, published, url, retrieved, digest in rows]
    return {"series_id": series_id, **SERIES[series_id], "history_type": "current_vintage", "start_date": start,
            "end_date": end, "coverage_start": rows[0][0] if rows else None, "coverage_end": rows[-1][0] if rows else None,
            "observations": observations}
