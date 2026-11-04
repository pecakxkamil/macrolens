"""Exact fiscal predecessor projection. No imports, writes or publisher HTTP."""


def previous_quarter(year, quarter):
    return (year - 1, 4) if quarter == 1 else (year, quarter - 1)


def basis(value):
    """E2B's constrained model explicitly permits only USD / US GAAP common EPS."""
    standard = value.get('reporting_standard') or 'US_GAAP'
    shares = value.get('share_basis') or ('not_applicable' if value['metric'] == 'revenue' else 'common_share')
    method = value['methodology']
    if method in ('gaap_diluted', 'reported_diluted_total_eps'):
        method = 'reported_diluted_total_eps'
    return value['currency'], standard, shares, method


def comparable(current, previous):
    return previous is not None and (current is None or basis(current) == basis(previous))


def attach(connection, events):
    # All events are already loaded in the caller's REPEATABLE READ READ ONLY
    # snapshot, before date filters. No per-event SQL or nearest-report fallback.
    from app.earnings_history import load
    history, store_status = load(connection)
    by_period = {(e['company_id'], e['cik'], int(e['fiscal_year']), int(e['fiscal_quarter'])): e for e in history}
    # An existing event is authoritative even when its newest snapshot has no
    # metrics; history must not silently refill a withdrawn/pending value.
    by_period.update({(e['company_id'], e['cik'], int(e['fiscal_year']), int(e['fiscal_quarter'])): e for e in events})
    for event in events:
        year, quarter = previous_quarter(int(event['fiscal_year']), int(event['fiscal_quarter']))
        previous = by_period.get((event['company_id'], event['cik'], year, quarter))
        event['previous_period'] = None
        event['previous_store_status'] = store_status
        event['previous_history'] = [r for r in history if r['company_id']==event['company_id'] and int(r['fiscal_year'])==year and int(r['fiscal_quarter'])==quarter]
        for metric, field in [('eps', 'reported_eps_actual'), ('revenue', 'revenue_actual')]:
            current = event.get(field)
            if metric == 'eps' and current is None:
                current = event.get('gaap_diluted_eps_actual')
            candidate = previous.get(field) if previous else None
            if previous and metric == 'eps' and candidate is None:
                candidate = previous.get('gaap_diluted_eps_actual')
            documents = event.get('report_documents') or []
            if current is None and candidate is not None and documents:
                document = documents[-1]
                if (document.get('reporting_currency') not in (None, candidate['currency']) or
                    document.get('reporting_standard') not in (None, basis(candidate)[1]) or
                    (metric == 'eps' and document.get('eps_share_basis') not in (None, basis(candidate)[2]))):
                    candidate = None
            event['current_' + metric + '_actual'] = current
            event['current_' + metric + '_forecast'] = None
            event['previous_' + metric + '_actual'] = candidate if comparable(current, candidate) else None
            event['previous_' + metric + '_forecast'] = None
        if previous and any(event['previous_' + m + '_actual'] is not None for m in ('eps', 'revenue')):
            event['previous_period'] = {k: previous[k] for k in ('fiscal_year', 'fiscal_quarter', 'period_label', 'period_end')}
    return events
