import tempfile
from pathlib import Path
from unittest.mock import patch
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.utils import timezone

from .models import OCRJob
from .services import OCRResult, OCRError
from .tasks import process_ocr_job, cleanup_ocr_jobs


class OCRJobTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.settings_override = override_settings(PHONE_OCR_UPLOAD_ROOT=Path(self.tmp.name))
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)

    def submit(self):
        return self.client.post('/phone-ocr/submit/', {'media': SimpleUploadedFile('test.mp4', b'video', content_type='video/mp4')}, HTTP_ACCEPT='application/json')

    @patch('phone_ocr_agent.job_views.process_ocr_job.apply_async')
    def test_async_result_and_session_isolation(self, enqueue):
        response = self.submit()
        self.assertEqual(response.status_code, 202)
        job = OCRJob.objects.get()
        self.assertEqual(job.status, 'queued')
        enqueue.assert_called_once()
        url = response.json()['status_url']
        self.assertEqual(Client().get(url).status_code, 404)
        with patch('phone_ocr_agent.tasks.extract_from_video', return_value=OCRResult('text', [], ['+237699123456'])):
            process_ocr_job(str(job.pk))
        job.refresh_from_db()
        self.assertEqual(job.numbers, ['+237699123456'])
        self.assertEqual(self.client.get(url).json()['status'], 'done')
        self.assertEqual(list(Path(self.tmp.name).iterdir()), [])
        with patch('phone_ocr_agent.tasks.extract_from_video') as extract:
            process_ocr_job(str(job.pk))
            extract.assert_not_called()

    @patch('phone_ocr_agent.job_views.process_ocr_job.apply_async')
    def test_total_limit_rejects_before_queue(self, enqueue):
        with patch('phone_ocr_agent.job_views.MAX_UPLOAD_BYTES', 4):
            self.assertEqual(self.submit().status_code, 413)
        enqueue.assert_not_called()
        self.assertFalse(OCRJob.objects.exists())

    @patch('phone_ocr_agent.job_views.process_ocr_job.apply_async', side_effect=RuntimeError('broker down'))
    def test_queue_failure_cleans_files(self, enqueue):
        self.assertEqual(self.submit().status_code, 503)
        self.assertEqual(OCRJob.objects.get().status, 'failed')
        self.assertEqual(list(Path(self.tmp.name).iterdir()), [])

    @patch('phone_ocr_agent.job_views.process_ocr_job.apply_async')
    def test_processing_failure_cleans_files(self, enqueue):
        self.submit()
        job = OCRJob.objects.get()
        with patch('phone_ocr_agent.tasks.extract_from_video', side_effect=OCRError('Vidéo illisible')):
            process_ocr_job(str(job.pk))
        job.refresh_from_db()
        self.assertEqual(job.status, 'failed')
        self.assertEqual(job.error, 'Vidéo illisible')
        self.assertEqual(list(Path(self.tmp.name).iterdir()), [])

    @patch('phone_ocr_agent.job_views.process_ocr_job.apply_async')
    def test_abandoned_job_expires(self, enqueue):
        self.submit()
        OCRJob.objects.update(updated_at=timezone.now() - timedelta(hours=3))
        cleanup_ocr_jobs()
        self.assertEqual(OCRJob.objects.get().status, 'failed')
        self.assertEqual(list(Path(self.tmp.name).iterdir()), [])
