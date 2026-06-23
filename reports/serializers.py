from rest_framework import serializers
from .models import ContentReport, CopyrightReport


class ContentReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentReport
        fields = ['reason', 'details']


class CopyrightReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = CopyrightReport
        fields = [
            'reporter_name',
            'reporter_email',
            'video',
            'work_description',
            'original_url',
            'good_faith_statement',
            'accuracy_statement',
        ]

    def validate(self, data):
        if not data.get('good_faith_statement'):
            raise serializers.ValidationError(
                {'good_faith_statement': 'Debés confirmar que tu denuncia es de buena fe.'}
            )
        if not data.get('accuracy_statement'):
            raise serializers.ValidationError(
                {'accuracy_statement': 'Debés confirmar que la información es exacta.'}
            )
        return data
