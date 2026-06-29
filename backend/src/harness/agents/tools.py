import json
import math


def get_weather(city: str) -> str:
    """Get the current weather for a city. Returns temperature and conditions."""
    weather_data = {
        "paris": {"temp": 22, "conditions": "Sunny", "humidity": 45},
        "london": {"temp": 15, "conditions": "Cloudy", "humidity": 78},
        "new york": {"temp": 28, "conditions": "Partly cloudy", "humidity": 60},
        "tokyo": {"temp": 26, "conditions": "Clear", "humidity": 55},
    }
    data = weather_data.get(city.lower(), {"temp": 20, "conditions": "Unknown", "humidity": 50})
    return json.dumps(data)


def calculate(expression: str) -> str:
    """Evaluate a mathematical expression. Supports basic arithmetic and math functions."""
    allowed_names = {
        "abs": abs, "round": round, "min": min, "max": max,
        "sqrt": math.sqrt, "pow": pow, "pi": math.pi, "e": math.e,
    }
    try:
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return str(result)
    except Exception as exc:
        return f"Error: {exc}"


def search_knowledge(query: str) -> str:
    """Search a knowledge base for information. Returns relevant text snippets."""
    knowledge = {
        "python": "Python is a high-level programming language created by Guido van Rossum in 1991.",
        "fastapi": "FastAPI is a modern Python web framework for building APIs, created by Sebastián Ramírez.",
        "machine learning": "Machine learning is a subset of AI that enables systems to learn from data.",
    }
    query_lower = query.lower()
    for key, value in knowledge.items():
        if key in query_lower:
            return value
    return "No relevant information found."
