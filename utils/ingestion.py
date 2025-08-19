import logging

from auto_qa import settings
from test_case.models import TestCase, TestCaseCustomer, TestCasePlatform
from utils.utils import get_response, convert_timestamp, sanitize_test_case_text

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_URL = settings.TESTRAIL_BASE_URL
PROJECT_ID = settings.PROJECT_ID
SUITE_ID = settings.SUITE_ID
AUTH = settings.AUTH
HEADERS = {
    'Accept': 'application/json'
}
TEST_CASE_FIELDS = ['custom_customers', 'custom_platfroms']

def ingest_test_rail(**kwargs):
    try:
        logger.info('Ingest Test Rail Data : BEGIN')
        fetch_fields = kwargs.get('fetch_fields')
        if fetch_fields:
            get_case_fields()
            return
        project = get_project()
        suite = get_suite()
        sections = get_sections()
        get_test_cases(project, suite, sections)
    except Exception as e:
         logger.exception(f'Error while ingestion of test rail data: {str(e)}')


def get_project():
    url = f'{BASE_URL}/get_project/{PROJECT_ID}'
    response = get_response(url, AUTH, HEADERS)
    return {PROJECT_ID: response.get('name', 'Unnamed')}


def get_suite(): 
    url = f'{BASE_URL}/get_suite/{SUITE_ID}'
    response = get_response(url, AUTH, HEADERS)
    return {SUITE_ID: response.get('name', 'Unnamed')}


def get_sections():
    url = f'{BASE_URL}/get_sections/{PROJECT_ID}'
    params = {'suite_id': SUITE_ID}
    response = get_response(url, AUTH, HEADERS, params=params)
    sections = response.get('sections', [])
    result = {}
    if sections:
        for section in sections:
            result[section.get('id')] = section.get('name', 'Unnamed').strip()
    return result


def get_case_fields():
    url = f'{BASE_URL}/get_case_fields'
    response = get_response(url, AUTH, HEADERS)
    result = get_customers_platforms(response)
    customers = result.get(TEST_CASE_FIELDS[0])
    platforms = result.get(TEST_CASE_FIELDS[1])
    populate_customers(customers)
    populate_platforms(platforms)


def get_customers_platforms(response):
    result = {}
    for res in response:
        system_name = res.get('system_name')
        if system_name in TEST_CASE_FIELDS:
            sub_dict = {}
            configs = res.get('configs')
            if configs and isinstance(configs, list):
                items = configs[0].get('options', {}).get('items')
                if items:
                    for item in items.split('\n'):
                        parts = item.split(', ')
                        try:
                            field_id = int(parts[0])
                            label = parts[1].strip() if len(parts) > 1 else ''
                            sub_dict[field_id] = label
                        except (ValueError, IndexError):
                            logger.exception(f'Error getting {item}')
                            continue
            result[system_name] = sub_dict
    return result


def populate_customers(customers):
    if not customers:
        logger.debug('No customers fetched from Test Rail')
    for cust_id, cust in customers.items():
        cust_params = {
            'customer_id': cust_id,
            'name': cust
        }
        try:
            TestCaseCustomer.objects.create(**cust_params)
            logger.info(f'{cust_id}-{cust} instance created')
        except Exception as e:
            logger.exception(f'{cust_id}-{cust} instance not created')
            continue


def populate_platforms(platforms):
    if not platforms:
        logger.debug('No Platforms fetched from Test Rail')
    for pl_id, pl in platforms.items():
        pl_params = {
            'platform_id': pl_id,
            'name': pl
        }
        try:
            TestCasePlatform.objects.create(**pl_params)
            logger.info(f'{pl_id}-{pl} instance created')
        except Exception as e:
            logger.exception(f'{pl_id}-{pl} instance not created')
            continue


def get_test_cases(project, suite, sections, offset=0):
    url = f'{BASE_URL}/get_cases/{PROJECT_ID}'
    params = {
        'suite_id': SUITE_ID,
        'limit': 250,
        'offset': offset
    }
    response = get_response(url, AUTH, HEADERS, params=params)
    import_test_cases_to_db(project, suite, sections, response.get('cases'))
    next = response.get('_links', {}).get('next')
    if next:
        offset += 250
        get_test_cases(project, suite, sections, offset)


def import_test_cases_to_db(project, suite, sections, cases):
    if not cases:
        return
    try:
        for case in cases:
            refs = case.get('refs')
            tickets = [x.strip() for x in refs.split(',')] if refs else None
            preconds = sanitize_test_case_text(case.get('custom_preconds', ''))
            steps = sanitize_test_case_text(case.get('custom_steps', ''))
            expected_result = sanitize_test_case_text(case.get('custom_expected', ''))
            comments = sanitize_test_case_text(case.get('custom_comments'))
            case_params = {
                'test_rail_id': case.get('id'),
                'title': case.get('title'),
                'tickets': tickets,
                'tr_created_at': convert_timestamp(case.get('created_on')),
                'tr_updated_at': convert_timestamp(case.get('updated_on')),
                'preconditions': preconds,
                'steps': steps,
                'expected_result': expected_result,
                'comments': comments,
                'project': project.get(PROJECT_ID),
                'suite': suite.get(SUITE_ID),
                'section': sections.get(case.get('section_id'), 'Unnamed'),
            }
            test_case = TestCase.objects.create(**case_params)
            customers = case.get('custom_customers')
            platforms = case.get('custom_platfroms')
            if customers:
                test_case.customers.set(TestCaseCustomer.objects.filter(pk__in=customers))
            if platforms:
                test_case.platforms.set(TestCasePlatform.objects.filter(pk__in=platforms))
    except Exception as e:
        logger.exception(f'Error while importing test case {case.get("id")} to db : {str(e)}')
