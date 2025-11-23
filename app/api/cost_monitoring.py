"""Google API cost monitoring and analytics.

This module provides cost monitoring functionality for Google API usage,
including cost tracking, analytics, and optimization recommendations.

Following TIGER principles:
- Testing: Cost calculations are pure and testable
- Interfaces: Simple cost monitoring API
- Generality: Reusable cost tracking patterns
- Examples: Clear cost analysis examples
- Refactoring: Single responsibility for cost monitoring
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from flask import Response, jsonify, request
from flask_login import login_required

from app.config.cost_optimization import CostOptimizer

from . import bp

logger = logging.getLogger(__name__)


@bp.route("/cost-monitoring/stats", methods=["GET"])
@login_required
def get_cost_stats() -> Response:
    """Get Google API cost statistics and analytics.

    Returns:
        JSON response with cost statistics
    """
    try:
        # Get date range from query parameters
        days = int(request.args.get("days", 7))
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Get cost statistics
        stats = _calculate_cost_statistics(start_date, end_date)

        return jsonify({"status": "success", "data": stats, "message": f"Cost statistics for last {days} days"})

    except Exception as e:
        logger.error(f"Error getting cost stats: {e}")
        return jsonify({"status": "error", "message": "Failed to retrieve cost statistics"}), 500


@bp.route("/cost-monitoring/optimization", methods=["GET"])
@login_required
def get_optimization_recommendations() -> Response:
    """Get cost optimization recommendations.

    Returns:
        JSON response with optimization recommendations
    """
    try:
        # Get optimization recommendations
        recommendations = _get_optimization_recommendations()

        return jsonify(
            {
                "status": "success",
                "data": recommendations,
                "message": "Cost optimization recommendations",
            }
        )

    except Exception as e:
        logger.error(f"Error getting optimization recommendations: {e}")
        return (
            jsonify({"status": "error", "message": "Failed to retrieve optimization recommendations"}),
            500,
        )


@bp.route("/cost-monitoring/cache-stats", methods=["GET"])
@login_required
def get_cache_stats() -> Response:
    """Get cache performance statistics.

    Returns:
        JSON response with cache statistics
    """
    try:
        # Get cache statistics
        cache_stats = _get_cache_performance_stats()

        return jsonify({"status": "success", "data": cache_stats, "message": "Cache performance statistics"})

    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return jsonify({"status": "error", "message": "Failed to retrieve cache statistics"}), 500


def _calculate_cost_statistics(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """Calculate cost statistics for the given date range.

    Args:
        start_date: Start date for statistics
        end_date: End date for statistics

    Returns:
        Dictionary with cost statistics
    """
    # This would typically query a cost tracking database
    # For now, we'll simulate with mock data

    # Mock API call data (in production, this would come from a database)
    mock_api_calls = {
        "text_search": 150,
        "nearby_search": 75,
        "place_details": 200,
        "place_photos": 300,
        "autocomplete": 500,
    }

    # Calculate costs
    costs = CostOptimizer.estimate_api_cost(mock_api_calls)

    # Calculate daily averages
    days = (end_date - start_date).days or 1
    daily_calls = {api_type: count // days for api_type, count in mock_api_calls.items()}
    daily_costs = CostOptimizer.estimate_api_cost(daily_calls)

    # Calculate trends (mock data)
    previous_period_calls = {
        "text_search": 120,
        "nearby_search": 60,
        "place_details": 180,
        "place_photos": 250,
        "autocomplete": 400,
    }

    trends = {}
    for api_type in mock_api_calls:
        current = mock_api_calls[api_type]
        previous = previous_period_calls[api_type]
        change = ((current - previous) / previous * 100) if previous > 0 else 0
        trends[api_type] = {
            "change_percentage": round(change, 1),
            "change_direction": "up" if change > 0 else "down" if change < 0 else "stable",
        }

    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": days,
        },
        "api_calls": mock_api_calls,
        "costs": costs,
        "daily_averages": {
            "api_calls": daily_calls,
            "costs": daily_costs,
        },
        "trends": trends,
        "total_cost": costs["total"],
        "daily_average_cost": daily_costs["total"],
    }


def _get_optimization_recommendations() -> Dict[str, Any]:
    """Get cost optimization recommendations.

    Returns:
        Dictionary with optimization recommendations
    """
    recommendations = []

    # Check cache performance
    cache_stats = _get_cache_performance_stats()
    if cache_stats["hit_rate"] < 0.7:
        recommendations.append(
            {
                "type": "caching",
                "priority": "high",
                "title": "Improve Cache Hit Rate",
                "description": f"Current cache hit rate is {cache_stats['hit_rate']:.1%}. Increase to 70%+ for significant cost savings.",
                "estimated_savings": "30-50%",
                "action": "Review cache TTL settings and ensure proper cache key generation",
            }
        )

    # Check field mask usage
    recommendations.append(
        {
            "type": "field_masks",
            "priority": "medium",
            "title": "Optimize Field Masks",
            "description": "Use minimal field masks for search results to reduce API costs.",
            "estimated_savings": "20-30%",
            "action": "Switch from 'comprehensive' to 'search_essential' field masks for search operations",
        }
    )

    # Check photo usage
    recommendations.append(
        {
            "type": "photos",
            "priority": "medium",
            "title": "Optimize Photo Loading",
            "description": "Load photos on demand instead of with every search result.",
            "estimated_savings": "15-25%",
            "action": "Implement lazy loading for restaurant photos",
        }
    )

    # Check search strategy
    recommendations.append(
        {
            "type": "search_strategy",
            "priority": "low",
            "title": "Optimize Search Strategy",
            "description": "Use nearby search when location is available for better cost efficiency.",
            "estimated_savings": "10-15%",
            "action": "Prioritize nearby search over text search when user location is available",
        }
    )

    # Calculate total potential savings
    total_savings = 0.0
    for rec in recommendations:
        savings_str = rec["estimated_savings"]
        if "30-50%" in savings_str:
            total_savings += 0.4  # Average of range
        elif "20-30%" in savings_str:
            total_savings += 0.25
        elif "15-25%" in savings_str:
            total_savings += 0.20
        elif "10-15%" in savings_str:
            total_savings += 0.125

    return {
        "recommendations": recommendations,
        "total_potential_savings": f"{total_savings:.1%}",
        "implementation_priority": sorted(recommendations, key=lambda x: x["priority"]),
    }


def _get_cache_performance_stats() -> Dict[str, Any]:
    """Get cache performance statistics.

    Returns:
        Dictionary with cache performance statistics
    """
    try:
        from app.services.google_places_cache import get_google_places_cache

        cache_service = get_google_places_cache()
        if not cache_service:
            return {
                "available": False,
                "message": "Cache service not available",
                "hit_rate": 0.0,
            }

        # Get cache statistics
        cache_stats = cache_service.get_cache_stats()

        if "error" in cache_stats:
            return {
                "available": False,
                "message": cache_stats["error"],
                "hit_rate": 0.0,
            }

        # Calculate hit rate (mock calculation)
        # In production, this would track actual hit/miss ratios
        total_entries = cache_stats["total"]["count"]
        hit_rate = min(0.85, max(0.3, total_entries / 1000))  # Mock hit rate calculation

        return {
            "available": True,
            "hit_rate": hit_rate,
            "total_entries": total_entries,
            "entries_by_type": cache_stats,
            "performance": {
                "excellent": hit_rate >= 0.8,
                "good": 0.6 <= hit_rate < 0.8,
                "needs_improvement": hit_rate < 0.6,
            },
        }

    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return {
            "available": False,
            "message": f"Error retrieving cache statistics: {str(e)}",
            "hit_rate": 0.0,
        }
