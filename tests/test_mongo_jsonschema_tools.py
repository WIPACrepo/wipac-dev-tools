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
def valid_coll(schema, mock_collection):
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


def test_0100__validate__valid_full_doc(valid_coll: MongoJSONSchemaValidatedCollection):
    """Test _validate with a fully valid document."""
    doc = {"name": "Alice", "age": 30}
    # Should not raise
    valid_coll._validate(doc)


def test_0101__validate__invalid_full_doc(
    valid_coll: MongoJSONSchemaValidatedCollection,
):
    """Test _validate with a full document missing required fields."""
    doc = {"name": "Bob"}  # missing "age"
    with pytest.raises(MongoJSONSchemaValidationError):
        valid_coll._validate(doc)


def test_0102__validate__valid_partial_doc(
    valid_coll: MongoJSONSchemaValidatedCollection,
):
    """Test _validate with valid dotted keys and partial update allowed."""
    doc = {"address.city": "Springfield", "address.zip": "12345"}
    # Should not raise
    valid_coll._validate(doc, allow_partial_update=True)


def test_0103__validate__invalid_partial_doc(
    valid_coll: MongoJSONSchemaValidatedCollection,
):
    """Test _validate with invalid partial doc missing required subfield."""
    doc = {"address.city": "Springfield"}  # missing zip
    with pytest.raises(MongoJSONSchemaValidationError):
        valid_coll._validate(doc, allow_partial_update=True)


def test_0104__validate__partial_doc_not_allowed(
    valid_coll: MongoJSONSchemaValidatedCollection,
):
    """Test _validate with dotted keys and partial updates disallowed raises error."""
    doc = {"address.city": "Springfield"}
    with pytest.raises(MongoJSONSchemaValidationError):
        valid_coll._validate(doc, allow_partial_update=False)


########################################################################################
# _validate_mongo_update()


def test_0200__validate_mongo_update__unsupported_operator(
    valid_coll: MongoJSONSchemaValidatedCollection,
):
    """Test _validate_mongo_update with unsupported operator raises error."""
    update = {"$rename": {"name": "full_name"}}
    with pytest.raises(KeyError):
        valid_coll._validate_mongo_update(update)


def test_0201__validate_mongo_update__set(
    valid_coll: MongoJSONSchemaValidatedCollection,
):
    """Test _validate_mongo_update with valid $set operator."""
    update = {"$set": {"name": "Alice", "age": 42}}
    valid_coll._validate_mongo_update(update)


def test_0202__validate_mongo_update__set_invalid(
    valid_coll: MongoJSONSchemaValidatedCollection,
):
    """Test _validate_mongo_update with invalid $set schema."""
    update = {"$set": {"name": "Bob"}}
    with pytest.raises(MongoJSONSchemaValidationError):
        valid_coll._validate_mongo_update(update)


def test_0203__validate_mongo_update__push(
    valid_coll: MongoJSONSchemaValidatedCollection,
):
    """Test _validate_mongo_update with valid $push operator."""
    update = {"$push": {"address": {"city": "Chicago", "zip": "60601"}}}
    valid_coll._validate_mongo_update(update)


def test_0204__validate_mongo_update__push_invalid(
    valid_coll: MongoJSONSchemaValidatedCollection,
):
    """Test _validate_mongo_update with invalid $push schema."""
    update = {"$push": {"address": {"city": "Chicago"}}}
    with pytest.raises(MongoJSONSchemaValidationError):
        valid_coll._validate_mongo_update(update)


########################################################################################
# insert_one()


@pytest.mark.asyncio
async def test_1000__insert_one_calls_validate_and_motor(
    valid_coll: MongoJSONSchemaValidatedCollection,
):
    """Test insert_one calls validation and insert_one, and removes _id."""
    doc = {"name": "Alice", "age": 30, "_id": "abc"}
    valid_coll._validate = MagicMock()  # type: ignore[method-assign]
    valid_coll._collection.insert_one = AsyncMock()

    result = await valid_coll.insert_one(doc.copy())

    valid_coll._validate.assert_called_once_with(doc)
    valid_coll._collection.insert_one.assert_called_once_with(doc)
    assert "_id" not in result
    assert result == {"name": "Alice", "age": 30}


########################################################################################
# insert_many()


@pytest.mark.asyncio
async def test_1100__insert_many_calls_validate_and_motor(
    valid_coll: MongoJSONSchemaValidatedCollection,
):
    """Test insert_many calls validation on each doc and strips _id."""
    docs = [
        {"name": "Alice", "age": 30, "_id": "abc"},
        {"name": "Bob", "age": 25, "_id": "def"},
    ]
    valid_coll._validate = MagicMock()  # type: ignore[method-assign]
    valid_coll._collection.insert_many = AsyncMock()

    result = await valid_coll.insert_many([doc.copy() for doc in docs])

    assert result == [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
    assert valid_coll._validate.call_count == 2
    valid_coll._collection.insert_many.assert_called_once_with(docs)


########################################################################################
# find_one()


@pytest.mark.asyncio
async def test_1200__find_one_removes_id_and_returns(
    valid_coll: MongoJSONSchemaValidatedCollection,
):
    """Test find_one removes _id and returns result."""
    valid_coll._collection.find_one = AsyncMock(
        return_value={"_id": "id", "name": "Alice", "age": 30}
    )

    result = await valid_coll.find_one({"name": "Alice"})

    valid_coll._collection.find_one.assert_called_once_with({"name": "Alice"})
    assert result == {"name": "Alice", "age": 30}


@pytest.mark.asyncio
async def test_1201__find_one_not_found_raises(
    valid_coll: MongoJSONSchemaValidatedCollection,
):
    """Test find_one raises DocumentNotFoundException when no document found."""
    valid_coll._collection.find_one = AsyncMock(return_value=None)

    with pytest.raises(DocumentNotFoundException):
        await valid_coll.find_one({"name": "Missing"})


########################################################################################
# find_one_and_update()


@pytest.mark.asyncio
async def test_1300__find_one_and_update_calls_validate_and_motor(
    valid_coll: MongoJSONSchemaValidatedCollection,
):
    """Test find_one_and_update calls validation and returns updated doc."""
    update = {"$set": {"age": 35}}
    result_doc = {"_id": "x", "name": "Updated", "age": 35}
    valid_coll._validate_mongo_update = MagicMock()  # type: ignore[method-assign]
    valid_coll._collection.find_one_and_update = AsyncMock(return_value=result_doc)

    result = await valid_coll.find_one_and_update({"name": "Alice"}, update)

    valid_coll._validate_mongo_update.assert_called_once_with(update)
    valid_coll._collection.find_one_and_update.assert_called_once()
    assert result == result_doc


@pytest.mark.asyncio
async def test_1301__find_one_and_update_not_found_raises(
    valid_coll: MongoJSONSchemaValidatedCollection,
):
    """Test find_one_and_update raises DocumentNotFoundException if not found."""
    valid_coll._validate_mongo_update = MagicMock()  # type: ignore[method-assign]
    valid_coll._collection.find_one_and_update = AsyncMock(return_value=None)

    with pytest.raises(DocumentNotFoundException):
        await valid_coll.find_one_and_update({"name": "Missing"}, {"$set": {"age": 35}})


########################################################################################
# update_many()


@pytest.mark.asyncio
async def test_1400__update_many_calls_validate_and_motor(
    valid_coll: MongoJSONSchemaValidatedCollection,
):
    """Test update_many calls validation and returns modified count."""
    mock_res = MagicMock(matched_count=1, modified_count=3)
    valid_coll._validate_mongo_update = MagicMock()  # type: ignore[method-assign]
    valid_coll._collection.update_many = AsyncMock(return_value=mock_res)

    count = await valid_coll.update_many({"active": True}, {"$set": {"age": 40}})

    valid_coll._validate_mongo_update.assert_called_once()
    valid_coll._collection.update_many.assert_called_once()
    assert count == 3


@pytest.mark.asyncio
async def test_1401__update_many_not_found_raises(
    valid_coll: MongoJSONSchemaValidatedCollection,
):
    """Test update_many raises DocumentNotFoundException if no documents matched."""
    valid_coll._validate_mongo_update = MagicMock()  # type: ignore[method-assign]
    valid_coll._collection.update_many = AsyncMock(
        return_value=MagicMock(matched_count=0)
    )

    with pytest.raises(DocumentNotFoundException):
        await valid_coll.update_many({"active": False}, {"$set": {"age": 40}})


########################################################################################
# find_all()


@pytest.mark.asyncio
async def test_1500__find_all_removes_id(
    valid_coll: MongoJSONSchemaValidatedCollection,
):
    """Test find_all yields documents without _id field."""
    docs = [{"_id": 1, "name": "A"}, {"_id": 2, "name": "B"}]

    async def async_gen():
        for doc in docs:
            yield doc

    valid_coll._collection.find = lambda *_args, **_kwargs: async_gen()

    results = [doc async for doc in valid_coll.find_all({}, ["name"])]
    assert results == [{"name": "A"}, {"name": "B"}]


########################################################################################
# aggregate()


@pytest.mark.asyncio
async def test_1600__aggregate_removes_id(
    valid_coll: MongoJSONSchemaValidatedCollection,
):
    """Test aggregate yields documents without _id field."""
    docs = [{"_id": 1, "val": "X"}, {"_id": 2, "val": "Y"}]

    async def async_gen():
        for doc in docs:
            yield doc

    valid_coll._collection.aggregate = lambda *_args, **_kwargs: async_gen()

    results = [doc async for doc in valid_coll.aggregate([{"$match": {}}])]
    assert results == [{"val": "X"}, {"val": "Y"}]


########################################################################################
# aggregate_one()


@pytest.mark.asyncio
async def test_1700__aggregate_one_returns_first_doc(
    valid_coll: MongoJSONSchemaValidatedCollection,
):
    """Test aggregate_one returns the first document."""
    valid_coll.aggregate = AsyncMock()  # type: ignore[method-assign]
    valid_coll.aggregate.return_value.__aiter__.return_value = [
        {"_id": 99, "result": "match"}
    ]

    result = await valid_coll.aggregate_one([{"$match": {"val": "match"}}])
    assert result == {"result": "match"}


@pytest.mark.asyncio
async def test_1701__aggregate_one_not_found_raises(
    valid_coll: MongoJSONSchemaValidatedCollection,
):
    """Test aggregate_one raises DocumentNotFoundException if empty."""
    valid_coll.aggregate = AsyncMock()  # type: ignore[method-assign]
    valid_coll.aggregate.return_value.__aiter__.return_value = []

    with pytest.raises(DocumentNotFoundException):
        await valid_coll.aggregate_one([{"$match": {"val": "none"}}])
