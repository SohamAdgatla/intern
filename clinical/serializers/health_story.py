from rest_framework import serializers


class BiomarkerChangeSerializer(serializers.Serializer):
    start_value = serializers.FloatField()
    end_value = serializers.FloatField()
    percent_change = serializers.FloatField()
    months_span = serializers.FloatField()
    direction = serializers.CharField()


class BiomarkerHighlightSerializer(serializers.Serializer):
    loinc_code = serializers.CharField()
    friendly_name = serializers.CharField()
    narrative = serializers.CharField()
    tone = serializers.CharField()
    trend_label = serializers.CharField()
    latest_value = serializers.FloatField(allow_null=True)
    in_reference_range = serializers.BooleanField(allow_null=True)
    change = BiomarkerChangeSerializer(allow_null=True)


class HealthStorySerializer(serializers.Serializer):
    patient_id = serializers.IntegerField()
    headline = serializers.CharField()
    overview = serializers.CharField()
    paragraphs = serializers.ListField(child=serializers.CharField())
    highlights = BiomarkerHighlightSerializer(many=True)
    encouragement = serializers.CharField()
    lookback_months = serializers.IntegerField()
    generated_at = serializers.DateTimeField()
