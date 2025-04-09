"""Tests for test_mongo_jsonschema_tools.py."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from wipac_dev_tools.mongo_jsonschema_tools import (
    DocumentNotFoundException,
    MongoJSONSchemaValidatedCollection,
    MongoJSONSchemaValidationError,
    _convert_mongo_to_jsonschema,
)


@pytest.fixture
def schema():
    return {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "address": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "zip": {"type": "string"},
                },
                "required": ["city", "zip"],
            },
        },
        "required": ["name", "age"],
    }


@pytest.fixture
def mock_collection():
    return AsyncMock()


@pytest.fixture
def mongo_collection(schema, mock_collection):
    with patch(
        "mongo_jsonschema_tools.AsyncIOMotorCollection", return_value=mock_collection
    ):
        client = MagicMock()
        return MongoJSONSchemaValidatedCollection(
            mongo_client=client,
            database_name="test_db",
            collection_name="test_coll",
            collection_jsonschema_spec=schema,
            parent_logger=logging.getLogger("test_logger"),
        )


########################################################################################
# _convert_mongo_to_jsonschema()


def test_0000__convert_no_dots_no_partial_returns_as_is(schema):
    """Test conversion passes through doc and schema as-is if no dotted keys."""
    doc = {"name": "Charlie", "age": 28}
    out_doc, out_schema = _convert_mongo_to_jsonschema(
        doc, schema, allow_partial_update=False
    )
    assert out_doc == doc
    assert out_schema == schema


def test_0001__convert_with_dots_no_partial_raises(schema):
    """Test conversion with dotted keys and no partial update raises error."""
    doc = {"address.city": "Springfield"}
    with pytest.raises(MongoJSONSchemaValidationError):
        _convert_mongo_to_jsonschema(doc, schema, allow_partial_update=False)


def test_0002__convert_with_dots_and_partial_succeeds(schema):
    """Test conversion with dotted keys and partial update flattens and validates."""
    doc = {"address.city": "Metropolis"}
    out_doc, out_schema = _convert_mongo_to_jsonschema(
        doc, schema, allow_partial_update=True
    )
    assert out_doc == {"address": {"city": "Metropolis"}}
    assert out_schema["required"] == []
    assert out_schema["properties"]["address"]["required"] == []


########################################################################################
# _validate()


def test_0100__validate__valid_full_doc(mongo_collection):
    """Test _validate with a fully valid document."""
    doc = {"name": "Alice", "age": 30}
    # Should not raise
    mongo_collection._validate(doc)


def test_0101__validate__invalid_full_doc(mongo_collection):
    """Test _validate with a full document missing required fields."""
    doc = {"name": "Bob"}  # missing "age"
    with pytest.raises(MongoJSONSchemaValidationError):
        mongo_collection._validate(doc)


def test_0102__validate__valid_partial_doc(mongo_collection):
    """Test _validate with valid dotted keys and partial update allowed."""
    doc = {"address.city": "Springfield", "address.zip": "12345"}
    # Should not raise
    mongo_collection._validate(doc, allow_partial_update=True)


def test_0103__validate__invalid_partial_doc(mongo_collection):
    """Test _validate with invalid partial doc missing required subfield."""
    doc = {"address.city": "Springfield"}  # missing zip
    with pytest.raises(MongoJSONSchemaValidationError):
        mongo_collection._validate(doc, allow_partial_update=True)


def test_0104__validate__partial_doc_not_allowed(mongo_collection):
    """Test _validate with dotted keys and partial updates disallowed raises error."""
    doc = {"address.city": "Springfield"}
    with pytest.raises(MongoJSONSchemaValidationError):
        mongo_collection._validate(doc, allow_partial_update=False)


########################################################################################
# _validate_mongo_update()


def test_0200__validate_mongo_update__unsupported_operator(mongo_collection):
    """Test _validate_mongo_update with unsupported operator raises error."""
    update = {"$rename": {"name": "full_name"}}
    with pytest.raises(KeyError):
        mongo_collection._validate_mongo_update(update)


def test_0201__validate_mongo_update__set(mongo_collection):
    """Test _validate_mongo_update with valid $set operator."""
    update = {"$set": {"name": "Alice", "age": 42}}
    mongo_collection._validate_mongo_update(update)


def test_0202__validate_mongo_update__set_invalid(mongo_collection):
    """Test _validate_mongo_update with invalid $set schema."""
    update = {"$set": {"name": "Bob"}}
    with pytest.raises(MongoJSONSchemaValidationError):
        mongo_collection._validate_mongo_update(update)


def test_0203__validate_mongo_update__push(mongo_collection):
    """Test _validate_mongo_update with valid $push operator."""
    update = {"$push": {"address": {"city": "Chicago", "zip": "60601"}}}
    mongo_collection._validate_mongo_update(update)


def test_0204__validate_mongo_update__push_invalid(mongo_collection):
    """Test _validate_mongo_update with invalid $push schema."""
    update = {"$push": {"address": {"city": "Chicago"}}}
    with pytest.raises(MongoJSONSchemaValidationError):
        mongo_collection._validate_mongo_update(update)


########################################################################################
# insert_one()


@pytest.mark.asyncio
async def test_1000__insert_one(mongo_collection):
    """Test inserting one valid document."""
    doc = {"name": "Alice", "age": 30}
    mongo_collection._collection.insert_one = AsyncMock()
    result = await mongo_collection.insert_one(doc.copy())
    assert result == doc


@pytest.mark.asyncio
async def test_1001__insert_one__invalid_schema(mongo_collection):
    """Test inserting one document with invalid schema."""
    doc = {"name": "Alice"}
    with pytest.raises(MongoJSONSchemaValidationError):
        await mongo_collection.insert_one(doc)


########################################################################################
# insert_many()


@pytest.mark.asyncio
async def test_1100__insert_many(mongo_collection):
    """Test inserting multiple valid documents."""
    docs = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
    mongo_collection._collection.insert_many = AsyncMock()
    result = await mongo_collection.insert_many([doc.copy() for doc in docs])
    assert result == docs


@pytest.mark.asyncio
async def test_1101__insert_many__invalid_schema(mongo_collection):
    """Test inserting multiple documents with one invalid document raises error."""
    docs = [{"name": "Alice", "age": 30}, {"name": "Bob"}]
    with pytest.raises(MongoJSONSchemaValidationError):
        await mongo_collection.insert_many(docs)


########################################################################################
# find_one()


@pytest.mark.asyncio
async def test_1200__find_one(mongo_collection):
    """Test finding one document that exists."""
    mongo_collection._collection.find_one = AsyncMock(
        return_value={"_id": "123", "name": "Bob", "age": 40}
    )
    result = await mongo_collection.find_one({"name": "Bob"})
    assert result == {"name": "Bob", "age": 40}


@pytest.mark.asyncio
async def test_1201__find_one__not_found(mongo_collection):
    """Test finding one document that does not exist."""
    mongo_collection._collection.find_one = AsyncMock(return_value=None)
    with pytest.raises(DocumentNotFoundException):
        await mongo_collection.find_one({"name": "Bob"})


########################################################################################
# find_one_and_update()


@pytest.mark.asyncio
async def test_1300__find_one_and_update__set(mongo_collection):
    """Test updating and returning one document successfully with $set."""
    mongo_collection._collection.find_one_and_update = AsyncMock(
        return_value={"_id": "1", "name": "Updated", "age": 35}
    )
    result = await mongo_collection.find_one_and_update(
        {"name": "Alice"}, {"$set": {"age": 35}}
    )
    assert result == {"_id": "1", "name": "Updated", "age": 35}


@pytest.mark.asyncio
async def test_1301__find_one_and_update__set__invalid_schema(mongo_collection):
    """Test updating one document with invalid $set schema raises error."""
    update = {"$set": {"name": "Charlie"}}
    with pytest.raises(MongoJSONSchemaValidationError):
        await mongo_collection.find_one_and_update({"name": "Charlie"}, update)


@pytest.mark.asyncio
async def test_1310__find_one_and_update__push(mongo_collection):
    """Test updating one document successfully with $push."""
    mongo_collection._collection.find_one_and_update = AsyncMock(
        return_value={
            "_id": "2",
            "name": "Alice",
            "address": [{"city": "NY", "zip": "10001"}],
        }
    )
    update = {"$push": {"address": {"city": "NY", "zip": "10001"}}}
    result = await mongo_collection.find_one_and_update({"name": "Alice"}, update)
    assert result["address"][0]["city"] == "NY"


@pytest.mark.asyncio
async def test_1311__find_one_and_update__push__invalid_schema(mongo_collection):
    """Test updating one document with invalid $push schema raises error."""
    update = {"$push": {"address": "not-an-object"}}
    with pytest.raises(MongoJSONSchemaValidationError):
        await mongo_collection.find_one_and_update({"name": "Charlie"}, update)


@pytest.mark.asyncio
async def test_1390__find_one_and_update__unsupported_operator(mongo_collection):
    """Test updating with unsupported operator raises error."""
    with pytest.raises(KeyError):
        await mongo_collection.find_one_and_update(
            {"name": "Bob"}, {"$unset": {"age": ""}}
        )


########################################################################################
# update_many()


@pytest.mark.asyncio
async def test_1400__update_many(mongo_collection):
    """Test updating multiple documents successfully."""
    mock_res = MagicMock()
    mock_res.matched_count = 1
    mock_res.modified_count = 2
    mongo_collection._collection.update_many = AsyncMock(return_value=mock_res)
    modified = await mongo_collection.update_many(
        {"name": "Alice"}, {"$set": {"age": 31}}
    )
    assert modified == 2


@pytest.mark.asyncio
async def test_1401__update_many__not_found(mongo_collection):
    """Test updating multiple documents with no match raises error."""
    mock_res = MagicMock()
    mock_res.matched_count = 0
    mongo_collection._collection.update_many = AsyncMock(return_value=mock_res)
    with pytest.raises(DocumentNotFoundException):
        await mongo_collection.update_many({"name": "Bob"}, {"$set": {"age": 40}})


########################################################################################
# find_all()


@pytest.mark.asyncio
async def test_1500__find_all(mongo_collection):
    """Test finding all matching documents."""
    docs = [{"_id": 1, "name": "A", "age": 20}, {"_id": 2, "name": "B", "age": 25}]

    async def async_gen():
        for doc in docs:
            yield doc

    mongo_collection._collection.find = lambda *_args, **_kwargs: async_gen()
    results = [doc async for doc in mongo_collection.find_all({}, ["name", "age"])]
    assert results == [{"name": "A", "age": 20}, {"name": "B", "age": 25}]


########################################################################################
# aggregate()


@pytest.mark.asyncio
async def test_1600__aggregate(mongo_collection):
    """Test running an aggregation pipeline."""
    docs = [{"_id": "x", "name": "X"}, {"_id": "y", "name": "Y"}]

    async def async_gen():
        for doc in docs:
            yield doc

    mongo_collection._collection.aggregate = lambda *_args, **_kwargs: async_gen()
    results = [doc async for doc in mongo_collection.aggregate([{"$match": {}}])]
    assert results == [{"name": "X"}, {"name": "Y"}]


########################################################################################
# aggregate_one()


@pytest.mark.asyncio
async def test_1700__aggregate_one(mongo_collection):
    """Test finding one document using aggregation."""
    mongo_collection.aggregate = AsyncMock()
    mongo_collection.aggregate.return_value.__aiter__.return_value = [
        {"_id": "z", "name": "Z"}
    ]

    result = await mongo_collection.aggregate_one([{"$match": {"name": "Z"}}])
    assert result == {"name": "Z"}


@pytest.mark.asyncio
async def test_1701__aggregate_one__not_found(mongo_collection):
    """Test aggregation returns no document raises error."""
    mongo_collection.aggregate = AsyncMock()
    mongo_collection.aggregate.return_value.__aiter__.return_value = []

    with pytest.raises(DocumentNotFoundException):
        await mongo_collection.aggregate_one([{"$match": {"name": "None"}}])
