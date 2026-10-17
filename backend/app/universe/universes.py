from typing import List, Dict, Any

# Stock universe definitions with exact sectors and company names for Indian stock market
STOCK_UNIVERSES: Dict[str, List[Dict[str, Any]]] = {
    "NIFTY 50": [
        {"symbol": "RELIANCE", "name": "Reliance Industries Ltd.", "sector": "Energy", "exchange": "NSE", "mcap": 1900000},
        {"symbol": "TCS", "name": "Tata Consultancy Services Ltd.", "sector": "IT", "exchange": "NSE", "mcap": 1400000},
        {"symbol": "HDFCBANK", "name": "HDFC Bank Ltd.", "sector": "Bank", "exchange": "NSE", "mcap": 1200000},
        {"symbol": "BHARTIARTL", "name": "Bharti Airtel Ltd.", "sector": "Telecom", "exchange": "NSE", "mcap": 900000},
        {"symbol": "ICICIBANK", "name": "ICICI Bank Ltd.", "sector": "Bank", "exchange": "NSE", "mcap": 850000},
        {"symbol": "INFY", "name": "Infosys Ltd.", "sector": "IT", "exchange": "NSE", "mcap": 750000},
        {"symbol": "ITC", "name": "ITC Ltd.", "sector": "FMCG", "exchange": "NSE", "mcap": 600000},
        {"symbol": "SBIN", "name": "State Bank of India", "sector": "Bank", "exchange": "NSE", "mcap": 700000},
        {"symbol": "LTIM", "name": "LTIMindtree Ltd.", "sector": "IT", "exchange": "NSE", "mcap": 500000},
        {"symbol": "LT", "name": "Larsen & Toubro Ltd.", "sector": "Infra", "exchange": "NSE", "mcap": 500000},
        {"symbol": "HINDUNILVR", "name": "Hindustan Unilever Ltd.", "sector": "FMCG", "exchange": "NSE", "mcap": 550000},
        {"symbol": "TATAMOTORS", "name": "Tata Motors Ltd.", "sector": "Auto", "exchange": "NSE", "mcap": 350000},
        {"symbol": "M&M", "name": "Mahindra & Mahindra Ltd.", "sector": "Auto", "exchange": "NSE", "mcap": 380000},
        {"symbol": "SUNPHARMA", "name": "Sun Pharmaceutical Industries", "sector": "Pharma", "exchange": "NSE", "mcap": 400000},
        {"symbol": "NTPC", "name": "NTPC Ltd.", "sector": "Energy", "exchange": "NSE", "mcap": 370000},
        {"symbol": "ONGC", "name": "Oil & Natural Gas Corp.", "sector": "Energy", "exchange": "NSE", "mcap": 360000},
        {"symbol": "TITAN", "name": "Titan Company Ltd.", "sector": "FMCG", "exchange": "NSE", "mcap": 300000},
        {"symbol": "MARUTI", "name": "Maruti Suzuki India Ltd.", "sector": "Auto", "exchange": "NSE", "mcap": 380000},
        {"symbol": "POWERGRID", "name": "Power Grid Corp of India", "sector": "Energy", "exchange": "NSE", "mcap": 310000},
        {"symbol": "AXISBANK", "name": "Axis Bank Ltd.", "sector": "Bank", "exchange": "NSE", "mcap": 360000},
        {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank Ltd.", "sector": "Bank", "exchange": "NSE", "mcap": 350000},
        {"symbol": "ADANIENT", "name": "Adani Enterprises Ltd.", "sector": "Infra", "exchange": "NSE", "mcap": 340000},
        {"symbol": "ADANIPORTS", "name": "Adani Ports & SEZ Ltd.", "sector": "Infra", "exchange": "NSE", "mcap": 300000},
        {"symbol": "TATASTEEL", "name": "Tata Steel Ltd.", "sector": "Metal", "exchange": "NSE", "mcap": 200000},
        {"symbol": "JSWSTEEL", "name": "JSW Steel Ltd.", "sector": "Metal", "exchange": "NSE", "mcap": 220000},
        {"symbol": "HCLTECH", "name": "HCL Technologies Ltd.", "sector": "IT", "exchange": "NSE", "mcap": 420000},
        {"symbol": "WIPRO", "name": "Wipro Ltd.", "sector": "IT", "exchange": "NSE", "mcap": 280000},
        {"symbol": "TECHM", "name": "Tech Mahindra Ltd.", "sector": "IT", "exchange": "NSE", "mcap": 150000},
        {"symbol": "BAJFINANCE", "name": "Bajaj Finance Ltd.", "sector": "Financials", "exchange": "NSE", "mcap": 430000},
        {"symbol": "BAJAJFINSV", "name": "Bajaj Finserv Ltd.", "sector": "Financials", "exchange": "NSE", "mcap": 300000},
        {"symbol": "ASIANPAINT", "name": "Asian Paints Ltd.", "sector": "FMCG", "exchange": "NSE", "mcap": 280000},
        {"symbol": "ULTRACEMCO", "name": "UltraTech Cement Ltd.", "sector": "Infra", "exchange": "NSE", "mcap": 320000},
        {"symbol": "NESTLEIND", "name": "Nestle India Ltd.", "sector": "FMCG", "exchange": "NSE", "mcap": 230000},
        {"symbol": "COALINDIA", "name": "Coal India Ltd.", "sector": "Energy", "exchange": "NSE", "mcap": 290000},
        {"symbol": "GRASIM", "name": "Grasim Industries Ltd.", "sector": "Infra", "exchange": "NSE", "mcap": 180000},
        {"symbol": "CIPLA", "name": "Cipla Ltd.", "sector": "Pharma", "exchange": "NSE", "mcap": 130000},
        {"symbol": "DRREDDY", "name": "Dr. Reddy's Laboratories", "sector": "Pharma", "exchange": "NSE", "mcap": 110000},
        {"symbol": "EICHERMOT", "name": "Eicher Motors Ltd.", "sector": "Auto", "exchange": "NSE", "mcap": 135000},
        {"symbol": "HEROMOTOCO", "name": "Hero MotoCorp Ltd.", "sector": "Auto", "exchange": "NSE", "mcap": 110000},
        {"symbol": "APOLLOHOSP", "name": "Apollo Hospitals Enterprise", "sector": "Pharma", "exchange": "NSE", "mcap": 95000},
        {"symbol": "DIVISLAB", "name": "Divi's Laboratories Ltd.", "sector": "Pharma", "exchange": "NSE", "mcap": 125000},
        {"symbol": "TATACONSUM", "name": "Tata Consumer Products Ltd.", "sector": "FMCG", "exchange": "NSE", "mcap": 110000},
        {"symbol": "BPCL", "name": "Bharat Petroleum Corp. Ltd.", "sector": "Energy", "exchange": "NSE", "mcap": 140000},
        {"symbol": "HDFCLIFE", "name": "HDFC Life Insurance Co.", "sector": "Financials", "exchange": "NSE", "mcap": 150000},
        {"symbol": "SBILIFE", "name": "SBI Life Insurance Co. Ltd.", "sector": "Financials", "exchange": "NSE", "mcap": 160000},
        {"symbol": "BEL", "name": "Bharat Electronics Ltd.", "sector": "Infra", "exchange": "NSE", "mcap": 210000},
        {"symbol": "TRENT", "name": "Trent Ltd.", "sector": "FMCG", "exchange": "NSE", "mcap": 240000},
        {"symbol": "HINDALCO", "name": "Hindalco Industries Ltd.", "sector": "Metal", "exchange": "NSE", "mcap": 150000},
        {"symbol": "SHRIRAMFIN", "name": "Shriram Finance Ltd.", "sector": "Financials", "exchange": "NSE", "mcap": 120000}
    ],
    "NIFTY 100": [],
    "NIFTY 200": [],
    "NIFTY 500": [],
    "Midcap": [
        {"symbol": "PERSISTENT", "name": "Persistent Systems Ltd.", "sector": "IT", "exchange": "NSE", "mcap": 75000},
        {"symbol": "COFORGE", "name": "Coforge Ltd.", "sector": "IT", "exchange": "NSE", "mcap": 50000},
        {"symbol": "MPHASIS", "name": "Mphasis Ltd.", "sector": "IT", "exchange": "NSE", "mcap": 55000},
        {"symbol": "DIXON", "name": "Dixon Technologies Ltd.", "sector": "Infra", "exchange": "NSE", "mcap": 80000},
        {"symbol": "POLYCAB", "name": "Polycab India Ltd.", "sector": "Infra", "exchange": "NSE", "mcap": 98000},
        {"symbol": "DLF", "name": "DLF Ltd.", "sector": "Realty", "exchange": "NSE", "mcap": 210000},
        {"symbol": "GODREJPROP", "name": "Godrej Properties Ltd.", "sector": "Realty", "exchange": "NSE", "mcap": 85000},
        {"symbol": "OBERREALTY", "name": "Oberoi Realty Ltd.", "sector": "Realty", "exchange": "NSE", "mcap": 65000},
        {"symbol": "PHOENIXLTD", "name": "The Phoenix Mills Ltd.", "sector": "Realty", "exchange": "NSE", "mcap": 62000},
        {"symbol": "LUPIN", "name": "Lupin Ltd.", "sector": "Pharma", "exchange": "NSE", "mcap": 95000},
        {"symbol": "AUROPHARMA", "name": "Aurobindo Pharma Ltd.", "sector": "Pharma", "exchange": "NSE", "mcap": 82000},
        {"symbol": "TUBEINVEST", "name": "Tube Investments of India", "sector": "Auto", "exchange": "NSE", "mcap": 78000},
        {"symbol": "TVSMOTOR", "name": "TVS Motor Company Ltd.", "sector": "Auto", "exchange": "NSE", "mcap": 120000},
        {"symbol": "BHARATFORG", "name": "Bharat Forge Ltd.", "sector": "Auto", "exchange": "NSE", "mcap": 68000}
    ],
    "Smallcap": [
        {"symbol": "KPITTECH", "name": "KPIT Technologies Ltd.", "sector": "IT", "exchange": "NSE", "mcap": 45000},
        {"symbol": "HAPPSTMNDS", "name": "Happiest Minds Technologies", "sector": "IT", "exchange": "NSE", "mcap": 12000},
        {"symbol": "CYIENT", "name": "Cyient Ltd.", "sector": "IT", "exchange": "NSE", "mcap": 22000},
        {"symbol": "BRIGADE", "name": "Brigade Enterprises Ltd.", "sector": "Realty", "exchange": "NSE", "mcap": 28000},
        {"symbol": "SOBHA", "name": "Sobha Ltd.", "sector": "Realty", "exchange": "NSE", "mcap": 18000},
        {"symbol": "GRANULES", "name": "Granules India Ltd.", "sector": "Pharma", "exchange": "NSE", "mcap": 14000},
        {"symbol": "CRAFTSMAN", "name": "Craftsman Automation Ltd.", "sector": "Auto", "exchange": "NSE", "mcap": 11000}
    ]
}

# Expand NIFTY 100, 200, 500 by combining sets for complete coverage
STOCK_UNIVERSES["NIFTY 100"] = STOCK_UNIVERSES["NIFTY 50"] + STOCK_UNIVERSES["Midcap"][:10]
STOCK_UNIVERSES["NIFTY 200"] = STOCK_UNIVERSES["NIFTY 100"] + STOCK_UNIVERSES["Midcap"][10:] + STOCK_UNIVERSES["Smallcap"][:4]
STOCK_UNIVERSES["NIFTY 500"] = STOCK_UNIVERSES["NIFTY 200"] + STOCK_UNIVERSES["Smallcap"][4:]

def get_universe_stocks(universe_name: str) -> List[Dict[str, Any]]:
    return STOCK_UNIVERSES.get(universe_name, STOCK_UNIVERSES["NIFTY 50"])

def get_available_universes() -> List[str]:
    return list(STOCK_UNIVERSES.keys())
