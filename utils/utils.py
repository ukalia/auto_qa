from datetime import datetime, timezone as dt_tz
import html
import re
import requests
import tempfile
from utils.logger import Logger

logger = Logger(__name__).logger

def get_response(url, creds, headers, params=None):
    if params:
        response = requests.get(url, auth=creds, params=params, headers=headers)
        return response.json()
    response = requests.get(url, auth=creds, headers=headers)
    return response.json()

def convert_timestamp(ts):
    return datetime.fromtimestamp(int(ts), tz=dt_tz.utc) if ts else None

def sanitize_test_case_text(text):
    sanitized_text = []
    if not text:
        return sanitized_text
    lines = text.strip().split('\n')
    for i, line in enumerate(lines, 1):
        step_text = re.sub(r'^\d+\.\s*', '', line)
        step_text = re.sub(r'\s+', ' ', step_text)
        step_text = html.escape(step_text)
        text_object = {
            'order': i,
            'description': step_text
        }
        sanitized_text.append(text_object)
    return sanitized_text

def save_content_to_temp_file(content, suffix='.py'):
    try:
        temp_file = tempfile.NamedTemporaryFile(
            mode='w+',
            suffix=suffix,
            delete=False
        )
        temp_file.write(content)
        temp_file.close()
    except Exception as e:
        logger.exception(f'Error while writing the script to the temp file : {str(e)}')