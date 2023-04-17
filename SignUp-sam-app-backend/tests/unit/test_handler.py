import json
from unittest import TestCase, mock
from handler.create_post import lambda_handler

class TestCreatePostHandler(TestCase):

    def test_lambda_handler(self):
        # Mock DynamoDB table and environment variables
        table_name = 'test_table'
        region = 'us-east-1'
        os.environ['DYNAMODB_TABLE'] = table_name
        os.environ['REGION_NAME'] = region
        mock_table = mock.MagicMock()
        mock_table.query.return_value = {'Count': 0}
        mock_table.put_item.return_value = None
        with mock.patch('boto3.resource') as mock_resource:
            mock_resource.return_value.Table.return_value = mock_table

            # Test POST request with required fields
            post_data = {'Full Name': 'John Doe', 'Business Email': 'john.doe@example.com', 'Company Name': 'ACME', 'Cloud Usage': 'AWS'}
            event = {'httpMethod': 'POST', 'body': json.dumps(post_data)}
            response = lambda_handler(event, None)
            self.assertEqual(response['statusCode'], 200)
            self.assertEqual(response['headers']['Content-Type'], 'application/json')
            self.assertEqual(json.loads(response['body']), {'msg': 'Company added successfully'})
            mock_table.put_item.assert_called_once_with(Item=mock.ANY)

            # Test POST request missing required field
            post_data = {'Full Name': 'John Doe', 'Business Email': 'john.doe@example.com', 'Cloud Usage': 'AWS'}
            event = {'httpMethod': 'POST', 'body': json.dumps(post_data)}
            response = lambda_handler(event, None)
            self.assertEqual(response['statusCode'], 400)
            self.assertEqual(response['headers']['Content-Type'], 'application/json')
            self.assertEqual(json.loads(response['body']), {'msg': 'Missing required field(s)'})

            # Test POST request with existing email
            mock_table.query.return_value = {'Count': 1}
            post_data = {'Full Name': 'John Doe', 'Business Email': 'john.doe@example.com', 'Company Name': 'ACME', 'Cloud Usage': 'AWS'}
            event = {'httpMethod': 'POST', 'body': json.dumps(post_data)}
            response = lambda_handler(event, None)
            self.assertEqual(response['statusCode'], 400)
            self.assertEqual(response['headers']['Content-Type'], 'application/json')
            self.assertEqual(json.loads(response['body']), {'msg': 'Business Email already exists'})
