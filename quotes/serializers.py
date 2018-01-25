from rest_framework import serializers

from quotes.models import Quote, QuoteVote


class QuoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quote
        fields = ('url', 'id', 'text', 'quoter', 'sum', 'verified_by',)


class QuoteVoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuoteVote
        fields = ('url', 'id', 'quote', 'value', 'caster',)
