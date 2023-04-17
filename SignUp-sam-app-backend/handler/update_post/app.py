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

sqs = boto3.client('sqs', region_name=region)

companies_table = boto3.resource('dynamodb', region_name=region).Table(table_name)
headers = {
    'Access-Control-Allow-Origin': '*',  # Replace with your desired origin domain
    'Content-Type': 'application/json',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'PUT'
}



def lambda_handler(event, context):

    try:
        # Check if required fields are present in the request body
        put_data = json.loads(event['body'])
        required_fields = ['Business Email', 'Full Name']
        if not all(field in put_data for field in required_fields):
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'msg': 'Missing required field(s)'})
            }

        # Check if email already exists in the DynamoDB table
        response = companies_table.query(
            IndexName='BusinessEmailIndex',
            KeyConditionExpression=boto3.dynamodb.conditions.Key('Business Email').eq(put_data['Business Email'])
        )

        if response['Count'] == 0:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'msg': 'Business Email not found'})
            }

        # Check if the status is "VERIFIED"
        item = response['Items'][0]
        if item['Status'] == 'VERIFIED':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'msg': 'Company is already verified'})
            }

    

        # Update the company item in the DynamoDB table
        key = {'Business Email': put_data['Business Email']}
        expression = 'SET #s = :status, #ua = :updated_at, #ub = :updated_by'
        attribute_names = {
            '#s': 'Status',
            '#ua': 'Updated at',
            '#ub': 'Updated by'
        }
        attribute_values = {
            ':status': 'VERIFIED',
            ':updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            ':updated_by': 'lambda update'
        }
        update_response = companies_table.update_item(
            Key=key,
            UpdateExpression=expression,
            ExpressionAttributeNames=attribute_names,
            ExpressionAttributeValues=attribute_values,
            ReturnValues='ALL_NEW'
        )
        
        # Send a message to the SQS queue
        sqs_message = {'Business Email': put_data['Business Email'],'Full Name': put_data['Full Name'],'Type':'PUT'}
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
            'body': json.dumps({'msg': 'Company updated successfully', 'data': update_response['Attributes'], 'message_sent_to_sqs': response['MessageId']})

        }

    except Exception as e:
        print(f"An error occurred while updating data in DynamoDB: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'msg': 'Error updating data in DynamoDB'})
        }
