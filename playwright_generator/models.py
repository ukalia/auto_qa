from django.db import models
from auto_qa import settings
from utils.base import BaseModel
from utils.logger import Logger
from utils.s3_utils import S3Client


class GeneratedScript(BaseModel):
    '''
    Represents a test script that has been generated for a specific test case.
    This model stores metadata and status information about the generated script,
    including where it is stored, its current
    validation state, and integrity/versioning details.

    Attributes:
        GENERATED (str): Status indicating the script has been generated but not yet validated.
        VALIDATED (str): Status indicating the script has been validated and approved.
        MANUAL_REVIEW (str): Status indicating the script requires manual review.
        
        test_case (OneToOneField[TestCase]): The test case for which this script was generated.
        name (str): The name of the script.
        script_storage_key (str): Storage key or path (e.g., S3 key) where the script file is stored.
        etag (str, optional): The ETag returned by the storage service, useful for change detection.
        version (int): Internal version number for tracking script updates (default = 1).
        status (str): Current validation state of the script. One of `GENERATED`, `VALIDATED`, or `MANUAL_REVIEW`.
    '''

    GENERATED = 'generated'
    VALIDATED = 'validated'
    MANUAL_REVIEW = 'manual_review'
    status_choices = [
        (GENERATED, 'Generated'),
        (VALIDATED, 'Validated'),
        (MANUAL_REVIEW, 'Manual Review')
    ]

    test_case = models.OneToOneField("test_case.TestCase", on_delete=models.CASCADE, related_name='generated_script')
    name = models.CharField(max_length=200)
    script_storage_key = models.TextField()
    etag = models.CharField(max_length=100, null=True, blank=True)
    version = models.IntegerField(default=1)
    status = models.CharField(max_length=50, choices=status_choices)
 

class SctiptExecutionResult(BaseModel):
    '''
    Represents the execution result of a generated test script.
    This model records the outcome of running a given script, along with
    supporting artifacts such as execution logs and screenshots.

    Attributes:
        PENDING (str): Result indicating the script has not yet been executed.
        PASSED (str): Result indicating the script executed successfully.
        FAILED (str): Result indicating the script ran but did not pass.
        EXECUTION_ERROR (str): Result indicating an error occurred during execution.

        script (OneToOneField[GeneratedScript]): The generated script associated with this execution result.
        result (str): Current execution outcome. One of `PENDING`, `PASSED`, `FAILED`, or `EXECUTION_ERROR`.
        execution_time (float): Total time taken to execute the script, in seconds.
        log_storage_key (str): Storage key or path to the execution logs (e.g., S3 key).
        screenshots_storage_key (str): Storage key or path to screenshots captured during execution.
    '''

    PENDING = 'pending'
    PASSED = 'passed'
    FAILED = 'failed'
    EXECUTION_ERROR = 'error'

    result_choices = [
        (PENDING, 'Pending'),
        (PASSED, 'Passed'),
        (FAILED, 'Failed'),
        (EXECUTION_ERROR, 'Execution Error')
    ]

    script = models.OneToOneField(GeneratedScript, on_delete=models.CASCADE, related_name='execution_result')
    result = models.CharField(max_length=50, choices=result_choices)
    execution_time = models.FloatField()
    log_storage_key = models.TextField()
    screenshots_storage_key = models.TextField()


