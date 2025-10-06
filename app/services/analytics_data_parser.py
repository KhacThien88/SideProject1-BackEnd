import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import statistics
import json

logger = logging.getLogger(__name__)


class AnalyticsDataParser:
    """Parser for converting raw analytics data into actionable insights"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Insight thresholds
        self.thresholds = {
            'high_performance': 0.8,
            'medium_performance': 0.6,
            'low_performance': 0.4,
            'trend_increase': 0.1,
            'trend_decrease': -0.1,
            'significant_change': 0.2
        }
        
        # Metric categories
        self.metric_categories = {
            'performance': ['match_score', 'success_rate', 'completion_rate'],
            'engagement': ['views', 'clicks', 'applications', 'time_spent'],
            'quality': ['accuracy', 'precision', 'recall', 'f1_score'],
            'efficiency': ['response_time', 'processing_time', 'throughput'],
            'growth': ['user_count', 'job_count', 'revenue', 'conversion_rate']
        }
    
    def parse_analytics_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse raw analytics data into structured insights
        
        Args:
            raw_data: Raw analytics data
            
        Returns:
            Dictionary containing parsed insights and recommendations
        """
        try:
            self.logger.info("Starting analytics data parsing")
            
            parsed_data = {
                'raw_data': raw_data,
                'metrics': {},
                'insights': {},
                'trends': {},
                'recommendations': [],
                'metadata': {
                    'parsed_at': datetime.utcnow().isoformat(),
                    'data_period': self._get_data_period(raw_data),
                    'data_quality_score': 0.0
                }
            }
            
            # Parse metrics
            parsed_data['metrics'] = self._parse_metrics(raw_data)
            
            # Generate insights
            parsed_data['insights'] = self._generate_insights(parsed_data['metrics'])
            
            # Analyze trends
            parsed_data['trends'] = self._analyze_trends(raw_data)
            
            # Generate recommendations
            parsed_data['recommendations'] = self._generate_recommendations(parsed_data)
            
            # Calculate data quality score
            parsed_data['metadata']['data_quality_score'] = self._calculate_data_quality(raw_data)
            
            self.logger.info("Analytics data parsing completed")
            return parsed_data
            
        except Exception as e:
            self.logger.error(f"Error parsing analytics data: {e}")
            return {
                'raw_data': raw_data,
                'error': str(e),
                'parsed_at': datetime.utcnow().isoformat()
            }
    
    def _get_data_period(self, raw_data: Dict[str, Any]) -> str:
        """Get data period from raw data"""
        if 'start_date' in raw_data and 'end_date' in raw_data:
            return f"{raw_data['start_date']} to {raw_data['end_date']}"
        elif 'period' in raw_data:
            return raw_data['period']
        else:
            return 'unknown'
    
    def _parse_metrics(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse metrics from raw data"""
        metrics = {
            'performance': {},
            'engagement': {},
            'quality': {},
            'efficiency': {},
            'growth': {}
        }
        
        # Extract performance metrics
        if 'performance' in raw_data:
            metrics['performance'] = self._parse_performance_metrics(raw_data['performance'])
        
        # Extract engagement metrics
        if 'engagement' in raw_data:
            metrics['engagement'] = self._parse_engagement_metrics(raw_data['engagement'])
        
        # Extract quality metrics
        if 'quality' in raw_data:
            metrics['quality'] = self._parse_quality_metrics(raw_data['quality'])
        
        # Extract efficiency metrics
        if 'efficiency' in raw_data:
            metrics['efficiency'] = self._parse_efficiency_metrics(raw_data['efficiency'])
        
        # Extract growth metrics
        if 'growth' in raw_data:
            metrics['growth'] = self._parse_growth_metrics(raw_data['growth'])
        
        return metrics
    
    def _parse_performance_metrics(self, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse performance metrics"""
        metrics = {}
        
        # Match scores
        if 'match_scores' in performance_data:
            scores = performance_data['match_scores']
            metrics['match_score'] = {
                'average': statistics.mean(scores) if scores else 0,
                'median': statistics.median(scores) if scores else 0,
                'min': min(scores) if scores else 0,
                'max': max(scores) if scores else 0,
                'count': len(scores)
            }
        
        # Success rates
        if 'success_rates' in performance_data:
            rates = performance_data['success_rates']
            metrics['success_rate'] = {
                'average': statistics.mean(rates) if rates else 0,
                'trend': self._calculate_trend(rates),
                'count': len(rates)
            }
        
        return metrics
    
    def _parse_engagement_metrics(self, engagement_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse engagement metrics"""
        metrics = {}
        
        # Views
        if 'views' in engagement_data:
            views = engagement_data['views']
            metrics['views'] = {
                'total': sum(views.values()) if isinstance(views, dict) else views,
                'daily_average': self._calculate_daily_average(views),
                'trend': self._calculate_trend(list(views.values()) if isinstance(views, dict) else [views])
            }
        
        # Applications
        if 'applications' in engagement_data:
            apps = engagement_data['applications']
            metrics['applications'] = {
                'total': sum(apps.values()) if isinstance(apps, dict) else apps,
                'conversion_rate': self._calculate_conversion_rate(engagement_data),
                'trend': self._calculate_trend(list(apps.values()) if isinstance(apps, dict) else [apps])
            }
        
        return metrics
    
    def _parse_quality_metrics(self, quality_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse quality metrics"""
        metrics = {}
        
        # Accuracy
        if 'accuracy' in quality_data:
            metrics['accuracy'] = {
                'value': quality_data['accuracy'],
                'level': self._get_performance_level(quality_data['accuracy']),
                'trend': quality_data.get('accuracy_trend', 0)
            }
        
        # Precision and Recall
        if 'precision' in quality_data and 'recall' in quality_data:
            precision = quality_data['precision']
            recall = quality_data['recall']
            f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            metrics['precision'] = precision
            metrics['recall'] = recall
            metrics['f1_score'] = f1_score
        
        return metrics
    
    def _parse_efficiency_metrics(self, efficiency_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse efficiency metrics"""
        metrics = {}
        
        # Response time
        if 'response_times' in efficiency_data:
            times = efficiency_data['response_times']
            metrics['response_time'] = {
                'average': statistics.mean(times) if times else 0,
                'median': statistics.median(times) if times else 0,
                'p95': self._calculate_percentile(times, 95) if times else 0,
                'trend': self._calculate_trend(times)
            }
        
        # Throughput
        if 'throughput' in efficiency_data:
            metrics['throughput'] = {
                'requests_per_second': efficiency_data['throughput'],
                'trend': efficiency_data.get('throughput_trend', 0)
            }
        
        return metrics
    
    def _parse_growth_metrics(self, growth_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse growth metrics"""
        metrics = {}
        
        # User growth
        if 'user_count' in growth_data:
            user_counts = growth_data['user_count']
            metrics['user_growth'] = {
                'current': user_counts[-1] if user_counts else 0,
                'growth_rate': self._calculate_growth_rate(user_counts),
                'trend': self._calculate_trend(user_counts)
            }
        
        # Revenue growth
        if 'revenue' in growth_data:
            revenue = growth_data['revenue']
            metrics['revenue_growth'] = {
                'current': revenue[-1] if revenue else 0,
                'growth_rate': self._calculate_growth_rate(revenue),
                'trend': self._calculate_trend(revenue)
            }
        
        return metrics
    
    def _generate_insights(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights from metrics"""
        insights = {
            'performance_insights': [],
            'engagement_insights': [],
            'quality_insights': [],
            'efficiency_insights': [],
            'growth_insights': [],
            'overall_score': 0.0
        }
        
        # Performance insights
        if 'performance' in metrics:
            insights['performance_insights'] = self._generate_performance_insights(metrics['performance'])
        
        # Engagement insights
        if 'engagement' in metrics:
            insights['engagement_insights'] = self._generate_engagement_insights(metrics['engagement'])
        
        # Quality insights
        if 'quality' in metrics:
            insights['quality_insights'] = self._generate_quality_insights(metrics['quality'])
        
        # Efficiency insights
        if 'efficiency' in metrics:
            insights['efficiency_insights'] = self._generate_efficiency_insights(metrics['efficiency'])
        
        # Growth insights
        if 'growth' in metrics:
            insights['growth_insights'] = self._generate_growth_insights(metrics['growth'])
        
        # Calculate overall score
        insights['overall_score'] = self._calculate_overall_score(insights)
        
        return insights
    
    def _generate_performance_insights(self, performance_metrics: Dict[str, Any]) -> List[str]:
        """Generate performance insights"""
        insights = []
        
        if 'match_score' in performance_metrics:
            avg_score = performance_metrics['match_score']['average']
            if avg_score >= self.thresholds['high_performance']:
                insights.append(f"Excellent match performance with {avg_score:.2f} average score")
            elif avg_score >= self.thresholds['medium_performance']:
                insights.append(f"Good match performance with {avg_score:.2f} average score")
            else:
                insights.append(f"Match performance needs improvement (current: {avg_score:.2f})")
        
        if 'success_rate' in performance_metrics:
            success_rate = performance_metrics['success_rate']['average']
            if success_rate >= 0.8:
                insights.append(f"High success rate of {success_rate:.1%}")
            elif success_rate >= 0.6:
                insights.append(f"Moderate success rate of {success_rate:.1%}")
            else:
                insights.append(f"Low success rate of {success_rate:.1%} - needs attention")
        
        return insights
    
    def _generate_engagement_insights(self, engagement_metrics: Dict[str, Any]) -> List[str]:
        """Generate engagement insights"""
        insights = []
        
        if 'views' in engagement_metrics:
            total_views = engagement_metrics['views']['total']
            trend = engagement_metrics['views']['trend']
            
            if trend > self.thresholds['trend_increase']:
                insights.append(f"View engagement is growing strongly (+{trend:.1%})")
            elif trend < self.thresholds['trend_decrease']:
                insights.append(f"View engagement is declining ({trend:.1%}) - needs attention")
            else:
                insights.append(f"View engagement is stable ({total_views:,} total views)")
        
        if 'applications' in engagement_metrics:
            conversion_rate = engagement_metrics['applications']['conversion_rate']
            if conversion_rate >= 0.1:
                insights.append(f"Strong conversion rate of {conversion_rate:.1%}")
            elif conversion_rate >= 0.05:
                insights.append(f"Moderate conversion rate of {conversion_rate:.1%}")
            else:
                insights.append(f"Low conversion rate of {conversion_rate:.1%} - optimization needed")
        
        return insights
    
    def _generate_quality_insights(self, quality_metrics: Dict[str, Any]) -> List[str]:
        """Generate quality insights"""
        insights = []
        
        if 'accuracy' in quality_metrics:
            accuracy = quality_metrics['accuracy']['value']
            level = quality_metrics['accuracy']['level']
            insights.append(f"System accuracy is {level} ({accuracy:.1%})")
        
        if 'f1_score' in quality_metrics:
            f1_score = quality_metrics['f1_score']
            if f1_score >= 0.8:
                insights.append(f"Excellent F1 score of {f1_score:.2f}")
            elif f1_score >= 0.6:
                insights.append(f"Good F1 score of {f1_score:.2f}")
            else:
                insights.append(f"F1 score needs improvement ({f1_score:.2f})")
        
        return insights
    
    def _generate_efficiency_insights(self, efficiency_metrics: Dict[str, Any]) -> List[str]:
        """Generate efficiency insights"""
        insights = []
        
        if 'response_time' in efficiency_metrics:
            avg_time = efficiency_metrics['response_time']['average']
            p95_time = efficiency_metrics['response_time']['p95']
            
            if avg_time <= 1.0:
                insights.append(f"Fast response times (avg: {avg_time:.2f}s)")
            elif avg_time <= 3.0:
                insights.append(f"Moderate response times (avg: {avg_time:.2f}s)")
            else:
                insights.append(f"Slow response times (avg: {avg_time:.2f}s) - optimization needed")
            
            if p95_time > avg_time * 2:
                insights.append(f"High response time variance (P95: {p95_time:.2f}s)")
        
        return insights
    
    def _generate_growth_insights(self, growth_metrics: Dict[str, Any]) -> List[str]:
        """Generate growth insights"""
        insights = []
        
        if 'user_growth' in growth_metrics:
            growth_rate = growth_metrics['user_growth']['growth_rate']
            if growth_rate > 0.1:
                insights.append(f"Strong user growth (+{growth_rate:.1%})")
            elif growth_rate > 0:
                insights.append(f"Moderate user growth (+{growth_rate:.1%})")
            else:
                insights.append(f"User growth is declining ({growth_rate:.1%})")
        
        if 'revenue_growth' in growth_metrics:
            revenue_growth = growth_metrics['revenue_growth']['growth_rate']
            if revenue_growth > 0.2:
                insights.append(f"Excellent revenue growth (+{revenue_growth:.1%})")
            elif revenue_growth > 0.05:
                insights.append(f"Good revenue growth (+{revenue_growth:.1%})")
            else:
                insights.append(f"Revenue growth is slow (+{revenue_growth:.1%})")
        
        return insights
    
    def _analyze_trends(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze trends in the data"""
        trends = {
            'overall_trend': 'stable',
            'trend_strength': 0.0,
            'key_trends': [],
            'anomalies': []
        }
        
        # Analyze time series data
        time_series_data = self._extract_time_series(raw_data)
        
        for metric_name, values in time_series_data.items():
            if len(values) >= 3:  # Need at least 3 data points
                trend = self._calculate_trend(values)
                trend_strength = abs(trend)
                
                if trend_strength > self.thresholds['significant_change']:
                    trend_direction = 'increasing' if trend > 0 else 'decreasing'
                    trends['key_trends'].append({
                        'metric': metric_name,
                        'direction': trend_direction,
                        'strength': trend_strength,
                        'trend': trend
                    })
        
        # Calculate overall trend
        if trends['key_trends']:
            avg_trend = statistics.mean([t['trend'] for t in trends['key_trends']])
            trends['overall_trend'] = 'increasing' if avg_trend > 0.05 else 'decreasing' if avg_trend < -0.05 else 'stable'
            trends['trend_strength'] = abs(avg_trend)
        
        return trends
    
    def _generate_recommendations(self, parsed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate actionable recommendations"""
        recommendations = []
        
        insights = parsed_data['insights']
        metrics = parsed_data['metrics']
        
        # Performance recommendations
        if 'performance' in metrics:
            perf_metrics = metrics['performance']
            if 'match_score' in perf_metrics:
                avg_score = perf_metrics['match_score']['average']
                if avg_score < self.thresholds['medium_performance']:
                    recommendations.append({
                        'category': 'performance',
                        'priority': 'high',
                        'title': 'Improve Match Algorithm',
                        'description': f'Current match score ({avg_score:.2f}) is below optimal. Consider refining matching criteria.',
                        'action': 'Review and update matching algorithm parameters'
                    })
        
        # Engagement recommendations
        if 'engagement' in metrics:
            eng_metrics = metrics['engagement']
            if 'applications' in eng_metrics:
                conversion_rate = eng_metrics['applications']['conversion_rate']
                if conversion_rate < 0.05:
                    recommendations.append({
                        'category': 'engagement',
                        'priority': 'medium',
                        'title': 'Improve User Experience',
                        'description': f'Low conversion rate ({conversion_rate:.1%}) suggests UX issues.',
                        'action': 'Conduct user research and improve application flow'
                    })
        
        # Efficiency recommendations
        if 'efficiency' in metrics:
            eff_metrics = metrics['efficiency']
            if 'response_time' in eff_metrics:
                avg_time = eff_metrics['response_time']['average']
                if avg_time > 3.0:
                    recommendations.append({
                        'category': 'efficiency',
                        'priority': 'high',
                        'title': 'Optimize Performance',
                        'description': f'Response time ({avg_time:.2f}s) is too slow.',
                        'action': 'Implement caching and optimize database queries'
                    })
        
        return recommendations
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend direction and strength"""
        if len(values) < 2:
            return 0.0
        
        # Simple linear trend calculation
        n = len(values)
        x = list(range(n))
        
        # Calculate slope
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        
        if n * sum_x2 - sum_x ** 2 == 0:
            return 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        
        # Normalize by average value
        avg_value = sum_y / n
        if avg_value == 0:
            return 0.0
        
        return slope / avg_value
    
    def _calculate_daily_average(self, data: Union[Dict, List, float]) -> float:
        """Calculate daily average from data"""
        if isinstance(data, dict):
            return sum(data.values()) / len(data) if data else 0
        elif isinstance(data, list):
            return sum(data) / len(data) if data else 0
        else:
            return float(data) if data else 0
    
    def _calculate_conversion_rate(self, engagement_data: Dict[str, Any]) -> float:
        """Calculate conversion rate from engagement data"""
        views = engagement_data.get('views', 0)
        applications = engagement_data.get('applications', 0)
        
        if isinstance(views, dict):
            views = sum(views.values())
        if isinstance(applications, dict):
            applications = sum(applications.values())
        
        return applications / views if views > 0 else 0
    
    def _calculate_growth_rate(self, values: List[float]) -> float:
        """Calculate growth rate from time series"""
        if len(values) < 2:
            return 0.0
        
        first_value = values[0]
        last_value = values[-1]
        
        if first_value == 0:
            return 0.0
        
        return (last_value - first_value) / first_value
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int((percentile / 100) * len(sorted_values))
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def _get_performance_level(self, value: float) -> str:
        """Get performance level description"""
        if value >= self.thresholds['high_performance']:
            return 'excellent'
        elif value >= self.thresholds['medium_performance']:
            return 'good'
        elif value >= self.thresholds['low_performance']:
            return 'fair'
        else:
            return 'poor'
    
    def _calculate_overall_score(self, insights: Dict[str, Any]) -> float:
        """Calculate overall performance score"""
        # Simple scoring based on insight categories
        scores = []
        
        for category in ['performance', 'engagement', 'quality', 'efficiency', 'growth']:
            category_insights = insights.get(f'{category}_insights', [])
            if category_insights:
                # Count positive vs negative insights
                positive_count = sum(1 for insight in category_insights if any(word in insight.lower() for word in ['excellent', 'strong', 'high', 'good', 'fast']))
                total_count = len(category_insights)
                category_score = positive_count / total_count if total_count > 0 else 0.5
                scores.append(category_score)
        
        return statistics.mean(scores) if scores else 0.5
    
    def _calculate_data_quality(self, raw_data: Dict[str, Any]) -> float:
        """Calculate data quality score"""
        quality_score = 0.0
        total_checks = 0
        
        # Check for required fields
        required_fields = ['start_date', 'end_date', 'metrics']
        for field in required_fields:
            total_checks += 1
            if field in raw_data:
                quality_score += 1
        
        # Check for data completeness
        if 'metrics' in raw_data:
            metrics = raw_data['metrics']
            metric_categories = ['performance', 'engagement', 'quality']
            for category in metric_categories:
                total_checks += 1
                if category in metrics and metrics[category]:
                    quality_score += 1
        
        return quality_score / total_checks if total_checks > 0 else 0.0
    
    def _extract_time_series(self, raw_data: Dict[str, Any]) -> Dict[str, List[float]]:
        """Extract time series data from raw data"""
        time_series = {}
        
        # Look for time series data in metrics
        if 'metrics' in raw_data:
            metrics = raw_data['metrics']
            for category, category_data in metrics.items():
                if isinstance(category_data, dict):
                    for metric_name, metric_data in category_data.items():
                        if isinstance(metric_data, list) and all(isinstance(x, (int, float)) for x in metric_data):
                            time_series[f"{category}_{metric_name}"] = metric_data
        
        return time_series


# Global instance
analytics_data_parser = AnalyticsDataParser()
