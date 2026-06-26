from rest_framework import serializers


class TimelineCodingSerializer(serializers.Serializer):
    system = serializers.CharField()
    code = serializers.CharField()
    display = serializers.CharField()
    version = serializers.CharField(allow_blank=True)


class TimelineEventSerializer(serializers.Serializer):
    id = serializers.CharField()
    resource_type = serializers.ChoiceField(choices=["observation", "condition", "medication"])
    resource_id = serializers.IntegerField()
    fhir_id = serializers.UUIDField()
    sort_datetime = serializers.DateTimeField()
    effective_datetime = serializers.DateTimeField(allow_null=True)
    recorded_datetime = serializers.DateTimeField(allow_null=True)
    title = serializers.CharField()
    subtitle = serializers.CharField(allow_blank=True)
    summary = serializers.CharField()
    status = serializers.CharField()
    category = serializers.CharField()
    coding = TimelineCodingSerializer()
    details = serializers.DictField()


class TimelineCountsSerializer(serializers.Serializer):
    observation = serializers.IntegerField()
    condition = serializers.IntegerField()
    medication = serializers.IntegerField()


class TimelineFiltersSerializer(serializers.Serializer):
    from_datetime = serializers.DateTimeField(allow_null=True)
    to_datetime = serializers.DateTimeField(allow_null=True)
    resource_types = serializers.ListField(child=serializers.CharField(), allow_null=True)
    observation_categories = serializers.ListField(child=serializers.CharField(), allow_null=True)
    include_cancelled = serializers.BooleanField()
    limit = serializers.IntegerField(allow_null=True)


class TimelineResponseSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField()
    generated_at = serializers.DateTimeField()
    total_events = serializers.IntegerField()
    returned_events = serializers.IntegerField()
    counts_by_type = TimelineCountsSerializer()
    filters = TimelineFiltersSerializer()
    events = TimelineEventSerializer(many=True)
