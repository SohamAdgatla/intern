from rest_framework import serializers


class RiskAssessmentSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField()
    risk_probability = serializers.FloatField()
    risk_percentage = serializers.FloatField()
    risk_label = serializers.CharField()
    model_version = serializers.CharField()
    assessed_at = serializers.DateTimeField()
    features = serializers.DictField(child=serializers.FloatField())
    trend_details = serializers.DictField()
    top_risk_drivers = serializers.ListField(child=serializers.DictField())
    preventative_suggestions = serializers.ListField(child=serializers.CharField())
