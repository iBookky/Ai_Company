import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

BASE_DIR = Path(__file__).parent.parent.parent
USAGE_FILE = BASE_DIR / "logs" / "model_usage.json"
LIMITS_FILE = BASE_DIR / "logs" / "model_limits.json"

# Rate pricing per 1 Million tokens (input / output) in USD
MODEL_RATES = {
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
}

DEFAULT_LIMITS = {
    "monthly_token_limit": 10000000,  # 10 Million Tokens
    "monthly_cost_limit": 50.0,       # 50 USD
}


def load_limits() -> dict:
    if LIMITS_FILE.exists():
        try:
            return json.loads(LIMITS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return DEFAULT_LIMITS


def save_limits(limits: dict):
    LIMITS_FILE.parent.mkdir(parents=True, exist_ok=True)
    LIMITS_FILE.write_text(json.dumps(limits, ensure_ascii=False, indent=2), encoding="utf-8")


def load_usage() -> list:
    if USAGE_FILE.exists():
        try:
            return json.loads(USAGE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def save_usage(usage_list: list):
    USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    USAGE_FILE.write_text(json.dumps(usage_list, ensure_ascii=False, indent=2), encoding="utf-8")


def record_usage(model: str, input_tokens: int, output_tokens: int):
    # Sanitize model name
    model = model.replace("models/", "")
    
    usage_list = load_usage()
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_month = datetime.now().strftime("%Y-%m")
    
    # Calculate pricing
    rates = MODEL_RATES.get(model, {"input": 0.15, "output": 0.60})
    cost = ((input_tokens / 1000000.0) * rates["input"]) + ((output_tokens / 1000000.0) * rates["output"])
    
    found = False
    for entry in usage_list:
        if entry.get("date") == current_date and entry.get("model") == model:
            entry["input_tokens"] = entry.get("input_tokens", 0) + input_tokens
            entry["output_tokens"] = entry.get("output_tokens", 0) + output_tokens
            entry["total_tokens"] = entry["input_tokens"] + entry["output_tokens"]
            entry["cost"] = entry.get("cost", 0.0) + cost
            entry["requests"] = entry.get("requests", 0) + 1
            found = True
            break
            
    if not found:
        usage_list.append({
            "date": current_date,
            "month": current_month,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost": cost,
            "requests": 1
        })
        
    save_usage(usage_list)


def get_usage_summary() -> dict:
    usage_list = load_usage()
    limits = load_limits()
    current_month = datetime.now().strftime("%Y-%m")
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    month_input = 0
    month_output = 0
    month_tokens = 0
    month_cost = 0.0
    month_requests = 0
    
    today_tokens = 0
    today_cost = 0.0
    
    model_stats = {}
    
    for entry in usage_list:
        # Today
        if entry.get("date") == current_date:
            today_tokens += entry.get("total_tokens", 0)
            today_cost += entry.get("cost", 0.0)
            
        # Month
        if entry.get("month") == current_month:
            input_t = entry.get("input_tokens", 0)
            output_t = entry.get("output_tokens", 0)
            tot_t = entry.get("total_tokens", 0)
            c = entry.get("cost", 0.0)
            reqs = entry.get("requests", 1)
            
            month_input += input_t
            month_output += output_t
            month_tokens += tot_t
            month_cost += c
            month_requests += reqs
            
            model = entry.get("model", "unknown")
            if model not in model_stats:
                model_stats[model] = {"tokens": 0, "cost": 0.0, "requests": 0}
            model_stats[model]["tokens"] += tot_t
            model_stats[model]["cost"] += c
            model_stats[model]["requests"] += reqs

    monthly_token_limit = limits.get("monthly_token_limit", 10000000)
    monthly_cost_limit = limits.get("monthly_cost_limit", 50.0)
    
    remaining_tokens = max(0, monthly_token_limit - month_tokens)
    remaining_cost = max(0.0, monthly_cost_limit - month_cost)
    
    # Generate daily history
    history = {}
    for entry in usage_list:
        date = entry.get("date")
        if date not in history:
            history[date] = {"tokens": 0, "cost": 0.0, "requests": 0}
        history[date]["tokens"] += entry.get("total_tokens", 0)
        history[date]["cost"] += entry.get("cost", 0.0)
        history[date]["requests"] += entry.get("requests", 0)
        
    history_sorted = [{"date": k, **v} for k, v in sorted(history.items(), reverse=True)]
    
    return {
        "monthly_limit_tokens": monthly_token_limit,
        "monthly_limit_cost": monthly_cost_limit,
        "month_used_tokens": month_tokens,
        "month_used_cost": month_cost,
        "month_remaining_tokens": remaining_tokens,
        "month_remaining_cost": remaining_cost,
        "month_requests": month_requests,
        "today_used_tokens": today_tokens,
        "today_used_cost": today_cost,
        "model_stats": model_stats,
        "history": history_sorted[:30]
    }
