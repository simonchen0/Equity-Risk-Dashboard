import pandas as pd
import streamlit as st
from components import format as fmt
from components.state import current_alerts, get_limits, require_snapshot, set_limits
from components.theme import kpi_strip, table_height
from pydantic import ValidationError

from riskdash.alerts.limits import Limits, load_limits

st.title("Alerts")
snap = require_snapshot()
alerts = current_alerts(snap)

counts = {s: sum(a.severity == s for a in alerts) for s in ("breach", "warn", "ok")}
kpi_strip(
    [
        dict(label="Breaches", value=counts["breach"], help="Metric is over its limit."),
        dict(
            label="Approaching limit",
            value=counts["warn"],
            help=f"Metric has reached {get_limits().warn_fraction:.0%} of its limit.",
        ),
        dict(label="Within limits", value=counts["ok"]),
    ],
    key="alerts",
)

ITEM_RULES = ("single_name", "sector", "pair_correlation")
STATUS = {"breach": "✖ Breach", "warn": "▲ Approaching", "ok": "✔ OK"}
COLOR = {"breach": fmt.NEG, "warn": "#e3b341", "ok": fmt.POS}


def value_text(a) -> str:
    return f"{a.value:.1%}" if a.kind == "pct" else f"{a.value:.2f}"


table = pd.DataFrame(
    {
        "Status": [STATUS[a.severity] for a in alerts],
        "Rule": [a.label for a in alerts],
        "Item": [a.detail.rsplit(" ", 1)[0] if a.rule in ITEM_RULES else "" for a in alerts],
        "Value": [value_text(a) for a in alerts],
        "Limit": [a.limit_text for a in alerts],
    }
)
sev = [a.severity for a in alerts]
st.dataframe(
    table.style.apply(
        lambda col: [f"color: {COLOR[s]}; font-weight: 600" for s in sev], subset=["Status"]
    ),
    hide_index=True,
    width="stretch",
    height=table_height(len(table)),
    row_height=28,
)
st.caption(
    "Single-name uses each position's absolute weight; sector uses the net weight (longs minus "
    "shorts); correlation looks only at pairs of large positions. Weights are % of NAV."
)

# --- Limit editor -----------------------------------------------------------------------
with st.expander("Edit limits", icon=":material/tune:"):
    lim = get_limits()
    ver = st.session_state.limits_version
    st.caption(
        "Changes apply to this session only. Defaults come from `config/default_limits.yaml`."
    )
    PCT = [
        ("max_single_name_weight", "Max single-name weight (%)"),
        ("max_sector_net_weight", "Max sector net weight (%)"),
        ("max_top5_weight", "Max top-5 concentration (%)"),
        ("max_volatility", "Max annualized volatility (%)"),
        ("max_gross_exposure", "Max gross exposure (%)"),
        ("max_abs_net_exposure", "Max absolute net exposure (%)"),
        ("correlation_min_weight", "A 'large' position is at least (%)"),
        ("warn_fraction", "Warn at this % of a limit"),
    ]
    PLAIN = [
        ("beta_min", "Minimum portfolio beta"),
        ("beta_max", "Maximum portfolio beta"),
        ("max_pair_correlation", "Max pair correlation"),
    ]
    with st.form(f"limits_form_{ver}"):
        cols = st.columns(3)
        values = {}
        for i, (key, label) in enumerate(PCT):
            values[key] = (
                cols[i % 3].number_input(
                    label,
                    value=round(getattr(lim, key) * 100, 4),
                    step=1.0,
                    format="%.1f",
                    key=f"{key}_{ver}",
                )
                / 100
            )
        for i, (key, label) in enumerate(PLAIN, start=len(PCT)):
            values[key] = cols[i % 3].number_input(
                label, value=float(getattr(lim, key)), step=0.05, format="%.2f", key=f"{key}_{ver}"
            )
        if st.form_submit_button("Apply limits", type="primary"):
            try:
                set_limits(Limits(**{k: round(v, 6) for k, v in values.items()}))
            except ValidationError as exc:
                for e in exc.errors():
                    field = ".".join(str(x) for x in e["loc"]) or "limits"
                    st.error(f"{field}: {e['msg']}")
            else:
                st.rerun()
    if st.button("Reset to defaults", icon=":material/restart_alt:"):
        set_limits(load_limits())
        st.rerun()
