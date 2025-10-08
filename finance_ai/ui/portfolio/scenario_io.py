import io
import json
import pandas as pd
import streamlit as st
from typing import Any, Dict, List


def _flatten(d: Dict[str, Any], prefix: str = "") -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            rows.extend(_flatten(v, key))
        elif isinstance(v, list):
            # Store lists (e.g., windfalls) as JSON under the key
            rows.append({"key": key, "value": json.dumps(v)})
        else:
            rows.append({"key": key, "value": str(v)})
    return rows


def export_portfolio_to_csv_bytes() -> bytes:
    """Export the current portfolio session state into CSV bytes of key,value pairs."""
    if "portfolio" not in st.session_state:
        return b"key,value\n"
    rows = _flatten(st.session_state["portfolio"])  # list of {key,value}
    df = pd.DataFrame(rows, columns=["key", "value"]).sort_values("key").reset_index(drop=True)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


def _get_nested(root: Dict[str, Any], path: List[str]):
    cur = root
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


def _set_if_exists_with_cast(root: Dict[str, Any], dotted_key: str, new_val_str: str):
    parts = dotted_key.split(".")
    # If key is top-level 'windfalls' or endswith '.windfalls', parse JSON and assign
    if parts[-1] == "windfalls":
        try:
            parsed = json.loads(new_val_str) if new_val_str else []
            # Only accept list
            if isinstance(parsed, list):
                # Sanitize rows to have label, amount, age
                clean = []
                for item in parsed:
                    if not isinstance(item, dict):
                        continue
                    label = str(item.get("label", "")).strip()
                    amount = float(item.get("amount", 0) or 0)
                    age = int(item.get("age", 0) or 0)
                    if label or amount > 0:
                        clean.append({"label": label, "amount": amount, "age": age})
                # Write if path exists
                parent = st.session_state.get("portfolio", {})
                for p in parts[:-1]:
                    if isinstance(parent, dict) and p in parent:
                        parent = parent[p]
                    else:
                        return
                if isinstance(parent, dict):
                    parent[parts[-1]] = clean
        except Exception:
            pass
        return

    # For regular keys: traverse to parent and cast based on existing value type
    parent = st.session_state.get("portfolio", {})
    for p in parts[:-1]:
        if isinstance(parent, dict) and p in parent:
            parent = parent[p]
        else:
            return
    leaf = parts[-1]
    if not (isinstance(parent, dict) and leaf in parent):
        return
    current_val = parent[leaf]
    try:
        if isinstance(current_val, bool):
            v = str(new_val_str).strip().lower()
            parent[leaf] = v in ("1", "true", "yes", "y", "on")
        elif isinstance(current_val, int) and not isinstance(current_val, bool):
            parent[leaf] = int(float(new_val_str))
        elif isinstance(current_val, float):
            parent[leaf] = float(new_val_str)
        else:
            parent[leaf] = str(new_val_str)
    except Exception:
        # Ignore cast errors; leave existing value
        pass


def import_portfolio_from_csv(file_bytes: bytes):
    """Load a key,value CSV and map values back into session state where keys exist.
    Only keys that already exist in st.session_state['portfolio'] are updated.
    Special handling: windfalls JSON.
    """
    try:
        df = pd.read_csv(io.BytesIO(file_bytes))
    except Exception:
        st.error("Failed to read CSV. Expect two columns: key,value")
        return
    if "key" not in df.columns or "value" not in df.columns:
        st.error("CSV must have columns: key,value")
        return
    for _, row in df.iterrows():
        k = str(row["key"]) if pd.notna(row["key"]) else ""
        v = "" if pd.isna(row["value"]) else str(row["value"])
        if not k:
            continue
        _set_if_exists_with_cast(st.session_state.get("portfolio", {}), k, v)
