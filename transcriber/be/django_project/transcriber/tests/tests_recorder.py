"""Unit tests for Transcriber app recorder view."""
from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from transcriber.models import Transcription
from transcriber.forms import BasicAudioFileUploadForm, EditTranscriptForm


class RecorderViewTest(TestCase):
    """Test class for the recorder view."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.url = reverse('transcriber:recorder')

        # Create a mock audio file for testing
        self.audio_file = SimpleUploadedFile(
            'test_audio.mp3',
            b'test audio content',
            content_type='audio/mpeg'
        )

        # Create a test transcription for reformat tests
        self.transcription = Transcription.objects.create(
            filename='existing_audio.mp3',
            transcript='Original transcript text',
            formatted_text='Original formatted text',
            edited_transcript=None
        )

    def test_recorder_view_get(self):
        """Test recorder view GET request returns correct template and context."""
        response = self.client.get(self.url)

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'transcriber/recorder.html')

        # Check context
        self.assertIsInstance(response.context['form'], BasicAudioFileUploadForm)
        self.assertIsNone(response.context['transcription'])
        self.assertIsNone(response.context['edit_original_transcript_form'])
        self.assertIsNone(response.context['edit_modified_transcript_form'])
        self.assertIsInstance(response.context['empty_edit_form'], EditTranscriptForm)

    @patch('transcriber.views.handle_audio_file_upload')
    def test_recorder_view_post_file_upload_valid(self, mock_handle_upload):
        """Test recorder view POST request with valid file upload."""
        # Mock the handle_audio_file_upload function
        def side_effect(request, form, context):
            transcription = Transcription.objects.create(
                filename='uploaded_audio_123.mp3',
                transcript='Uploaded transcript',
                formatted_text='Uploaded formatted text'
            )
            context['transcription'] = transcription

        mock_handle_upload.side_effect = side_effect

        # Make the request with a file
        response = self.client.post(
            self.url,
            {
                'file': self.audio_file,
                'existing_file': 'true',
                'timezone_offset': '0'
            }
        )

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'transcriber/recorder.html')

        # Verify the mock was called
        mock_handle_upload.assert_called_once()

    @patch('transcriber.views.handle_audio_file_upload')
    def test_recorder_view_post_file_upload_with_redirect(self, mock_handle_upload):
        """Test recorder view POST request with file upload and
        new_file parameter (should redirect)."""
        # Mock the handle_audio_file_upload function
        def side_effect(request, form, context):
            transcription = Transcription.objects.create(
                filename='new_audio_123.mp3',
                transcript='New transcript',
                formatted_text='New formatted text'
            )
            context['transcription'] = transcription

        mock_handle_upload.side_effect = side_effect

        # Make the request with a file and new_file parameter
        response = self.client.post(
            self.url,
            {
                'file': self.audio_file,
                'new_file': 'true',
                'timezone_offset': '0'
            }
        )

        # Check response is a redirect
        self.assertEqual(response.status_code, 302)
        self.assertIn('transcriber/result/', response.url)
        self.assertIn('new_audio_123.mp3', response.url)

        # Verify the mock was called
        mock_handle_upload.assert_called_once()

    def test_recorder_view_post_file_upload_invalid_form(self):
        """Test recorder view POST request with invalid file upload form."""
        # Create an invalid file (wrong content type)
        invalid_file = SimpleUploadedFile(
            'test_doc.txt',
            b'This is not an audio file',
            content_type='text/plain'
        )

        response = self.client.post(
            self.url,
            {
                'file': invalid_file,
                'existing_file': 'true'
            }
        )

        # Check response
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content.decode(), 'Invalid file upload form')

    @patch('transcriber.views.handle_reformat_original_transcript')
    def test_recorder_view_post_reformat_original(self, mock_handle_reformat):
        """Test recorder view POST request for reformatting original transcript."""
        # Mock the handle_reformat_original_transcript function
        def side_effect(form, context):
            transcription = Transcription.objects.get(filename=form.cleaned_data['filename'])
            transcription.edited_transcript = form.cleaned_data['transcript']
            transcription.save()
            context['transcription'] = transcription

        mock_handle_reformat.side_effect = side_effect

        # Create form data
        form_data = {
            'reformat': 'true',
            'filename': self.transcription.filename,
            'transcript': 'Modified original transcript'
        }

        # Make the request
        response = self.client.post(self.url, form_data)

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'transcriber/recorder.html')

        # Verify the mock was called
        mock_handle_reformat.assert_called_once()

    @patch('transcriber.views.handle_reformat_edited_transcript')
    def test_recorder_view_post_reformat_edited(self, mock_handle_reformat):
        """Test recorder view POST request for reformatting edited transcript."""
        # Update transcription to have an edited transcript
        self.transcription.edited_transcript = 'Edited transcript text'
        self.transcription.save()

        # Mock the handle_reformat_edited_transcript function
        def side_effect(form, context):
            transcription = Transcription.objects.get(filename=form.cleaned_data['filename'])
            transcription.edited_transcript = form.cleaned_data['transcript']
            transcription.save()
            context['transcription'] = transcription

        mock_handle_reformat.side_effect = side_effect

        # Create form data
        form_data = {
            'reformat_edited': 'true',
            'filename': self.transcription.filename,
            'transcript': 'Further modified edited transcript'
        }

        # Make the request
        response = self.client.post(self.url, form_data)

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'transcriber/recorder.html')

        # Verify the mock was called
        mock_handle_reformat.assert_called_once()

    def test_recorder_view_post_reformat_invalid_form(self):
        """Test recorder view POST request with invalid reformat form."""
        # Create invalid form data (missing transcript field)
        form_data = {
            'reformat': 'true',
            'filename': self.transcription.filename,
            # Missing 'transcript' field
        }

        # Make the request
        response = self.client.post(self.url, form_data)

        # Check response
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content.decode(), 'Invalid reformat form')

    def test_recorder_view_post_reformat_edited_invalid_form(self):
        """Test recorder view POST request with invalid reformat_edited form."""
        # Create invalid form data (missing transcript field)
        form_data = {
            'reformat_edited': 'true',
            'filename': self.transcription.filename,
            # Missing 'transcript' field
        }

        # Make the request
        response = self.client.post(self.url, form_data)

        # Check response
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content.decode(), 'Invalid edit reformat form')

    def test_recorder_view_post_no_action(self):
        """Test recorder view POST request with no specific action (should render template)."""
        # Make a POST request without any specific action parameters
        response = self.client.post(self.url, {})

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'transcriber/recorder.html')

        # Check context is properly initialized
        self.assertIsInstance(response.context['form'], BasicAudioFileUploadForm)
        self.assertIsNone(response.context['transcription'])
        self.assertIsNone(response.context['edit_original_transcript_form'])
        self.assertIsNone(response.context['edit_modified_transcript_form'])
        self.assertIsInstance(response.context['empty_edit_form'], EditTranscriptForm)
