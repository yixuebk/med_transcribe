"""Transcriber App Views"""
import logging
import uuid
import datetime
import os
import base64

# Django
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.forms import model_to_dict
from django.utils import timezone
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

# Local
from .models import Transcription

from .forms import (
    BasicAudioFileUploadForm,
    EditTranscriptForm,
    TextInputForm,
    RichTextInputForm,
)
from .gpt_transcription import (
    get_transcription_from_local_file,
    get_soap_format_from_transcription,
    update_soap_format_with_intruction,
)

# Get logger
logger = logging.getLogger(__name__)

MEDIA_AUDIO_DIR = 'transcriber/media/audio/'

# Create your views here.

def recorder(request):
    """Recorder view containing audio recording, downloading, and transcribing features."""
    context = {
        'form': BasicAudioFileUploadForm(),
        'transcription': None,
        'edit_original_transcript_form': None,
        'edit_modified_transcript_form': None,
        # Empty form, only used for JS fetch POST request
        'empty_edit_form': EditTranscriptForm(),
        # Forms for editing reformatted text
        'edit_soap_form': RichTextInputForm(),
        'edit_chat_form': TextInputForm(),
    }

    if request.method == 'POST':
        # If file is uploaded (audio file)
        if request.FILES:
            # Load form data
            form = BasicAudioFileUploadForm(request.POST, request.FILES)

            # Check if form is valid
            if form.is_valid():
                logger.info('Handling audio file upload.')
                handle_audio_file_upload(request, form, context)

                # Redirect to result page if 'new_file' in request.POST
                # Current workaround to handle JS fetch POST request for 1-click transcription
                if 'new_file' in request.POST:
                    return redirect(
                        'transcriber:result', query_id=context['transcription'].filename
                    )
            else:
                return HttpResponse(status=404, content='Invalid file upload form')
        else:
            # If form for original transcript to generate new formatted text
            if 'reformat' in request.POST:
                # Load form data
                form = EditTranscriptForm(request.POST)

                # Check if form is valid
                if form.is_valid():
                    logger.info('Handling reformatting of original transcript.')
                    handle_reformat_original_transcript(form, context)
                else:
                    return HttpResponse(status=404, content='Invalid reformat form')
            # If form for edited transcript to generate new formatted text
            elif 'reformat_edited' in request.POST:
                # Load form data
                form = EditTranscriptForm(request.POST)

                # Check if form is valid
                if form.is_valid():
                    logger.info('Handling reformatting of edited transcript.')
                    handle_reformat_edited_transcript(form, context)
                else:
                    return HttpResponse(status=404, content='Invalid edit reformat form')

        # Prefill SOAP note edit form if applicable
        context['edit_soap_form'].initial = (
            {'text': context['transcription'].formatted_text} if context['transcription'] else {}
        )

    return render(request, 'transcriber/recorder.html', context)

def result(request, query_id):
    """Result view"""
    context = {
        'query_id': query_id,
        'edit_original_transcript_form': None,
        'edit_modified_transcript_form': None,
        # Forms for editing reformatted text
        'edit_soap_form': RichTextInputForm(),
        'edit_chat_form': TextInputForm(),
    }

    try:
        transcription = Transcription.objects.get(filename=query_id)

        # Add Transcription instance to context
        context['transcription'] = transcription

        # Load audio file into memory and add to context
        with open(f'{MEDIA_AUDIO_DIR}{transcription.filename}', 'rb') as audio_file:
            context['audio_file'] = audio_file.read()

    except Transcription.DoesNotExist:
        return HttpResponse(status=404, content='Transcription not found for this filename.')

    if request.method == 'POST':
        # If form for original transcript to generate new formatted text
        if 'reformat' in request.POST:
            # Load form data
            form = EditTranscriptForm(request.POST)

            # Check if form is valid
            if form.is_valid():
                logger.info('Handling reformatting of original transcript.')
                handle_reformat_original_transcript(form, context)
            else:
                return HttpResponse(status=404, content='Invalid reformat form')
        # If form for edited transcript to generate new formatted text
        elif 'reformat_edited' in request.POST:
            # Load form data
            form = EditTranscriptForm(request.POST)

            # Check if form is valid
            if form.is_valid():
                logger.info('Handling reformatting of edited transcript.')
                handle_reformat_edited_transcript(form, context)
            else:
                return HttpResponse(status=404, content='Invalid edit reformat form')

        # Set variable to updated transcription instance (otherwise it will provide previous values)
        # context['transcription'] points to updated instance, but transcription does not
        transcription = context['transcription']

    # Prefill transcript edit form
    if transcription.edited_transcript:
        context['edit_modified_transcript_form'] = EditTranscriptForm(
            initial={
                'filename': transcription.filename,
                'transcript': transcription.edited_transcript,
            }
        )
    else:
        context['edit_original_transcript_form'] = EditTranscriptForm(
            initial={
                'filename': transcription.filename,
                'transcript': transcription.transcript,
            }
        )

    # Prefill SOAP note edit form
    context['edit_soap_form'].initial = (
        {'text': transcription.formatted_text}
    )

    return render(request, 'transcriber/result.html', context)


def result_list(request):
    """Result list view"""

    transcriptions = Transcription.objects.all().order_by('-audio_created_at')
    context = {
        'total': transcriptions.count(),
        'page_obj': pagination(request, transcriptions, 30),
    }

    return render(request, 'transcriber/result_list.html', context)

def delete_result(request, query_id):
    """Delete transcription result."""
    try:
        transcription = Transcription.objects.get(filename=query_id)
        transcription.delete()
    except Transcription.DoesNotExist:
        return HttpResponse(status=404, content='Transcription not found for this filename.')

    return redirect('transcriber:result_list')

def delete_result_multi(request):
    """Delete multiple transcription results."""
    if request.method == 'POST':
        print(request.POST)
        # Get selected transcription IDs from request
        list_query_id = request.POST.getlist('id')

        list_except = []

        if not list_query_id:
            return HttpResponse(status=404, content='No transcriptions selected for deletion.')

        for query_id in list_query_id:
            try:
                transcription = Transcription.objects.get(filename=query_id)
                # Delete audio file from media directory if it exists
                if os.path.exists(f'{MEDIA_AUDIO_DIR}{transcription.filename}'):
                    os.remove(f'{MEDIA_AUDIO_DIR}{transcription.filename}')

                # Delete Transcription instance from database
                transcription.delete()
            except Transcription.DoesNotExist:
                list_except.append(query_id)
                logger.warning(
                    'Failed to find Transcription instance for the following filenames: %s',
                    list_except
                )
        # Redirect back to result list view
        return redirect('transcriber:result_list')
    return HttpResponse(status=404, content='Invalid request method.')


# JsonResponse API ---------------------------------------------------------------------------------

def api_transcribe(request):
    """Transcribe audio file using OpenAI API"""
    context = {}

    # Check if request is POST
    if request.method == 'POST' and request.FILES:
        # Load form data
        form = BasicAudioFileUploadForm(request.POST, request.FILES)

        # Check if form is valid
        if form.is_valid():
            logger.info('Handling audio file upload.')
            handle_audio_file_upload(request, form, context)

            trimmed_context = {
                'transcription': model_to_dict(context['transcription']),
            }

            # Redirect to result page if 'new_file' in request.POST
            # Current workaround to handle JS fetch POST request for 1-click transcription
            if 'new_file' in request.POST:
                return JsonResponse(status=200, data={'context': trimmed_context})
        else:
            return JsonResponse(status=404, data={'error': 'Invalid form data'})
    return JsonResponse(status=404, data={'error': 'Invalid request'})

def api_audio(request, query_id):
    """Get audio file"""
    context = {
        'audio_file':  None
    }

    try:
        # Get Transcription instance
        transcription = Transcription.objects.get(filename=query_id)

        # Check if audio file exists
        if os.path.exists(f'{MEDIA_AUDIO_DIR}{transcription.filename}'):
            # Get audio file data and make it JSON-serializable as hex string
            with open(f'{MEDIA_AUDIO_DIR}{transcription.filename}', 'rb') as audio_file:
                audio_bytes = audio_file.read()
                # Encode the audio content to base64
                audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

                # Add to context
                context['audio_b64'] = audio_base64

                return JsonResponse(status=200, data={'context': context})
        else:
            return JsonResponse(status=404, data={'error': 'Audio file not found'})
    except Transcription.DoesNotExist:
        return JsonResponse(status=404, data={'error': 'Transcription not found'})

def api_update_soap(request):
    """Update SOAP formatted text for a Transcription instance."""
    context = {}

    try:
        # Get Transcription instance
        transcription = Transcription.objects.get(filename=request.POST['filename'])
    except Transcription.DoesNotExist:
        return JsonResponse(status=404, data={'error': 'Transcription not found'})

    # Check if request is POST
    if request.method == 'POST':
        # Handle form - direct edit
        if 'edit_soap' in request.POST:
            # Load form data
            form = RichTextInputForm(request.POST)

            # Check if form is valid
            if form.is_valid():
                logger.info('Handling SOAP note direct edit.')

                # Update SOAP formatted text
                transcription.formatted_text = form.cleaned_data['text']
                transcription.save()
            else:
                return HttpResponse(status=404, content='Invalid SOAP note edit form')
        # Handle form - edit with language model 'chat'
        elif 'edit_chat' in request.POST:
            form = TextInputForm(request.POST)

            # Check if form is valid
            if form.is_valid():
                logger.info('Handling SOAP note edit with LLM instruction.')

                # Update SOAP note with LLM instruction
                transcription.formatted_text = update_soap_format_with_intruction(
                    transcription, form.cleaned_data['input']
                )
                transcription.save()
            else:
                return HttpResponse(status=404, content='Invalid SOAP note edit form')

        # Add transcription to context (make it JSON-serializable)
        context['transcription'] = model_to_dict(transcription)

        # Return JSON response with updated SOAP note
        return JsonResponse(status=200, data={'context': context})

    # Handle other request methods
    return JsonResponse(status=404, data={'error': 'Invalid request'})


def api_basic_transcribe(request):
    """Transcribe audio file using OpenAI API."""
    context = {}

    # Check if request is POST
    if request.method == 'POST' and request.FILES:
        # Load form data
        form = BasicAudioFileUploadForm(request.POST, request.FILES)
        # Check if form is valid
        if form.is_valid():
            # Save edit instruction voice audio file
            file_name = '_edit_instruction_voice.mp3'
            with open(f'{MEDIA_AUDIO_DIR}{file_name}', 'wb+') as destination:
                for chunk in form.cleaned_data['file'].chunks():
                    destination.write(chunk)

            logger.info('Transcribe audio file using OpenAI API.')
            transcript = get_transcription_from_local_file(f'{MEDIA_AUDIO_DIR}{file_name}')

            context['transcript'] = transcript
            return JsonResponse(status=200, data={'context': context})
        return JsonResponse(status=404, data={'error': 'Invalid form data'})
    return JsonResponse(status=404, data={'error': 'Invalid request'})


# Component functions ------------------------------------------------------------------------------

def handle_existing_file_transcription(request_file, tz):
    """Handle existing file transcription."""
    # Set file name
    str_split = request_file.name.split('.')

    # filename = <original filename>_<uuid>.<extension>
    file_name = ''.join([
        ''.join(str_split[0:-1]),
        '_',
        str(uuid.uuid4()),
        '.',
        # Assume file extension is last element in list split by '.'
        str_split[-1]
    ])

    # Save the file with name if it doesn't exist in media directory
    if not os.path.isfile(f'{MEDIA_AUDIO_DIR}{file_name}'):
        logger.info('Saving file "%s" to media directory.', file_name)
        with open(f'{MEDIA_AUDIO_DIR}{file_name}', 'wb+') as destination:
            for chunk in request_file.chunks():
                destination.write(chunk)

    # Get transcript
    transcript_result = get_transcription_from_local_file(
        f'{MEDIA_AUDIO_DIR}{file_name}'
    )
    # Get SOAP format
    soap_format_result = get_soap_format_from_transcription(transcript_result)

    # Check there is a datetime substring (14 digits, YYYYMMDDHHMMSS)
    possible_datetime_string = file_name.split('_', maxsplit=1)[0]
    if possible_datetime_string.isnumeric() and len(possible_datetime_string) == 14:
        # Convert to datetime object and add local timezone info to be timezone-aware, not naive
        datetime_created = datetime.datetime.strptime(
            possible_datetime_string, '%Y%m%d%H%M%S'
        ).replace(tzinfo=tz)

        transcription = Transcription(
            filename=file_name,
            transcript=transcript_result,
            formatted_text=soap_format_result,
            audio_created_at=datetime_created,
        )
    else:
        transcription = Transcription(
            filename=file_name,
            transcript=transcript_result,
            formatted_text=soap_format_result,
            audio_created_at=timezone.now(),
        )

    # Save the object to database
    transcription.save()
    logger.info('Transcription for file "%s" saved to database.', file_name)

    return transcription

def handle_new_file_transcription(request_file):
    """Handle new file transcription."""
    # Get timestamp
    timestamp_str = timezone.now().strftime('%Y%m%d%H%M%S')

    # Save with new datetime + UUID file name otherwise
    file_name = f'{timestamp_str}_{str(uuid.uuid4())}.mp3'
    with open(f'{MEDIA_AUDIO_DIR}{file_name}', 'wb+') as destination:
        for chunk in request_file.chunks():
            destination.write(chunk)

    # Get transcript
    transcript_result = get_transcription_from_local_file(
        f'{MEDIA_AUDIO_DIR}{file_name}'
    )
    # Get SOAP format
    soap_format_result = get_soap_format_from_transcription(transcript_result)

    # Save the object to database
    transcription = Transcription(
        filename=file_name,
        transcript=transcript_result,
        formatted_text=soap_format_result,
        audio_created_at=timezone.now(),
    )
    transcription.save()
    logger.info('Transcription for file "%s" saved to database.', file_name)

    return transcription

def handle_audio_file_upload(request_obj, form_obj, context_dict):
    """Handle valid audio file upload."""
    # Get file from form cleaned data
    request_file = form_obj.cleaned_data['file']

    transcription = None

    # Get timezone offset from POST data
    offset_minutes = request_obj.POST.get('timezone_offset')
    tz = datetime.timezone(
        offset=datetime.timedelta(minutes=int(offset_minutes))
    )

    # For file upload skipping the recording step
    if 'existing_file' in request_obj.POST:
        transcription = handle_existing_file_transcription(request_file, tz)
    elif 'new_file' in request_obj.POST:
        # Save Transcription object
        transcription = handle_new_file_transcription(request_file)

    # Add to existing page context to display in the same page
    context_dict['transcription'] = transcription

    # Transcript edit form depends on whether the transcription has been edited
    # If there is an edited transcript, don't show the original transcript
    if transcription.edited_transcript:
        context_dict['edit_modified_transcript_form'] = EditTranscriptForm(
            initial={
                'filename': transcription.filename,
                'transcript': transcription.edited_transcript,
            }
        )
    else:
        context_dict['edit_original_transcript_form'] = EditTranscriptForm(
            initial={
                'filename': transcription.filename,
                'transcript': transcription.transcript,
            }
        )

def handle_reformat_original_transcript(form_obj, context_dict):
    """Handle reformat original transcript."""
    # Get transcription object
    transcription = Transcription.objects.get(
        filename=form_obj.cleaned_data['filename']
    )

    # Save edited transcript if different from original
    if form_obj.cleaned_data['transcript'] != transcription.transcript:
        transcription.edited_transcript = form_obj.cleaned_data['transcript']

        # Pass edit form to context (to display in the same page in the same way)
        context_dict['edit_modified_transcript_form'] = EditTranscriptForm(
            initial={
                'filename': transcription.filename,
                'transcript': transcription.edited_transcript,
            }
        )

        # Get new soap format
        soap_format_result = get_soap_format_from_transcription(transcription.edited_transcript)
    else:
        # If no changes, show original transcript
        context_dict['edit_original_transcript_form'] = EditTranscriptForm(
            initial={
                'filename': transcription.filename,
                'transcript': transcription.transcript,
            }
        )

        # Get new soap format
        soap_format_result = get_soap_format_from_transcription(transcription.transcript)
    transcription.formatted_text = soap_format_result

    # Save changes
    transcription.save()
    logger.info('Reformatted text for file "%s" saved to database.', transcription.filename)

    # Pass transcription to context
    context_dict['transcription'] = transcription

def handle_reformat_edited_transcript(form_obj, context_dict):
    """Handle reformat edited transcript."""
    # Get transcription object
    transcription = Transcription.objects.get(
        filename=form_obj.cleaned_data['filename']
    )

    # Save edited transcript if different from original
    if form_obj.cleaned_data['transcript'] != transcription.edited_transcript:
        transcription.edited_transcript = form_obj.cleaned_data['transcript']
        logger.info('Edited transcript for file "%s".', transcription.filename)

    # Pass edit form to context using transcription.edited_transcript regardless of changes
    context_dict['edit_modified_transcript_form'] = EditTranscriptForm(
        initial={
            'filename': transcription.filename,
            'transcript': transcription.edited_transcript,
        }
    )

    # Get new soap format
    soap_format_result = get_soap_format_from_transcription(transcription.edited_transcript)
    transcription.formatted_text = soap_format_result

    # Save changes
    transcription.save()
    logger.info('Reformatted text for file "%s" saved to database.', transcription.filename)

    # Pass transcription to context
    context_dict['transcription'] = transcription


# General-use functions ----------------------------------------------------------------------------

def pagination(request_obj, list_obj, items_per_page):
    """Function for basic pagination, returning a page object."""
    # Pagination
    page_num = request_obj.GET.get('page', 1)
    paginator = Paginator(list_obj, items_per_page)

    try:
        page_obj = paginator.page(page_num)
    except PageNotAnInteger:
        # if page is not an integer, deliver the first page
        page_obj = paginator.page(1)
    except EmptyPage:
        # if the page is out of range, deliver the last page
        page_obj = paginator.page(paginator.num_pages)

    return page_obj
