#!/usr/bin/env python3
from os import environ

import boto3
import typing
from typing import List, Union, Optional, Dict

if typing.TYPE_CHECKING:
    from mypy_boto3_dynamodb import DynamoDBClient
    from mypy_boto3_dynamodb.type_defs import AttributeValueTypeDef

    PaginationKeyType = Dict[str, 'AttributeValueTypeDef']


def get_dynamodb_client() -> 'DynamoDBClient':
    return boto3.client('dynamodb')


def get_table_name() -> str:
    return environ['PACKAGING_TABLE_NAME']


def get_index_name() -> str:
    return environ['CONTEXT_INDEX_NAME']


def get_evaluated_key_list_in_package_query(package_id: str, chunk_size: int = 100) -> List[Union[None, str]]:
    starting_item = True

    # Start with None, so that we have the correct number of iterations in the sfn map
    key_list: List[Optional['PaginationKeyType']] = [None]
    exclusive_start_key = None

    while True:
        # Not the first iteration
        # And no exclusive start key so we have reached the end of the results
        if not exclusive_start_key and not starting_item:
            break
        if starting_item:
            starting_item = False
            dynamodb_response = get_dynamodb_client().query(
                TableName=get_table_name(),
                IndexName=f"{get_index_name()}-index",
                KeyConditionExpression="#index = :value",
                ExpressionAttributeNames={
                    "#index": get_index_name()
                },
                ExpressionAttributeValues={
                    ":value": {
                        "S": f"{package_id}__file"
                    }
                },
                Limit=chunk_size
            )
        else:
            dynamodb_response = get_dynamodb_client().query(
                TableName=get_table_name(),
                IndexName=f"{get_index_name()}-index",
                KeyConditionExpression="#index = :value",
                ExpressionAttributeNames={
                    "#index": get_index_name()
                },
                ExpressionAttributeValues={
                    ":value": {
                        "S": f"{package_id}__file"
                    }
                },
                ExclusiveStartKey=exclusive_start_key,
                Limit=chunk_size
            )

        # Set the new key list for the next iteration
        exclusive_start_key: Optional['PaginationKeyType'] = dynamodb_response.get('LastEvaluatedKey', None)

        # And add the key to the list
        if exclusive_start_key is not None:
            key_list.append(exclusive_start_key)

    return key_list


def handler(event, context):
    # Get inputs
    packaging_id = event.get("packagingJobId")
    chunk_sizes = event.get("chunkSizes")

    # Return the evaluated key list
    return {
        "startKeyList": get_evaluated_key_list_in_package_query(
            package_id=packaging_id,
            chunk_size=chunk_sizes
        )
    }


# if __name__ == "__main__":
#     from os import environ
#     import json
#
#     environ['AWS_PROFILE'] = 'umccr-production'
#     environ['PACKAGING_TABLE_NAME'] = 'DataSharingPackagingLookupTable'
#     environ['CONTEXT_INDEX_NAME'] = 'context'
#
#     print(json.dumps(
#         handler(
#             {
#                 "packagingJobId": "pkg.01K1W1ZF1JW9M5Z5N6TVNRJD3M",
#                 "chunkSizes": 50
#             },
#         None
#         ),
#         indent=4
#     ))
#
#     # {
#     #     "startKeyList": [
#     #         null,
#     #         {
#     #             "id": {
#     #                 "S": "01938922-7776-7f41-8de4-7eed55a30faf"
#     #             },
#     #             "context": {
#     #                 "S": "pkg.01K1W1ZF1JW9M5Z5N6TVNRJD3M__file"
#     #             },
#     #             "job_id": {
#     #                 "S": "pkg.01K1W1ZF1JW9M5Z5N6TVNRJD3M"
#     #             }
#     #         },
#     #         {
#     #             "id": {
#     #                 "S": "01938aad-c795-7551-8436-b9a2eeb5c455"
#     #             },
#     #             "job_id": {
#     #                 "S": "pkg.01K1W1ZF1JW9M5Z5N6TVNRJD3M"
#     #             },
#     #             "context": {
#     #                 "S": "pkg.01K1W1ZF1JW9M5Z5N6TVNRJD3M__file"
#     #             }
#     #         }
#     #     ]
#     # }
