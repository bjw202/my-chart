#!/usr/bin/env python3
"""Offline, long-only portfolio snapshot calculator. No recommendation or orders."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, localcontext, ROUND_FLOOR
import json
from pathlib import Path
import sys

D = Decimal


class InputError(ValueError):
    pass


def number(value, name, nonnegative=True):
    if isinstance(value, bool) or value is None:
        raise InputError(f"{name}: a finite number is required")
    try:
        result = D(str(value))
    except (InvalidOperation, ValueError):
        raise InputError(f"{name}: invalid number") from None
    if not result.is_finite() or (nonnegative and result < 0):
        raise InputError(f"{name}: finite nonnegative number required")
    return result


def label(value, name):
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{name}: nonempty string required")
    return value.strip()


def currency(value):
    result = label(value, "currency").upper()
    if len(result) != 3 or not result.isascii() or not result.isalpha():
        raise InputError("currency must be a three-letter code")
    return result


def stamp(value, name):
    try:
        parsed = datetime.fromisoformat(label(value, name).replace("Z", "+00:00"))
    except ValueError:
        raise InputError(f"{name}: ISO date/time required") from None
    if parsed.tzinfo is None:
        if len(value) != 10:
            raise InputError(f"{name}: time requires an explicit timezone")
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def percent(part, whole):
    return part / whole * 100 if whole else None


def serial(value):
    if isinstance(value, D):
        return format(value.quantize(D("0.000001")), "f")
    if isinstance(value, dict):
        return {key: serial(item) for key, item in value.items()}
    if isinstance(value, list):
        return [serial(item) for item in value]
    return value


def calculate(data):
    if not isinstance(data, dict):
        raise InputError("input must be a JSON object")
    with localcontext() as context:
        context.prec = 50
        return serial(_calculate(data))


def _calculate(data):
    base = currency(data.get("base_currency"))
    as_of = stamp(data.get("as_of"), "as_of")
    coverage = data.get("coverage")
    if coverage not in ("partial", "full"):
        raise InputError("coverage must be partial or full (user declaration)")
    max_age = data.get("max_price_age_days")
    max_age = number(max_age, "max_price_age_days") if max_age is not None else None
    max_fx_age = data.get("max_fx_age_days")
    max_fx_age = number(max_fx_age, "max_fx_age_days") if max_fx_age is not None else None
    warnings = []
    rate_map = {base: D(1)}
    fx_records = []
    fx_seen = set()
    for rate in data.get("fx_rates", []):
        code = currency(rate.get("currency"))
        if code in fx_seen or code == base:
            raise InputError("duplicate FX currency or redundant base-currency rate")
        fx_seen.add(code)
        value = number(rate.get("rate_to_base"), "rate_to_base")
        if not value:
            raise InputError("rate_to_base must be positive")
        date = stamp(rate.get("as_of"), "FX as_of")
        if date > as_of:
            raise InputError("FX date is after the portfolio cutoff")
        source = label(rate.get("source"), "FX source")
        if rate.get("verified") is not True:
            raise InputError("FX rate requires verified=true from the source-checking agent")
        age = D(str((as_of - date).total_seconds())) / D(86400)
        stale = max_fx_age is not None and age > max_fx_age
        if stale:
            warnings.append(f"stale_fx:{code}")
        rate_map[code] = value
        fx_records.append({"currency": code, "rate_to_base": value,
                           "as_of": rate["as_of"], "source": source,
                           "age_days": age, "freshness": "stale" if stale else
                           "within_user_threshold" if max_fx_age is not None else "not_assessed"})

    def convert(value, code):
        if code not in rate_map:
            if f"missing_fx:{code}" not in warnings:
                warnings.append(f"missing_fx:{code}")
            return None
        return value * rate_map[code]

    holdings = data.get("holdings", [])
    cash = data.get("cash", [])
    if not isinstance(holdings, list) or not isinstance(cash, list) or not (holdings or cash):
        raise InputError("provide nonempty holdings and/or cash arrays")
    ids, listings, rows, cash_rows = set(), set(), [], []

    def unique_id(item):
        item_id = label(item.get("id"), "id")
        if item_id in ids:
            raise InputError(f"duplicate asset id: {item_id}")
        ids.add(item_id)
        return item_id

    for holding in holdings:
        item_id = unique_id(holding)
        ticker = label(holding.get("ticker"), "ticker")
        market = label(holding.get("market"), "market")
        listing = (ticker.upper(), market.upper())
        if listing in listings:
            raise InputError("duplicate ticker/market: consolidate lots before calculation")
        listings.add(listing)
        qty = number(holding.get("quantity"), "quantity")
        avg = number(holding.get("average_cost"), "average_cost per share")
        cost_currency = currency(holding.get("cost_currency"))
        price_currency = currency(holding.get("price_currency"))
        cost = convert(qty * avg, cost_currency)
        price = holding.get("current_price")
        price_base, age, freshness = None, None, "missing"
        if price is not None:
            price = number(price, "current_price")
            price_date = stamp(holding.get("price_as_of"), "price_as_of")
            if price_date > as_of:
                raise InputError(f"{item_id}: price date is after portfolio cutoff")
            label(holding.get("price_source"), "price_source")
            age = D(str((as_of - price_date).total_seconds())) / D(86400)
            freshness = ("stale" if max_age is not None and age > max_age else
                         "within_user_threshold" if max_age is not None else "not_assessed")
            if freshness == "stale":
                warnings.append(f"stale_price:{item_id}")
            price_base = convert(price, price_currency)
        value = qty * price_base if price_base is not None else (D(0) if qty == 0 else None)
        pnl = value - cost if value is not None and cost is not None else None
        sector = holding.get("sector")
        issuer = holding.get("issuer_id")
        rows.append({"id": item_id, "ticker": ticker, "market": market,
                     "quantity": qty, "average_cost": avg, "cost_currency": cost_currency,
                     "current_price": price, "price_currency": price_currency,
                     "price_as_of": holding.get("price_as_of"), "price_source": holding.get("price_source"),
                     "price_age_days": age, "price_freshness": freshness,
                     "unit_price_base": price_base, "cost_basis_base": cost,
                     "market_value_base": value, "unrealized_pnl_base": pnl,
                     "unrealized_pnl_percent": percent(pnl, cost) if pnl is not None else None,
                     "issuer_id": label(issuer, "issuer_id") if issuer is not None else None,
                     "sector": label(sector, "sector") if sector is not None else None})
    for item in cash:
        item_id = unique_id(item)
        code = currency(item.get("currency"))
        amount = number(item.get("amount"), "cash amount")
        cash_rows.append({"id": item_id, "currency": code, "amount": amount,
                          "market_value_base": convert(amount, code)})
    all_rows = rows + cash_rows
    complete = all(row["market_value_base"] is not None for row in all_rows)
    cost_complete = all(row["cost_basis_base"] is not None for row in rows)
    known_total = sum((row["market_value_base"] for row in all_rows if row["market_value_base"] is not None), D(0))
    known_cost = sum((row["cost_basis_base"] for row in rows if row["cost_basis_base"] is not None), D(0))
    paired_pnl = sum((row["unrealized_pnl_base"] for row in rows if row["unrealized_pnl_base"] is not None), D(0))
    for row in all_rows:
        value = row["market_value_base"]
        row["allocation_percent"] = percent(value, known_total) if complete else None
        row["known_subset_allocation_percent"] = percent(value, known_total) if value is not None else None

    def concentration(field):
        groups = {}
        unmapped = D(0)
        for row in rows:
            if row["market_value_base"] is None:
                continue
            key, value = row[field], row["market_value_base"]
            if key is None:
                unmapped += value
            else:
                groups[key] = groups.get(key, D(0)) + value
        return {"basis": "submitted_scope_including_cash" if complete else "known_subset_including_cash",
                "groups": [{"name": key, "market_value_base": value, "weight_percent": percent(value, known_total)}
                           for key, value in sorted(groups.items(), key=lambda pair: (-pair[1], pair[0]))],
                "unmapped_value_base": unmapped,
                "mapping_complete": all(row[field] is not None for row in rows if row["quantity"] > 0)}

    scenario = {"status": "not_requested"}
    targets = data.get("targets")
    if targets is not None:
        if not isinstance(targets, list):
            raise InputError("targets must be an array")
        target_map = {}
        for target in targets:
            key = label(target.get("id"), "target id")
            if key in target_map or key not in ids:
                raise InputError("target ids must be unique and match supplied holdings/cash")
            target_map[key] = number(target.get("weight_percent"), "target weight_percent")
        if set(target_map) != ids or sum(target_map.values(), D(0)) != 100:
            raise InputError("targets must cover every supplied holding and cash id and sum exactly to 100")
        costs = data.get("estimated_cost_base")
        costs = number(costs, "estimated_cost_base") if costs is not None else None
        blockers = []
        if not complete:
            blockers.append("incomplete_valuation")
        if known_total == 0:
            blockers.append("zero_total_value")
        if any(w.startswith("stale_") for w in warnings):
            blockers.append("stale_inputs_under_user_threshold")
        if any(row["unit_price_base"] is None or row["unit_price_base"] <= 0 for row in rows):
            blockers.append("missing_or_zero_unit_price")
        if blockers:
            scenario = {"status": "blocked", "reasons": blockers}
        else:
            changes, buys, sells = [], D(0), D(0)
            for row in rows:
                desired = known_total * target_map[row["id"]] / 100
                gap = desired - row["market_value_base"]
                shares = (abs(gap) / row["unit_price_base"]).to_integral_value(rounding=ROUND_FLOOR)
                if gap < 0:
                    shares = -min(shares, row["quantity"].to_integral_value(rounding=ROUND_FLOOR))
                delta = shares * row["unit_price_base"]
                buys += max(delta, D(0))
                sells += max(-delta, D(0))
                changes.append({"id": row["id"], "target_weight_percent": target_map[row["id"]],
                                "desired_value_base": desired, "value_gap_base": gap,
                                "estimated_whole_share_delta": shares, "estimated_value_delta_base": delta})
            cash_total = sum((row["market_value_base"] for row in cash_rows), D(0))
            cash_targets = [{"id": row["id"], "desired_value_base": known_total * target_map[row["id"]] / 100,
                             "value_gap_base": known_total * target_map[row["id"]] / 100 - row["market_value_base"]}
                            for row in cash_rows]
            before_cost = cash_total + sells - buys
            after_cost = before_cost - costs if costs is not None else None
            desired_cash = sum((entry["desired_value_base"] for entry in cash_targets), D(0))
            scenario = {"status": "illustrative_user_targets", "holdings": changes, "cash_targets": cash_targets,
                        "estimated_buys_base": buys, "estimated_sells_base": sells,
                        "cash_after_sells_and_buys_before_costs_base": before_cost,
                        "cash_feasible_before_costs": before_cost >= 0,
                        "estimated_cost_base": costs, "cash_after_estimated_costs_base": after_cost,
                        "cash_feasible_after_estimated_costs": after_cost >= 0 if after_cost is not None else None,
                        "target_cash_total_base": desired_cash,
                        "target_cash_gap_after_estimated_costs_base": after_cost - desired_cash if after_cost is not None else None,
                        "assumptions": ["User-supplied target scenario; not an order or recommendation.",
                                        "All hypothetical sales fund buys; settlement timing, liquidity, FX trading and trading restrictions are not modeled.",
                                        "Whole-share changes truncate toward zero; fractional holdings can leave residuals; target weights are not guaranteed.",
                                        "Targets use pre-cost snapshot value. User-estimated aggregate costs are not verified fees or taxes.",
                                        "Cash feasibility pools converted cash across currencies; actual spendable cash and target cash by currency are not verified."]}
    if coverage == "partial":
        warnings.append("partial_scope:not_a_complete_account_or_wealth_assessment")
    if not complete:
        warnings.append("incomplete_valuation:no_whole_scope_weights_or_rebalance")
    return {"schema_version": "1.0", "base_currency": base, "as_of": data["as_of"],
            "coverage": {"user_declared": coverage, "independently_verified_complete_wealth": False,
                         "valuation_complete_for_submitted_assets": complete, "cost_basis_complete": cost_complete,
                         "missing_value_ids": [row["id"] for row in all_rows if row["market_value_base"] is None]},
            "totals": {"market_value_base": known_total if complete else None, "known_market_value_subtotal_base": known_total,
                       "cost_basis_base": known_cost if cost_complete else None, "known_cost_basis_subtotal_base": known_cost,
                       "unrealized_pnl_base": paired_pnl if complete and cost_complete else None,
                       "known_paired_unrealized_pnl_subtotal_base": paired_pnl,
                       "unrealized_pnl_percent": percent(paired_pnl, known_cost) if complete and cost_complete else None},
            "holdings": rows, "cash": cash_rows, "fx_rates": fx_records,
            "sector_concentration": concentration("sector"), "issuer_concentration": concentration("issuer_id"),
            "rebalance": scenario, "warnings": warnings,
            "method_notes": ["Amounts and percentages are decimal strings rounded to six places for output; calculations use Decimal with 50-digit precision.",
                             "Cost basis = quantity × user average cost per share. Cash is excluded from investment cost basis and unrealized return denominator.",
                             "All FX conversions use supplied verified snapshot rates. Converted cost basis is not historical actual base-currency acquisition cost or FX-inclusive investment return.",
                             "Source verification is performed by the collecting agent; this offline calculator does not fetch or authenticate sources.",
                             "Date-only timestamps mean 00:00 UTC; use explicit timezone times for intraday cutoff analysis.",
                             "Missing prices remain unknown; zero is accepted only when explicitly supplied. No live-price claim or inferred risk objective."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"), parse_float=D)
        result = calculate(data)
        output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.write_text(output, encoding="utf-8")
        else:
            print(output, end="")
    except (InputError, OSError, ValueError, TypeError, AttributeError, InvalidOperation) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
