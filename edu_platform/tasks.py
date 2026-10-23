import logging

from celery import shared_task
from django.db import transaction

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=90)
def grade_challenge_submission(self, submission_id):
    from edu_platform.models import ChallengeSubmission
    from edu_platform.services.challenge_grader import grade_submission, save_grade

    try:
        with transaction.atomic():
            submission = ChallengeSubmission.objects.select_for_update().select_related("challenge", "challenge__subject").get(pk=submission_id)
            if submission.status in {ChallengeSubmission.Status.GRADED, ChallengeSubmission.Status.REVIEWED}:
                return {"status": "already_graded"}
            if submission.status == ChallengeSubmission.Status.PROCESSING:
                return {"status": "already_processing"}
            submission.status = ChallengeSubmission.Status.PROCESSING
            submission.error_message = ""
            submission.save(update_fields=["status", "error_message"])
        result = grade_submission(submission)
        save_grade(submission, result)
        return {"status": "graded", "score": result["score"]}
    except ChallengeSubmission.DoesNotExist:
        return {"status": "missing"}
    except Exception as exc:
        logger.exception("Edu challenge grading failed for submission %s", submission_id)
        try:
            submission = ChallengeSubmission.objects.get(pk=submission_id)
            submission.status = ChallengeSubmission.Status.FAILED
            submission.error_message = "La correction automatique a échoué. Un enseignant peut relancer ou vérifier la copie."
            submission.save(update_fields=["status", "error_message"])
        except Exception:
            pass
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        return {"status": "failed"}
