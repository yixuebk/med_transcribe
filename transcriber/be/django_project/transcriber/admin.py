"""Transcriber App Admin Config"""
from django.contrib import admin

from .models import Transcription

# Register your models here.

class TranscriptionAdmin(admin.ModelAdmin):
    """Transcription Admin"""
    list_display = (
        'filename',
        'transcript',
        'edited_transcript',
        'formatted_text',
        'audio_created_at'
    )

admin.site.register(Transcription, TranscriptionAdmin)
