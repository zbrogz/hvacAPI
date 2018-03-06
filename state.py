import boto3
import os
import json
from uuid import uuid4 as Uuid
import decimal


# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)


def state_table():
    return boto3.resource('dynamodb').Table(os.environ['STATE_TABLE_NAME'])


def get_hvac(uuid):
    hvac = state_table().get_item(Key={'uuid': uuid})
    response = {
        'isBase64Encoded': 'false',
        'statusCode': 200,
        'headers': {'Access-Control-Allow-Origin': '*'},
        'body': json.dumps(hvac['Item'], cls=DecimalEncoder)
    }
    return response


def get_all_hvacs():
    hvacs = state_table().scan()
    response = {
        'isBase64Encoded': 'false',
        'statusCode': 200,
        'headers': {'Access-Control-Allow-Origin': '*'},
        'body': json.dumps(hvacs['Items'], cls=DecimalEncoder)
    }
    return response


def create_hvac(hvac_data):
    if (not hvac_data['area'] or not isinstance(hvac_data['area'], str)):
        raise Exception('Error. Must specify area.')
    uuid = Uuid().hex
    state = {
        'uuid': uuid,
        'area': hvac_data['area'],
        'heater': False,
        'ac': False,
        'fan': False,
        'off_time': 0,
        'min_off_time': 10,
        'update_period': 30
    }
    state_table().put_item(Item=state)
    response = {
        'isBase64Encoded': 'false',
        'statusCode': 200,
        'headers': {'Access-Control-Allow-Origin': '*'},
        'body': json.dumps(state)
    }
    return response


def update_hvac(uuid, hvac_data):
    updateExpressions = []
    attributeValues = {}
    if 'area' in hvac_data and isinstance(hvac_data['area'], str):
        updateExpressions.append("area = :a")
        attributeValues[':a'] = hvac_data['area']
    if 'heater' in hvac_data and isinstance(hvac_data['heater'], bool):
        updateExpressions.append("heater = :h")
        attributeValues[':h'] = hvac_data['heater']
    if 'ac' in hvac_data and isinstance(hvac_data['ac'], bool):
        updateExpressions.append("ac = :c")
        attributeValues[':c'] = hvac_data['ac']
    if 'fan' in hvac_data and isinstance(hvac_data['fan'], bool):
        updateExpressions.append("fan = :f")
        attributeValues[':f'] = hvac_data['fan']
    if 'off_time' in hvac_data and isinstance(hvac_data['off_time'], int):
        updateExpressions.append("off_time = :o")
        attributeValues[':o'] = hvac_data['off_time']
    if ('min_off_time' in hvac_data and
            isinstance(hvac_data['min_off_time'], int)):
        updateExpressions.append("min_off_time = :m")
        attributeValues[':m'] = hvac_data['min_off_time']
    if ('update_period' in hvac_data and
            isinstance(hvac_data['update_period'], int)):
        updateExpressions.append("update_period = :u")
        attributeValues[':u'] = hvac_data['update_period']

    if len(updateExpressions) < 1:
        raise Exception('Error. Invalid update request.')
    updateExpressionStr = "set " + (",".join(updateExpressions))

    state_table().update_item(
        Key={'uuid': uuid},
        UpdateExpression=updateExpressionStr,
        ExpressionAttributeValues=attributeValues,
        ReturnValues="ALL_NEW")

    response = {
        "isBase64Encoded": "false",
        "statusCode": 200,
        'headers': {'Access-Control-Allow-Origin': '*'},
        "body": "{\"message\": \"Hvac updated\"}"
    }
    return response


def delete_hvac(uuid):
    # Delete hvac state
    state_table().delete_item(Key={'uuid': uuid})
    response = {
        "isBase64Encoded": "false",
        "statusCode": 200,
        'headers': {'Access-Control-Allow-Origin': '*'},
        "body": "{\"message\": \"Hvac deleted.\"}"
    }
    return response


def lambda_handler(event, context):
    try:
        if event['httpMethod'] == "GET":
            if event['pathParameters'] and 'uuid' in event['pathParameters']:
                return get_hvac(event['pathParameters']['uuid'])
            else:
                return get_all_hvacs()

        elif event['httpMethod'] == "POST":
            if event['body'] and not event['pathParameters']:
                return create_hvac(json.loads(event['body']))
            else:
                raise Exception(
                    'Error. HTTP body required for POST to create hvac.')

        elif event['httpMethod'] == "PUT":
            if (event['body'] and event['pathParameters'] and
                    'uuid' in event['pathParameters']):
                return update_hvac(event['pathParameters']['uuid'],
                                   json.loads(event['body']))

        elif event['httpMethod'] == "DELETE":
            if event['pathParameters'] and 'uuid' in event['pathParameters']:
                return delete_hvac(event['pathParameters']['uuid'])
        else:
            raise Exception("Invalid HTTP method")
    except Exception as e:
        response = {
            "isBase64Encoded": "false",
            "statusCode": 400,
            'headers': {'Access-Control-Allow-Origin': '*'},
            "body": "{\"errorMessage\": \"" + e.args[0] + ".\"}"
        }
        return response
