"""
Trade Journal Manager for Indian Market Intelligence Terminal.
Backed by SQLite (`trade_journal` table).
Features:
- Records both systematic research setups and real user executions
- Strictly enforces that signals are NOT marked as executed unless explicitly confirmed by user
- Tracks Entry, Stop Loss, Target, Quantity, Planned Risk, Actual Outcome, PnL, Notes, and Tags
- Allows CSV export and multi-factor filtering
"""

import io
import csv
from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.app.database import SessionLocal
from backend.app.models import TradeJournalModel
from backend.app.logging_config import logger


def add_trade_to_journal(trade_data: Dict[str, Any]) -> Optional[int]:
    """
    Saves a new planned or executed trade setup to SQLite.
    """
    try:
        db = SessionLocal()
        entry = TradeJournalModel(
            symbol=trade_data.get("symbol", "").upper(),
            strategy_name=trade_data.get("strategy_name", "General Setup"),
            timeframe=trade_data.get("timeframe", "1d"),
            bias=trade_data.get("bias", "BULLISH"),
            planned_entry=float(trade_data.get("planned_entry", 0.0)),
            planned_stop_loss=float(trade_data.get("planned_stop_loss", 0.0)),
            planned_target=float(trade_data.get("planned_target", 0.0)),
            planned_quantity=int(trade_data.get("planned_quantity", 1)),
            planned_risk=float(trade_data.get("planned_risk", 0.0)),
            estimated_charges=float(trade_data.get("estimated_charges", 0.0)),
            is_user_executed=bool(trade_data.get("is_user_executed", False)),
            actual_entry=float(trade_data["actual_entry"]) if trade_data.get("actual_entry") is not None else None,
            actual_exit=float(trade_data["actual_exit"]) if trade_data.get("actual_exit") is not None else None,
            actual_pnl=float(trade_data["actual_pnl"]) if trade_data.get("actual_pnl") is not None else None,
            status=trade_data.get("status", "PLANNED"),
            tags=trade_data.get("tags", ""),
            notes=trade_data.get("notes", ""),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        trade_id = entry.id
        db.close()
        logger.info(f"Trade #{trade_id} ({entry.symbol}) saved to SQLite Trade Journal.")
        return trade_id
    except Exception as e:
        logger.error(f"Error adding trade to journal: {e}")
        return None


def update_trade_journal(trade_id: int, updates: Dict[str, Any]) -> bool:
    """
    Updates an existing journal trade record (e.g. marking actual exit price, realized PnL, or status).
    """
    try:
        db = SessionLocal()
        entry = db.query(TradeJournalModel).filter(TradeJournalModel.id == trade_id).first()
        if not entry:
            db.close()
            return False

        for k, v in updates.items():
            if hasattr(entry, k):
                setattr(entry, k, v)

        entry.updated_at = datetime.utcnow()
        db.commit()
        db.close()
        logger.info(f"Trade #{trade_id} updated successfully.")
        return True
    except Exception as e:
        logger.error(f"Error updating trade #{trade_id}: {e}")
        return False


def get_all_journal_trades(
    status_filter: Optional[str] = None,
    symbol_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieves all journal entries from SQLite with optional filtering.
    """
    try:
        db = SessionLocal()
        query = db.query(TradeJournalModel)

        if status_filter and status_filter != "ALL":
            query = query.filter(TradeJournalModel.status == status_filter)
        if symbol_filter and symbol_filter != "ALL":
            query = query.filter(TradeJournalModel.symbol == symbol_filter.upper())

        records = query.order_by(TradeJournalModel.created_at.desc()).all()
        result = []
        for r in records:
            result.append({
                "id": r.id,
                "symbol": r.symbol,
                "strategy_name": r.strategy_name,
                "timeframe": r.timeframe,
                "bias": r.bias,
                "planned_entry": r.planned_entry,
                "planned_stop_loss": r.planned_stop_loss,
                "planned_target": r.planned_target,
                "planned_quantity": r.planned_quantity,
                "planned_risk": r.planned_risk,
                "estimated_charges": r.estimated_charges,
                "is_user_executed": r.is_user_executed,
                "actual_entry": r.actual_entry,
                "actual_exit": r.actual_exit,
                "actual_pnl": r.actual_pnl,
                "status": r.status,
                "tags": r.tags or "",
                "notes": r.notes or "",
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })
        db.close()
        return result
    except Exception as e:
        logger.error(f"Error reading trade journal: {e}")
        return []


def export_journal_to_csv() -> str:
    """
    Generates a CSV string of all journal records for user export.
    """
    trades = get_all_journal_trades()
    if not trades:
        return "ID,Symbol,Strategy,Timeframe,Bias,Planned_Entry,Stop_Loss,Target,Quantity,Planned_Risk,Is_Executed,Actual_Entry,Actual_Exit,Actual_PnL,Status,Tags,Created_At\n"

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(trades[0].keys()))
    writer.writeheader()
    for t in trades:
        writer.writerow(t)

    return output.getvalue()


def get_journal_statistics() -> Dict[str, Any]:
    """
    Computes performance summary across all closed and executed trades.
    """
    trades = get_all_journal_trades()
    executed_trades = [t for t in trades if t["is_user_executed"]]
    closed_trades = [t for t in executed_trades if t["actual_pnl"] is not None]

    total_realized_pnl = sum(t["actual_pnl"] for t in closed_trades) if closed_trades else 0.0
    winning = [t for t in closed_trades if t["actual_pnl"] > 0]
    losing = [t for t in closed_trades if t["actual_pnl"] <= 0]
    win_rate = round(len(winning) / len(closed_trades) * 100.0, 1) if closed_trades else 0.0

    return {
        "total_records": len(trades),
        "executed_trades_count": len(executed_trades),
        "closed_trades_count": len(closed_trades),
        "open_trades_count": len(executed_trades) - len(closed_trades),
        "winning_trades_count": len(winning),
        "losing_trades_count": len(losing),
        "win_rate_pct": win_rate,
        "total_realized_pnl": round(total_realized_pnl, 2)
    }
