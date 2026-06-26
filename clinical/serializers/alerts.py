from rest_framework import serializers


class SmartAlertSerializer(serializers.Serializer):
    id = serializers.CharField()
    severity = serializers.CharField()
    category = serializers.CharField()
    title = serializers.CharField()
    message = serializers.CharField()
    action_hint = serializers.CharField()
    detected_at = serializers.DateTimeField()
    metadata = serializers.DictField()


class SmartAlertsResponseSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField()
    generated_at = serializers.DateTimeField()
    alert_count = serializers.IntegerField()
    alerts = SmartAlertSerializer(many=True)
