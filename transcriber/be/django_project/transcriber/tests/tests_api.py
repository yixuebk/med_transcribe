"""Unit tests for Transcriber app API views."""
import os
import base64

from unittest.mock import patch, mock_open
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from transcriber.models import Transcription
from transcriber.views import MEDIA_AUDIO_DIR


class ApiTranscribeViewTest(TestCase):
    """Test class for the api_transcribe view."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.url = reverse('transcriber:api_transcribe')

        # Create a mock audio file for testing
        self.audio_content = b'test audio content'
        self.audio_file = SimpleUploadedFile(
            'test_audio.mp3',
            self.audio_content,
            content_type='audio/mpeg'
        )

    @patch('transcriber.views.handle_audio_file_upload')
    def test_api_transcribe_valid_request(self, mock_handle_upload):
        """Test api_transcribe with a valid POST request and file."""
        # Mock the handle_audio_file_upload function to set context
        def side_effect(request, form, context):
            # Create a test transcription and add it to the context
            transcription = Transcription.objects.create(
                filename='test_audio_123.mp3',
                transcript='This is a test transcript',
                formatted_text='Formatted test transcript'
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

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertIn('context', response.json())
        self.assertIn('transcription', response.json()['context'])

        # Verify the transcription data in the response
        transcription_data = response.json()['context']['transcription']
        self.assertEqual(transcription_data['filename'], 'test_audio_123.mp3')
        self.assertEqual(transcription_data['transcript'], 'This is a test transcript')
        self.assertEqual(transcription_data['formatted_text'], 'Formatted test transcript')

    def test_api_transcribe_no_file(self):
        """Test api_transcribe with a POST request but no file."""
        response = self.client.post(self.url, {'new_file': 'true'})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {'error': 'Invalid request'})

    def test_api_transcribe_invalid_form(self):
        """Test api_transcribe with an invalid form."""
        # Make a request with an invalid file type
        invalid_file = SimpleUploadedFile(
            'test_doc.txt',
            b'This is not an audio file',
            content_type='text/plain'
        )

        response = self.client.post(
            self.url,
            {
                'file': invalid_file,
                'new_file': 'true'
            }
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {'error': 'Invalid form data'})

    def test_api_transcribe_get_request(self):
        """Test api_transcribe with a GET request."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {'error': 'Invalid request'})

    def test_api_transcribe_filename_consistency(self):
        """Test that the filename used to save the audio file matches the filename
        in the Transcription object."""
        # Create a real test audio file
        audio_file = SimpleUploadedFile(
            'test_audio.mp3',
            b'test audio content',
            content_type='audio/mpeg'
        )

        # Use the actual handle_audio_file_upload function (no mocking)
        # to test the real file saving and database operations
        with patch(
            'transcriber.views.get_transcription_from_local_file',
            return_value='Test transcript'
        ):
            with patch(
                'transcriber.views.get_soap_format_from_transcription',
                return_value='Formatted test transcript'
            ):
                # Make the request with a file and new_file parameter
                response = self.client.post(
                    self.url,
                    {
                        'file': audio_file,
                        'new_file': 'true',
                        'timezone_offset': '0'
                    }
                )

                # Check response
                self.assertEqual(response.status_code, 200)

                # Get the transcription from the response
                transcription_data = response.json()['context']['transcription']
                filename = transcription_data['filename']

                # Verify that the file exists with exactly the same filename
                file_path = f'{MEDIA_AUDIO_DIR}{filename}'
                self.assertTrue(
                    os.path.exists(file_path),
                    f"File {file_path} does not exist"
                )

                # Verify that the Transcription object exists with this filename
                transcription = Transcription.objects.get(filename=filename)
                self.assertEqual(transcription.filename, filename)

                # Clean up the test file
                if os.path.exists(file_path):
                    os.remove(file_path)


class ApiAudioViewTest(TestCase):
    """Test class for the api_audio view."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

        # Create a test transcription
        self.transcription = Transcription.objects.create(
            filename='test_audio_file.mp3',
            transcript='This is a test transcript',
            formatted_text='Formatted test transcript'
        )

        # URL for the api_audio view with the transcription filename
        self.url = reverse('transcriber:api_audio', args=[self.transcription.filename])

        # Create a non-existent filename for testing
        self.nonexistent_url = reverse('transcriber:api_audio', args=['nonexistent_file.mp3'])

    @patch('os.path.exists')
    @patch('transcriber.views.open', new_callable=mock_open, read_data=b'test audio content')
    def test_api_audio_valid_request(self, mock_file, mock_exists):
        """Test api_audio with a valid request for an existing file."""
        # Mock os.path.exists to return True
        mock_exists.return_value = True

        # Make the request
        response = self.client.get(self.url)

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertIn('context', response.json())
        self.assertIn('audio_b64', response.json()['context'])

        # Verify the audio data in the response
        audio_b64 = response.json()['context']['audio_b64']
        self.assertEqual(
            audio_b64,
            base64.b64encode(b'test audio content').decode('utf-8')
        )

        # Verify the file was opened with the correct path
        mock_file.assert_called_once_with(
            f'{MEDIA_AUDIO_DIR}{self.transcription.filename}',
            'rb'
        )

    @patch('os.path.exists')
    def test_api_audio_file_not_found(self, mock_exists):
        """Test api_audio when the audio file doesn't exist."""
        # Mock os.path.exists to return False
        mock_exists.return_value = False

        # Make the request
        response = self.client.get(self.url)

        # Check response
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {'error': 'Audio file not found'})

    def test_api_audio_transcription_not_found(self):
        """Test api_audio when the transcription doesn't exist."""
        # Make the request with a non-existent filename
        response = self.client.get(self.nonexistent_url)

        # Check response
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {'error': 'Transcription not found'})
