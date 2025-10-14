import json
import boto3
import os
import base64
import re
import logging
from datetime import datetime, timedelta
import holidays
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
ssm = boto3.client('ssm')
dynamodb = boto3.resource('dynamodb')
acm_pca = boto3.client('acm-pca')
lambda_client = boto3.client('lambda')

BUCKET_NAME = os.environ.get('CSR_BUCKET_NAME')
CERT_TABLE = os.environ.get('CERT_TABLE_NAME')
MNO_CONFIG_TABLE = os.environ.get('MNO_CONFIG_TABLE_NAME')
CONTACTS_TABLE = os.environ.get('CONTACTS_TABLE_NAME')
CERTIFICATE_DOMAIN = os.environ.get('CERTIFICATE_DOMAIN')
PCA_ARN = os.environ.get('PCA_ARN')
NOTIFY_LAMBDA_ARN = os.environ.get('NOTIFY_LAMBDA_ARN')

VALID_CSR_TEMPLATE_ID = os.environ.get('VALID_CSR_TEMPLATE_ID')
INVALID_FIRST_CSR_TEMPLATE_ID = os.environ.get('INVALID_FIRST_CSR_TEMPLATE_ID')
INVALID_RETRY_CSR_TEMPLATE_ID = os.environ.get('INVALID_RETRY_CSR_TEMPLATE_ID')

# Holiday freeze periods (format: [start_date, end_date])
FREEZE_PERIODS = [
    ["12-20", "01-05"]
]

# UK holidays
uk_holidays = holidays.UK()


def valid_wednesday(check_date):
    if check_date.weekday() != 2:
        return False
    if check_date in uk_holidays:
        return False
    month_day = check_date.strftime("%m-%d")
    for period in FREEZE_PERIODS:
        start, end = period
        if start > end:
            if month_day >= start or month_day <= end:
                return False
        else:
            if start <= month_day <= end:
                return False
    return True


def find_next_valid_wednesday(start_date, time_hour=0):
    current_date = start_date + timedelta(days=1)
    days_until_wed = (2 - current_date.weekday()) % 7
    next_wed = current_date + timedelta(days=days_until_wed)
    next_wed = next_wed.replace(hour=time_hour, minute=0, second=0, microsecond=0)
    while not valid_wednesday(next_wed):
        next_wed = next_wed + timedelta(days=7)
    return next_wed


def calculate_certificate_validity(creation_date):
    # Activation is at least 7 days from creation, then aligned to a valid Wednesday (at midnight)
    min_activation_date = creation_date + timedelta(days=7)
    validity_start = find_next_valid_wednesday(min_activation_date, time_hour=0)
    waiting_days = (validity_start - creation_date).days
    candidate_expiry = creation_date + timedelta(days=waiting_days + 90)
    validity_end = find_next_valid_wednesday(candidate_expiry, time_hour=10)
    return validity_start, validity_end


def check_for_overlap(mno_id, validity_start, validity_end, new_cert_type):
    cert_table = dynamodb.Table(CERT_TABLE)
    response = cert_table.query(
        KeyConditionExpression="MnoID = :mno_id",
        ExpressionAttributeValues={":mno_id": mno_id}
    )
    for item in response.get('Items', []):
        # Skip certificates of the same type
        if item.get("Type") == new_cert_type:
            continue
        existing_start = datetime.fromisoformat(item.get('ValidFrom'))
        existing_end = datetime.fromisoformat(item.get('ExpiryDate'))
        if validity_start <= existing_end and validity_end >= existing_start:
            return True
    return False


def validate_csr(csr_content, mno_config):
    try:
        csr = x509.load_pem_x509_csr(csr_content.encode('utf-8'), default_backend())
        subject = csr.subject
        subject_dict = {}
        for attr in subject:
            name = attr.oid._name
            subject_dict[name] = attr.value
            logger.info(f"Extracted attribute: {name} -> {attr.value}")
            if name.lower() == "commonname":
                subject_dict["CN"] = attr.value
        logger.info(f"Full subject dictionary: {subject_dict}")
        required_fields = mno_config.get('RequiredCSRFields', {})
        for field, expected_pattern in required_fields.items():
            if field not in subject_dict:
                return False, f"Missing required field: {field}"
            if expected_pattern and not re.match(expected_pattern, subject_dict[field]):
                return False, f"Field {field} does not match required pattern"
        public_key = csr.public_key()
        if not isinstance(public_key, rsa.RSAPublicKey):
            return False, f"Invalid key type. Expected RSAPublicKey, got {type(public_key).__name__}"
        if hasattr(public_key, 'key_size'):
            min_key_size = mno_config.get('MinKeySize', 2048)
            if public_key.key_size < min_key_size:
                return False, f"Key size too small. Minimum required: {min_key_size} bits"
        return True, "CSR validation successful"
    except Exception as e:
        return False, f"CSR validation error: {str(e)}"


def generate_certificate(csr_content, mno_id, cert_id, validity_start, validity_end):
    try:
        response = acm_pca.issue_certificate(
            CertificateAuthorityArn=PCA_ARN,
            Csr=csr_content.encode('utf-8'),
            SigningAlgorithm='SHA256WITHRSA',
            TemplateArn='arn:aws:acm-pca:::template/EndEntityServerAuthCertificate/V1',
            Validity={
                'Value': int((validity_end - validity_start).days),
                'Type': 'DAYS'
            },
            ValidityNotBefore={
                'Value': int(validity_start.timestamp()),
                'Type': 'ABSOLUTE'
            }
        )
        certificate_arn = response['CertificateArn']
        waiter = acm_pca.get_waiter('certificate_issued')
        waiter.wait(
            CertificateAuthorityArn=PCA_ARN,
            CertificateArn=certificate_arn
        )
        cert_response = acm_pca.get_certificate(
            CertificateAuthorityArn=PCA_ARN,
            CertificateArn=certificate_arn
        )
        certificate = cert_response['Certificate']
        return certificate
    except Exception as e:
        logger.error(f"Error generating certificate: {str(e)}")
        raise e


def generate_download_link(mno_id, cert_id, expiry_time):
    params = {
        'location': f"certs/{mno_id}/{cert_id}.crt",
        'type': 'GET',
        'expiry': expiry_time.isoformat(),
        'reference': f"{mno_id}-{cert_id}-{int(datetime.now().timestamp())}"
    }
    encoded_params = base64.urlsafe_b64encode(json.dumps(params).encode()).decode()
    download_url = f"https://{CERTIFICATE_DOMAIN}/download?q={encoded_params}"
    return download_url


def handle_valid_csr(mno_id, cert_id, csr_content, mno_config, mno_contacts):
    now = datetime.utcnow()
    validity_start, validity_end = calculate_certificate_validity(now)
    # Retrieve certificate type from MNO configuration
    new_cert_type = mno_config.get("CertificateType", "Default")
    # Check for overlap with certificates of a different type
    if check_for_overlap(mno_id, validity_start, validity_end, new_cert_type):
        while check_for_overlap(mno_id, validity_start, validity_end, new_cert_type):
            validity_start = find_next_valid_wednesday(validity_start + timedelta(days=1))
            validity_end = find_next_valid_wednesday(validity_start + timedelta(days=90), time_hour=10)
    certificate = generate_certificate(csr_content, mno_id, cert_id, validity_start, validity_end)
    cert_key = f"certs/{mno_id}/{cert_id}.crt"
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=cert_key,
        Body=certificate.encode('utf-8')
    )
    download_expiry = now + timedelta(days=14)
    download_url = generate_download_link(mno_id, cert_id, download_expiry)
    cert_table = dynamodb.Table(CERT_TABLE)
    cert_table.put_item(
        Item={
            "MnoID": mno_id,
            "CertID": cert_id,
            "Status": "CertGenerated",
            "DownloadURL": download_url,
            "IssuedDate": now.isoformat(),
            "ValidFrom": validity_start.isoformat(),
            "ExpiryDate": validity_end.isoformat(),
            "Type": new_cert_type
        }
    )
    emails = mno_contacts.get("Emails", [])
    endpoint_names = mno_contacts.get("EndpointNames", "Unknown")
    for email in emails:
        notify_payload = {
            "email_address": email,
            "template_id": VALID_CSR_TEMPLATE_ID,
            "personalisation": {
                "mno_name": mno_id,
                "endpoint_site_names": endpoint_names,
                "cert_start_time": validity_start.strftime("%Y-%m-%d %H:%M:%S"),
                "certificate_expiry_time": validity_end.strftime("%Y-%m-%d %H:%M:%S"),
                "current_cert_end_time": validity_end.strftime("%Y-%m-%d %H:%M:%S"),
                "download_url": download_url
            }
        }
        lambda_client.invoke(
            FunctionName=NOTIFY_LAMBDA_ARN,
            InvocationType='Event',
            Payload=json.dumps(notify_payload)
        )
    return {
        "status": "success",
        "message": "Certificate generated successfully",
        "valid_from": validity_start.isoformat(),
        "expiry": validity_end.isoformat()
    }


def generate_csr_upload_link(mno_id, cert_id, expiry_duration=604800):
    now = datetime.utcnow()
    expiry_timestamp = now + timedelta(seconds=expiry_duration)
    expiry_str = expiry_timestamp.strftime("%Y%m%d%H%M")

    params = {
        "location": f"/received/{mno_id}/{cert_id}_retry.csr",
        "type": "upload",
        "expiry": expiry_str,
        "reference": f"{mno_id}-{cert_id}-retry"
    }

    encoded_params = base64.urlsafe_b64encode(json.dumps(params).encode()).decode()
    upload_link = f"https://{CERTIFICATE_DOMAIN}/received?data={encoded_params}"
    return upload_link


def handle_invalid_csr(mno_id, cert_id, error_message, mno_contacts, is_first_attempt):
    cert_table = dynamodb.Table(CERT_TABLE)
    update_data = {
        "Status": "CSRInvalid",
        "ValidationError": error_message
    }
    if is_first_attempt:
        custom_upload_link = generate_csr_upload_link(mno_id, cert_id, expiry_duration=604800)
        update_data["RetryUploadURL"] = custom_upload_link

    update_expression = "SET #status = :status, ValidationError = :error"
    expression_attribute_names = {"#status": "Status"}
    expression_attribute_values = {
        ":status": update_data["Status"],
        ":error": update_data["ValidationError"]
    }
    if is_first_attempt:
        update_expression += ", RetryUploadURL = :url"
        expression_attribute_values[":url"] = update_data["RetryUploadURL"]
    cert_table.update_item(
        Key={"MnoID": mno_id, "CertID": cert_id},
        UpdateExpression=update_expression,
        ExpressionAttributeNames=expression_attribute_names,
        ExpressionAttributeValues=expression_attribute_values
    )
    emails = mno_contacts.get("Emails", [])
    endpoint_names = mno_contacts.get("EndpointNames", "Unknown")
    for email in emails:
        template_id = INVALID_FIRST_CSR_TEMPLATE_ID if is_first_attempt else INVALID_RETRY_CSR_TEMPLATE_ID
        personalisation = {
            "mno_name": mno_id,
            "endpoint_site_names": endpoint_names,
            "error_message": error_message
        }
        if is_first_attempt:
            personalisation["upload_url"] = update_data["RetryUploadURL"]
        notify_payload = {
            "email_address": email,
            "template_id": template_id,
            "personalisation": personalisation
        }
        lambda_client.invoke(
            FunctionName=NOTIFY_LAMBDA_ARN,
            InvocationType='Event',
            Payload=json.dumps(notify_payload)
        )
    return {
        "status": "error",
        "message": "CSR validation failed",
        "error": error_message,
        "is_first_attempt": is_first_attempt
    }


def lambda_handler(event, context):
    try:
        record = event['Records'][0]
        s3_info = record['s3']
        bucket = s3_info['bucket']['name']
        object_key = s3_info['object']['key']
        parts = object_key.split('/')
        if len(parts) < 3 or parts[0] != "received":
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid file path structure"})
            }
        mno_id = parts[1]
        cert_file = parts[2]
        cert_id = cert_file.replace('.csr', '').replace('_retry', '')
        logger.info(f"Processing CSR for MNO: {mno_id}, Cert: {cert_id}")
        is_retry = '_retry' in cert_file
        is_first_attempt = not is_retry
        try:
            response = s3.get_object(Bucket=bucket, Key=object_key)
            csr_content = response['Body'].read().decode('utf-8')
        except Exception as e:
            logger.error(f"Error reading CSR from S3: {str(e)}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": f"Could not read CSR: {str(e)}"})
            }
        mno_config_table = dynamodb.Table(MNO_CONFIG_TABLE)
        try:
            mno_config_response = mno_config_table.get_item(Key={"MnoID": mno_id})
            mno_config = mno_config_response.get("Item", {})
            if not mno_config:
                logger.error(f"No configuration found for MNO {mno_id}")
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": f"No configuration found for MNO {mno_id}"})
                }
        except Exception as e:
            logger.error(f"Error retrieving MNO configuration: {str(e)}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": f"Error retrieving MNO configuration: {str(e)}"})
            }
        contacts_table = dynamodb.Table(CONTACTS_TABLE)
        try:
            contacts_response = contacts_table.get_item(Key={"MnoID": mno_id})
            mno_contacts = contacts_response.get("Item", {})
            if not mno_contacts or not mno_contacts.get("Emails"):
                logger.error(f"No contact emails found for MNO {mno_id}")
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": f"No contact emails found for MNO {mno_id}"})
                }
        except Exception as e:
            logger.error(f"Error retrieving MNO contacts: {str(e)}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": f"Error retrieving MNO contacts: {str(e)}"})
            }
        is_valid, error_message = validate_csr(csr_content, mno_config)
        if is_valid:
            result = handle_valid_csr(mno_id, cert_id, csr_content, mno_config, mno_contacts)
        else:
            result = handle_invalid_csr(mno_id, cert_id, error_message, mno_contacts, is_first_attempt)
        return {
            "statusCode": 200,
            "body": json.dumps(result)
        }
    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Unhandled error: {str(e)}"})
        }
