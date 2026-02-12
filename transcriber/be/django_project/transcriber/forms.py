"""Transcription App Forms"""
from django import forms
from django.core.validators import FileExtensionValidator
from ckeditor.widgets import CKEditorWidget


class BasicAudioFileUploadForm(forms.Form):
    """Basic image upload form, allowing only JPEG and PNG file extensions."""
    file = forms.FileField(
        validators=[FileExtensionValidator(allowed_extensions=['mp3', 'wav', 'webm'])],
        widget=forms.FileInput(attrs={'accept': 'audio/mp3, audio/wav, audio/webm'}),
    )

class EditTranscriptForm(forms.Form):
    """Form to edit a Transcription object's transcript field."""
    filename = forms.CharField(
        widget=forms.TextInput(attrs={'readonly': True}),
    )
    transcript = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 40,}),
    )

class TextInputForm(forms.Form):
    """Basic text input form."""
    input = forms.CharField(widget=forms.Textarea(
        attrs={
            'rows': 5,
            'style': 'width: 100%; resize: none;',
        }
    ), max_length=500)

class RichTextInputForm(forms.Form):
    """Basic rich text editor form."""
    text = forms.CharField(widget=CKEditorWidget())
