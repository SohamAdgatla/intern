from rest_framework import serializers

from clinical.constants.measurements import MEASUREMENT_TYPES


class MeasurementTypeSerializer(serializers.Serializer):
    loinc_code = serializers.CharField()
    display = serializers.CharField()
    category = serializers.CharField()
    unit = serializers.CharField()
    reference_low = serializers.FloatField(allow_null=True)
    reference_high = serializers.FloatField(allow_null=True)


class ObservationSubmitSerializer(serializers.Serializer):
    loinc_code = serializers.CharField()
    value_quantity = serializers.FloatField(required=False, allow_null=True)
    value_unit = serializers.CharField(required=False, allow_blank=True, default="")
    note = serializers.CharField(required=False, allow_blank=True, default="")
    effective_datetime = serializers.DateTimeField(required=False, allow_null=True)
    caption = serializers.CharField(required=False, allow_blank=True, default="")
    capture_source = serializers.ChoiceField(
        choices=["camera", "file"],
        required=False,
        default="camera",
    )

    def validate_loinc_code(self, value):
        codes = {m["loinc_code"] for m in MEASUREMENT_TYPES}
        if value not in codes:
            raise serializers.ValidationError("Unsupported measurement type.")
        return value


class ObservationResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    fhir_id = serializers.UUIDField()
    loinc_code = serializers.CharField()
    display = serializers.CharField()
    value_quantity = serializers.FloatField(allow_null=True)
    value_unit = serializers.CharField()
    effective_datetime = serializers.DateTimeField()
    in_reference_range = serializers.BooleanField(allow_null=True)


class AttachmentResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    fhir_id = serializers.UUIDField()
    image_url = serializers.CharField(allow_null=True)
    capture_source = serializers.CharField()
    caption = serializers.CharField()
    uploaded_at = serializers.DateTimeField()
    observation_id = serializers.IntegerField(allow_null=True)


class SubmitResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    observation = ObservationResponseSerializer(required=False, allow_null=True)
    attachment = AttachmentResponseSerializer(required=False, allow_null=True)


def measurement_types_payload():
    return MeasurementTypeSerializer(MEASUREMENT_TYPES, many=True).data
