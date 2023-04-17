import boto3
import os
import json
import uuid
from datetime import datetime
from botocore.config import Config

# Initialize global variables
table_name = os.environ.get('DYNAMODB_TABLE')
region = os.environ.get('REGION_NAME')
queue_name = os.environ.get('SQS_QUEUE_NAME')
queue_url = os.environ.get('SQS_QUEUE_URL')
dlq_arn = os.environ.get('SQS_ARN')

companies_table = boto3.resource('dynamodb', region_name=region).Table(table_name)
sqs = boto3.client('sqs', region_name=region)

headers = {
    'Access-Control-Allow-Origin': '*',  # Replace with your desired origin domain
    'Content-Type': 'application/json',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'POST'
}

def lambda_handler(event, context):
    sqs_message = None
    try:
        # Check if required fields are present in the request body
        post_data = json.loads(event['body'])
        required_fields = ['Full Name', 'Business Email', 'Company Name', 'Cloud Usage']
        if not all(field in post_data for field in required_fields):
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'msg': 'Missing required field(s)'})
            }

        # Check if email already exists in the DynamoDB table
        response = companies_table.query(
            IndexName='BusinessEmailIndex',
            KeyConditionExpression=boto3.dynamodb.conditions.Key('Business Email').eq(post_data['Business Email'])
        )
        if response['Count'] > 0:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'msg': 'Business Email already exists'})
            }

        # Create a new company item
        current_timestamp = datetime.now().isoformat()
        updated_timestamp = current_timestamp
        created_by ="Lambda"
        updated_by ="Lambda"
        status ='NOT VERIFIED'
        params = {
            'id': str(uuid.uuid4()),
            'Full Name': post_data['Full Name'],
            'Business Email': post_data['Business Email'],
            'Phone Number': post_data.get('Phone Number'),
            'Company Name': post_data['Company Name'],
            'Cloud Usage': post_data['Cloud Usage'],
            'Created at': current_timestamp,
            'Updated at': updated_timestamp,
            'Created by': created_by,
            'Updated by': updated_by,
            'Status': status ,
        }

        # Insert the new company item into the DynamoDB table
        companies_table.put_item(Item=params)

        # Send a message to the SQS queue
        sqs_message = {'Business Email': post_data['Business Email'],'Full Name': post_data['Full Name'],'Type':'POST'}
        queue_attributes = {
            'KmsMasterKeyId': {
                'StringValue': 'alias/aws/sqs',
                'DataType': 'String'
            },
            'KmsDataKeyReusePeriodSeconds': {
                'StringValue': '300',
                'DataType': 'Number'
            },
        }
        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(sqs_message),
            MessageAttributes=queue_attributes,
        )
        print(f"Message sent to SQS: {response['MessageId']}")

        # Return a response to the client
        return {
            "statusCode": 200,
            "headers": headers,
            'body': json.dumps({'msg': 'Company added successfully', 'message_sent_to_sqs': response['MessageId']})
        }


    except Exception as e:
        print(f"An error occurred while inserting data into DynamoDB: {str(e)}")

        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'msg': 'Error inserting data into DynamoDB'})
        }
