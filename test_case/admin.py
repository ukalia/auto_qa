from django.contrib import admin
from .models import TestCase, TestRun, TestRunCase


@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = [
        'test_case_id',
        'title',
        'steps',
        'expected_result',
        'status',
        'created_at',
        'updated_at'
    ]
    list_filter = [
        'platforms',
        'status',
        'created_at'
    ]
    search_fields = [
        'test_case_id',
        'title',
    ]
    readonly_fields = [
        'test_case_id',
        'status',
        'created_at',
        'updated_at'
    ]


@admin.register(TestRun)
class TestRunAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'total_test_cases',
        'pending_count',
        'passed_count',
        'failed_count',
        'created_at',
        'started_at',
        'completed_at'
    ]
    list_filter = [
        'started_at',
        'completed_at',
        'created_at'
    ]
    search_fields = ['name']
    readonly_fields = [
        'name',
        'total_test_cases',
        'pending_count',
        'passed_count',
        'failed_count',
        'created_at',
        'started_at',
        'completed_at'
    ]
    #filter_horizontal = ['test_cases']
    
    # fieldsets = (
    #     ('Run Information', {
    #         'fields': ('name', 'created_by')
    #     }),
    #     ('Test Cases', {
    #         'fields': ('test_cases',)
    #     }),
    #     ('Execution Timeline', {
    #         'fields': ('started_at', 'completed_at')
    #     }),
    #     ('Metadata', {
    #         'fields': ('created_at', 'updated_at')
    #     }),
    # )

@admin.register(TestRunCase)
class TestRunCaseAdmin(admin.ModelAdmin):
    list_display = [
        'test_run', 
        'test_case', 
        'status', 
    ]
    list_filter = [
        'status',
        'test_run',
        'test_case'
    ]
    search_fields = [
        'test_run__test_run_id',
        'test_run__name',
        'test_case__test_case_id', 
        'test_case__title'
    ]
    readonly_fields = ['created_at', 'updated_at']

