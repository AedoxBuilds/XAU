"""Broker-aware position sizing. Never hardcode XAUUSD pip values or contract sizes."""
import math


def size_from_loss_per_lot(risk_amount: float, loss_per_lot: float,
                           volume_min: float, volume_max: float,
                           volume_step: float) -> dict:
    if risk_amount <= 0 or loss_per_lot <= 0 or volume_step <= 0:
        raise ValueError("Risk amount, loss per lot and volume step must be positive.")
    raw = risk_amount / loss_per_lot
    stepped = math.floor((raw + 1e-12) / volume_step) * volume_step
    volume = round(min(stepped, volume_max), 8)
    if volume < volume_min:
        return {"volume": 0.0, "estimated_loss": 0.0, "risk_amount": risk_amount,
                "message": "Risk budget is below broker minimum volume."}
    return {"volume": volume, "estimated_loss": round(volume * loss_per_lot, 2),
            "risk_amount": risk_amount,
            "message": "Volume capped at broker maximum." if raw > volume_max else "OK"}


def mt5_position_size(mt5, symbol: str, order_type: int, entry: float, stop: float,
                      balance: float, risk_percent: float) -> dict:
    if balance <= 0 or not 0 < risk_percent <= 100:
        raise ValueError("Balance must be positive and risk_percent must be in (0, 100].")
    info = mt5.symbol_info(symbol)
    if info is None:
        raise RuntimeError(f"Unknown MT5 symbol: {symbol}")
    risk_amount = balance * risk_percent / 100.0
    loss = mt5.order_calc_profit(order_type, symbol, 1.0, entry, stop)
    if loss is None:
        raise RuntimeError(f"MT5 could not calculate stop loss: {mt5.last_error()}")
    result = size_from_loss_per_lot(risk_amount, abs(float(loss)), float(info.volume_min),
                                    float(info.volume_max), float(info.volume_step))
    result["loss_per_lot"] = round(abs(float(loss)), 2)
    result["risk_percent"] = risk_percent
    return result
