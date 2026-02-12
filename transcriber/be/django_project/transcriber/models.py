"""Transcriber App Models"""
from django.db import models
from ckeditor.fields import RichTextField

# Create your models here.

class Transcription(models.Model):
    """Transcriber Model"""
    filename = models.TextField(primary_key=True, unique=True)
    transcript = models.TextField(null=True)
    edited_transcript = models.TextField(null=True)
    formatted_text = RichTextField(null=True)
    audio_created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.filename)
