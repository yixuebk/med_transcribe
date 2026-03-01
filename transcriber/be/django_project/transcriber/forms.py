"""Transcription App Forms"""
from django import forms
from django.core.validators import FileExtensionValidator
from ckeditor.widgets import CKEditorWidget

from django_project.settings import LOCAL_LLM_API_MODELS


# Load list of available language models from settings via local server API config
LOCAL_LANGUAGE_MODEL_CHOICES = [
    (model, model + ' (Local)') for model in LOCAL_LLM_API_MODELS
]

# List of available models for transcription
MODELS_TRANSCRIPTION = [
    ('faster-whisper-large-v3-turbo', 'Faster Whisper Large V3 Turbo (Local)'),
    ('gpt-4o-mini-transcribe', 'GPT-4o Mini Transcribe (API)'),
]

MODELS_SUMMARIZATION = LOCAL_LANGUAGE_MODEL_CHOICES + [
    ('gpt-4o-mini', 'gpt-4o-mini')
]

class TranscriptionLanguageModelChoiceForm(forms.Form):
    """Basic form for choosing language models."""
    transcriber_model = forms.ChoiceField(
        choices=MODELS_TRANSCRIPTION,
        initial='faster-whisper-large-v3-turbo',
        label='Transcribe with'
    )

class SummarizationLanguageModelChoiceForm(forms.Form):
    """Basic form for choosing language models."""
    summarizer_model = forms.ChoiceField(
        choices=MODELS_SUMMARIZATION,
        label='Summarize with'
    )

class TranscriptionAndSummarizationLanguageModelChoiceForm(
    TranscriptionLanguageModelChoiceForm,
    SummarizationLanguageModelChoiceForm
):
    """Basic form for choosing language models for both transcription and summarization."""
    field_order = ['transcriber_model', 'summarizer_model']

class BasicAudioFileForm(forms.Form):
    """Audio upload form for basic audio file input.
    Allows only MP3, WAV, and WEBM file extensions."""
    file = forms.FileField(
        validators=[FileExtensionValidator(allowed_extensions=['mp3', 'wav', 'webm'])],
        widget=forms.FileInput(attrs={'accept': 'audio/mp3, audio/wav, audio/webm'}),
    )

class TranscribeAndSummarizeAudioFileForm(
    TranscriptionLanguageModelChoiceForm,
    SummarizationLanguageModelChoiceForm,
    BasicAudioFileForm
):
    """Audio upload form for processing existing audio files with options fortranscription and
    summarization language models. Allows only MP3, WAV, and WEBM file extensions."""
    field_order = ['transcriber_model', 'summarizer_model', 'file']

class EditTranscriptForm(SummarizationLanguageModelChoiceForm):
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

class EditWithInstructionForm(SummarizationLanguageModelChoiceForm, TextInputForm):
    """Text input form with options for summarization language models."""
    field_order = ['summarizer_model', 'input']

class RichTextInputForm(forms.Form):
    """Basic rich text editor form."""
    text = forms.CharField(widget=CKEditorWidget())
