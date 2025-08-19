from utils.base import BaseModel
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.fields import ArrayField
from django.db import models, transaction
from django.db.models import SET_NULL, CASCADE, PROTECT
from django.contrib.auth.models import User


class TestCaseCounter(BaseModel):
    '''
    Global monotonically increasing counter for TestCase IDs.

    This model is intended to have a single row (id=1). The `get_next_id()` class
    method increments and returns the next integer, inside a DB transaction, to
    generate stable, gap-minimized IDs (e.g., "TC-<n>") in `TestCase.save()`.
    '''
    last_id = models.IntegerField(default=0)
    
    @classmethod
    def get_next_id(cls):
        with transaction.atomic():
            counter, created = cls.objects.get_or_create(id=1)
            counter.last_id += 1
            counter.save()
            return counter.last_id


class TestRunCounter(BaseModel):
    '''
    Global monotonically increasing counter for TestRun IDs.

    Similar to `TestCaseCounter`, this table is expected to have a single row
    (id=1). The `get_next_id()` class method increments and returns the next
    integer used by `TestRun.save()` to create IDs like "TR-<n>".
    '''
    last_id = models.IntegerField(default=0)

    @classmethod
    def get_next_id(cls):
        with transaction.atomic():
            counter, created = cls.objects.get_or_create(id=1)
            counter.last_id += 1
            counter.save()
            return counter.last_id


class TestCasePlatform(models.Model):
    '''
    Lookup table of execution platforms/environments (e.g., PlatformOne, iOS, Android).

    Fields:
        platform_id (int, PK): Stable numeric identifier.
        name (str): platform name.
    '''
    platform_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=50, null=False)

    def __str__(self):
        return self.name


class TestCaseCustomer(models.Model):
    '''
    Lookup table of customers/tenants the test cases may target.

    Fields:
        customer_id (int, PK): Stable numeric identifier.
        name (str): customer name.
    '''
    customer_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=50, null=False)

    def __str__(self):
        return self.name


class TestCase(BaseModel):
    '''
    Canonical definition of a single test case, including steps, expectations,
    scope (project/suite/section), status, and relationships to platforms/customers.

    Fields:
        test_case_id (str, PK): unique ID (e.g., "TC-42").
        tickets (Array[str]): External references (e.g., Jira IDs).
        title (str): Short descriptive title of the test case.
        preconditions (JSON): Preconditions required before executing the test.
        steps (JSON): Ordered steps to execute (author-defined schema).
        expected_result (JSON): Expected outcomes (author-defined schema).
        platforms (M2M[TestCasePlatform]): Target platforms/environments.
        project (str): Optional project grouping.
        suite (str): Optional suite grouping.
        section (str): Optional section grouping.
        created_by (FK[User], PROTECT): Author/owner; protected from cascade delete.
        status (str, choices): Lifecycle status (ready/automated/manual_review/no_auto).
        test_rail_id (str): Optional upstream TestRail reference.
        customers (M2M[TestCaseCustomer]): Applicable customer(s)/tenants.
        comments (Text): Free-form notes.
        tr_created_at (datetime): Source-system creation timestamp (if mirrored).
        tr_updated_at (datetime): Source-system update timestamp (if mirrored).
    '''
    STATUS_CHOICES = [
        ('ready', 'ready'),
        ('automated', 'automated'),
        ('manual_review', 'manual_review'),
        ('no_auto', 'no_automation_to_be_done')
    ]
    test_case_id = models.CharField(unique=True, max_length=100, unique=True, editable=False, db_index=True)
    tickets = ArrayField(models.CharField(max_length=100), size=10, null=True, blank=True)
    title = models.CharField(max_length=200, null=False, blank=False)
    preconditions = models.JSONField(null=True, blank=True)
    steps = models.JSONField(null=False, blank=True)
    expected_result = models.JSONField(null=False, blank=True)
    platforms = models.ManyToManyField(TestCasePlatform, blank=True, related_name='test_case_platforms')
    project = models.CharField(max_length=100, null=True, blank=True)
    suite = models.CharField(max_length=100, null=True, blank=True)
    section = models.CharField(max_length=100, null=True, blank=True)
    created_by = models.ForeignKey(User,on_delete=PROTECT, null=True)
    status = models.CharField(max_length=100, choices=STATUS_CHOICES, default='ready', db_index=True)
    test_rail_id = models.CharField(max_length=100, null=True, blank=True)
    customers = models.ManyToManyField(TestCaseCustomer, blank=True, related_name='test_case_customers')
    comments = models.TextField(null=True, blank=True)
    tr_created_at = models.DateTimeField(null=True, blank=True)
    tr_updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.test_case_id} - {self.title}'

    def save(self, *args, **kwargs):
        if not self.test_case_id:
            next_id = TestCaseCounter.get_next_id()
            self.test_case_id = f'TC-{next_id}'
        super().save(*args, **kwargs)

    class Meta:
        app_label = 'test_case'
        db_table = 'test_case_tc'
        ordering = ['-created_at']
        indexes = [
            GinIndex(fields=['tickets'])
        ]


class TestCaseHistory(BaseModel):
    '''
    Immutable versioned history for a `TestCase`.

    Each row represents a specific version snapshot for a given test case.
    The `version` is auto-incremented per test case on insert.

    Fields:
        updated_by (FK[User], SET_NULL): User who caused the change (if known).
        test_case (FK[TestCase], CASCADE): The test case this history entry belongs to.
        version (int): Sequential version number per `test_case` (1,2,3,...).
    '''
    updated_by = models.ForeignKey(User, on_delete=SET_NULL, null=True)
    test_case = models.ForeignKey(TestCase, on_delete=CASCADE)
    version = models.IntegerField()

    def save(self, *args, **kwargs):
        if not self.pk:
            last = (TestCaseHistory.objects
                    .filter(test_case=self.test_case)
                    .order_by('-version')
                    .first())
            self.version = (last.version + 1) if last else 1
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['test_case', 'version'], name='uniq_test_case_version'),
        ]


class TestRun(BaseModel):
    '''
    A collection/execution of one or more test cases, tracked as a single run.

    Fields:
        test_run_id (str, PK): Human-readable unique ID (e.g., "TR-17").
        test_case (M2M[TestCase]): Test cases included in this run.
        created_by (FK[User], PROTECT): User who created/scheduled the run.
        name (str): Friendly name for the run (e.g., "Nightly Smoke 2025-08-19").
        started_at (datetime): Timestamp when execution began (optional).
        completed_at (datetime): Timestamp when execution finished (optional).
        save_beyond_expiration (bool): Whether to retain artifacts/results
            beyond normal retention windows.
    '''
    test_run_id = models.CharField(unique=True, max_length=20, unique=True, editable=False, db_index=True)
    test_case = models.ManyToManyField(TestCase, related_name='test_run_cases')
    created_by = models.ForeignKey(User, on_delete=PROTECT , null=False, blank=False)
    name = models.CharField(max_length=50, null=False, blank=False)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    save_beyond_expiration = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.test_run_id} - {self.name}'

    def save(self, *args, **kwargs):
        if not self.test_run_id:
            next_id = TestRunCounter.get_next_id()
            self.test_run_id = f'TR-{next_id}'
        super().save(*args, **kwargs)

    class Meta:
        app_label = 'test_case'
        db_table = 'test_case_tr'
        ordering = ['-created_at']
