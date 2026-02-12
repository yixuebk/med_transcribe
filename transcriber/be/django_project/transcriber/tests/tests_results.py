"""Unit tests for Transcriber app result and result_list views."""
import datetime

from unittest.mock import patch, mock_open
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from transcriber.models import Transcription
from transcriber.forms import EditTranscriptForm
from transcriber.views import MEDIA_AUDIO_DIR


# Create your tests here.

class ResultListViewTest(TestCase):
    """Test class for the result_list view."""

    def setUp(self):
        """Set up test data."""
        # Create client
        self.client = Client()

        # Create test transcriptions with different timestamps
        # audio_created_at has property auto_now_add=True, so we need to set it manually
        self.transcription1 = Transcription.objects.create(
            filename='test_file1.mp3',
            transcript='This is test transcript 1',
            formatted_text='Formatted text 1',
        )
        self.transcription1.audio_created_at = timezone.now() - datetime.timedelta(days=2)
        self.transcription1.save()

        self.transcription2 = Transcription.objects.create(
            filename='test_file2.mp3',
            transcript='This is test transcript 2',
            formatted_text='Formatted text 2',
        )
        self.transcription2.audio_created_at = timezone.now() - datetime.timedelta(days=1)
        self.transcription2.save()

        self.transcription3 = Transcription.objects.create(
            filename='test_file3.mp3',
            transcript='This is test transcript 3',
            formatted_text='Formatted text 3',
        )
        self.transcription3.audio_created_at = timezone.now()
        self.transcription3.save()

        # URL for the result_list view
        self.url = reverse('transcriber:result_list')

    def test_result_list_view_status_code(self):
        """Test that the view returns a 200 status code."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_result_list_view_template(self):
        """Test that the view uses the correct template."""
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'transcriber/result_list.html')

    def test_result_list_view_context(self):
        """Test that the view provides the correct context."""
        response = self.client.get(self.url)

        # Check that total count is correct
        self.assertEqual(response.context['total'], 3)

        # Check that page_obj is provided
        self.assertIn('page_obj', response.context)

        # Check that the page_obj contains the transcriptions
        self.assertEqual(len(response.context['page_obj']), 3)

    def test_result_list_view_ordering(self):
        """Test that transcriptions are ordered by audio_created_at in descending order."""
        response = self.client.get(self.url)

        # Get the transcriptions from the page_obj
        transcriptions = list(response.context['page_obj'])

        # Check that they are in the correct order (newest first)
        self.assertEqual(transcriptions[0], self.transcription3)
        self.assertEqual(transcriptions[1], self.transcription2)
        self.assertEqual(transcriptions[2], self.transcription1)

    def test_result_list_view_pagination(self):
        """Test pagination of the result_list view."""
        # Create more transcriptions to test pagination
        for i in range(4, 34):
            Transcription.objects.create(
                filename=f'test_file{i}.mp3',
                transcript=f'This is test transcript {i}',
                formatted_text=f'Formatted text {i}',
                audio_created_at=timezone.now() - datetime.timedelta(minutes=i)
            )

        # Test first page
        response = self.client.get(self.url)
        self.assertEqual(len(response.context['page_obj']), 30)
        self.assertTrue(response.context['page_obj'].has_next())
        self.assertFalse(response.context['page_obj'].has_previous())

        # Test second page
        response = self.client.get(f'{self.url}?page=2')
        self.assertEqual(len(response.context['page_obj']), 3)
        self.assertFalse(response.context['page_obj'].has_next())
        self.assertTrue(response.context['page_obj'].has_previous())

    def test_result_list_view_invalid_page(self):
        """Test that the view handles invalid page numbers gracefully."""
        # Test with a non-integer page number
        response = self.client.get(f'{self.url}?page=abc')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].number, 1)

        # Test with a page number that is too high
        response = self.client.get(f'{self.url}?page=999')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].number, 1)


class ResultViewTest(TestCase):
    """Test class for the result view."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

        # Create a test transcription
        self.transcription = Transcription.objects.create(
            filename='test_audio_123.mp3',
            transcript='This is a test transcript',
            formatted_text='Formatted test transcript',
            edited_transcript=None
        )

        # Create a test transcription with edited transcript
        self.edited_transcription = Transcription.objects.create(
            filename='edited_audio_123.mp3',
            transcript='This is the original transcript',
            edited_transcript='This is the edited transcript',
            formatted_text='Formatted edited transcript',
        )

        # URLs for the result view
        self.url = reverse('transcriber:result', args=[self.transcription.filename])
        self.edited_url = reverse('transcriber:result', args=[self.edited_transcription.filename])
        self.nonexistent_url = reverse('transcriber:result', args=['nonexistent_file.mp3'])

    @patch('transcriber.views.open', new_callable=mock_open, read_data=b'test audio content')
    def test_result_view_get_original(self, mock_file):
        """Test result view GET request for a transcription without edited transcript."""
        response = self.client.get(self.url)

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'transcriber/result.html')

        # Check context
        self.assertEqual(response.context['query_id'], self.transcription.filename)
        self.assertEqual(response.context['transcription'], self.transcription)
        self.assertIsNotNone(response.context['edit_original_transcript_form'])
        self.assertIsNone(response.context['edit_modified_transcript_form'])

        # Check form initial values
        form = response.context['edit_original_transcript_form']
        self.assertEqual(form.initial['filename'], self.transcription.filename)
        self.assertEqual(form.initial['transcript'], self.transcription.transcript)

        # Verify the file was opened with the correct path
        mock_file.assert_called_with(
            f'{MEDIA_AUDIO_DIR}{self.transcription.filename}',
            'rb'
        )

    @patch('transcriber.views.open', new_callable=mock_open, read_data=b'test audio content')
    def test_result_view_get_edited(self, mock_file):
        """Test result view GET request for a transcription with edited transcript."""
        response = self.client.get(self.edited_url)

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'transcriber/result.html')

        # Check context
        self.assertEqual(response.context['query_id'], self.edited_transcription.filename)
        self.assertEqual(response.context['transcription'], self.edited_transcription)
        self.assertIsNone(response.context['edit_original_transcript_form'])
        self.assertIsNotNone(response.context['edit_modified_transcript_form'])

        # Check form initial values
        form = response.context['edit_modified_transcript_form']
        self.assertEqual(form.initial['filename'], self.edited_transcription.filename)
        self.assertEqual(form.initial['transcript'], self.edited_transcription.edited_transcript)

        # Verify the file was opened with the correct path
        mock_file.assert_called_with(
            f'{MEDIA_AUDIO_DIR}{self.edited_transcription.filename}',
            'rb'
        )

    def test_result_view_nonexistent(self):
        """Test result view with a nonexistent transcription."""
        response = self.client.get(self.nonexistent_url)

        # Check response
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content.decode(), 'Transcription not found for this filename.')

    @patch('transcriber.views.open', new_callable=mock_open, read_data=b'test audio content')
    @patch('transcriber.views.handle_reformat_original_transcript')
    def test_result_view_post_reformat_original(self, mock_handle_reformat, mock_file):
        """Test result view POST request for reformatting original transcript."""
        # Create form data
        form_data = {
            'reformat': 'true',
            'filename': self.transcription.filename,
            'transcript': 'Modified original transcript'
        }

        # Define side effect for the mock
        def side_effect(form, context):
            # Update the transcription in the context
            transcription = Transcription.objects.get(filename=form.cleaned_data['filename'])
            transcription.edited_transcript = form.cleaned_data['transcript']
            transcription.formatted_text = 'New formatted text'
            transcription.save()
            context['transcription'] = transcription
            context['edit_modified_transcript_form'] = EditTranscriptForm(
                initial={
                    'filename': transcription.filename,
                    'transcript': transcription.edited_transcript,
                }
            )

        mock_handle_reformat.side_effect = side_effect

        # Make the request
        response = self.client.post(self.url, form_data)

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'transcriber/result.html')

        # Verify the mock was called with the correct arguments
        mock_handle_reformat.assert_called()
        self.assertEqual(
            mock_handle_reformat.call_args[0][0].cleaned_data['transcript'],
            'Modified original transcript'
        )

        # Verify the file was opened with the correct path
        mock_file.assert_called_with(
            f'{MEDIA_AUDIO_DIR}{self.transcription.filename}',
            'rb'
        )

    @patch('transcriber.views.open', new_callable=mock_open, read_data=b'test audio content')
    @patch('transcriber.views.handle_reformat_edited_transcript')
    def test_result_view_post_reformat_edited(self, mock_handle_reformat, mock_file):
        """Test result view POST request for reformatting edited transcript."""
        # Create form data
        form_data = {
            'reformat_edited': 'true',
            'filename': self.edited_transcription.filename,
            'transcript': 'Further modified edited transcript'
        }

        # Define side effect for the mock
        def side_effect(form, context):
            # Update the transcription in the context
            transcription = Transcription.objects.get(filename=form.cleaned_data['filename'])
            transcription.edited_transcript = form.cleaned_data['transcript']
            transcription.formatted_text = 'New formatted text for edited'
            transcription.save()
            context['transcription'] = transcription
            context['edit_modified_transcript_form'] = EditTranscriptForm(
                initial={
                    'filename': transcription.filename,
                    'transcript': transcription.edited_transcript,
                }
            )

        mock_handle_reformat.side_effect = side_effect

        # Make the request
        response = self.client.post(self.edited_url, form_data)

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'transcriber/result.html')

        # Verify the mock was called with the correct arguments
        mock_handle_reformat.assert_called()
        self.assertEqual(
            mock_handle_reformat.call_args[0][0].cleaned_data['transcript'],
            'Further modified edited transcript'
        )

        # Verify the file was opened with the correct path
        mock_file.assert_called_with(
            f'{MEDIA_AUDIO_DIR}{self.edited_transcription.filename}',
            'rb'
        )

    @patch('transcriber.views.open', new_callable=mock_open, read_data=b'test audio content')
    def test_result_view_post_invalid_reformat_form(self, mock_file):
        """Test result view POST request with invalid reformat form."""
        # Create invalid form data (missing transcript)
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

    @patch('transcriber.views.open', new_callable=mock_open, read_data=b'test audio content')
    def test_result_view_post_invalid_reformat_edited_form(self, mock_file):
        """Test result view POST request with invalid reformat_edited form."""
        # Create invalid form data (missing transcript)
        form_data = {
            'reformat_edited': 'true',
            'filename': self.edited_transcription.filename,
            # Missing 'transcript' field
        }

        # Make the request
        response = self.client.post(self.edited_url, form_data)

        # Check response
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content.decode(), 'Invalid edit reformat form')
