import pandas as pd
import io
from typing import List, Dict, Any

def parse_custom_csv_universe(csv_content: str) -> List[Dict[str, Any]]:
    """
    Parses user uploaded CSV string and extracts custom stock universe.
    Expected CSV columns (flexible matching): symbol, company_name/name, sector, exchange, market_cap/mcap.
    """
    df = pd.read_csv(io.StringIO(csv_content))
    
    # Normalize column names to lowercase stripped
    df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]
    
    # Map possible column names
    sym_col = next((c for c in ['symbol', 'ticker', 'stock'] if c in df.columns), None)
    name_col = next((c for c in ['company_name', 'name', 'company'] if c in df.columns), None)
    sector_col = next((c for c in ['sector', 'industry'] if c in df.columns), None)
    exch_col = next((c for c in ['exchange', 'exch'] if c in df.columns), None)
    mcap_col = next((c for c in ['market_cap', 'mcap', 'marketcap'] if c in df.columns), None)

    if not sym_col:
        raise ValueError("CSV must contain a 'symbol' column.")

    stocks = []
    for _, row in df.iterrows():
        sym = str(row[sym_col]).strip().upper()
        if not sym or pd.isna(sym):
            continue
        
        name = str(row[name_col]).strip() if name_col and not pd.isna(row[name_col]) else sym
        sector = str(row[sector_col]).strip() if sector_col and not pd.isna(row[sector_col]) else "General"
        exchange = str(row[exch_col]).strip().upper() if exch_col and not pd.isna(row[exch_col]) else "NSE"
        mcap = float(row[mcap_col]) if mcap_col and not pd.isna(row[mcap_col]) else None

        stocks.append({
            "symbol": sym,
            "name": name,
            "sector": sector,
            "exchange": exchange,
            "mcap": mcap
        })

    return stocks
