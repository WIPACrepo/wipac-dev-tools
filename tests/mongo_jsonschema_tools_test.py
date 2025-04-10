"""Tests for mongo_jsonschema_tools.py."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import jsonschema
import pytest

from wipac_dev_tools.mongo_jsonschema_tools import (
    DocumentNotFoundException,
    IllegalDotsNotationActionException,
    MongoJSONSchemaValidatedCollection,
    _convert_mongo_to_jsonschema,
)

ValidationError = jsonschema.exceptions.ValidationError


def make_coll(schema: dict) -> MongoJSONSchemaValidatedCollection:
    with patch("motor.motor_asyncio.AsyncIOMotorCollection"):
        return MongoJSONSchemaValidatedCollection(
            collection=AsyncMock(),
            collection_jsonschema_spec=schema,
            parent_logger=logging.getLogger("test_logger"),
        )


@pytest.fixture
def bio_schema():
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
def bio_coll(bio_schema) -> MongoJSONSchemaValidatedCollection:
    return make_coll(bio_schema)


@pytest.fixture
def team_schema():
    return {
        "type": "object",
        "properties": {
            "team": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "position": {"type": "string"},
                        "number": {"type": "integer"},
                    },
                    "required": ["name", "position", "number"],
                },
            }
        },
        "required": ["team"],
    }


########################################################################################
# _convert_mongo_to_jsonschema()


def test_0000__convert_no_dots_no_partial_returns_as_is(bio_schema):
    """Test conversion passes through doc and schema as-is if no dotted keys."""
    doc = {"name": "Charlie", "age": 28}
    out_doc, out_schema = _convert_mongo_to_jsonschema(
        doc, bio_schema, allow_partial_update=False
    )
    assert out_doc == doc
    assert out_schema == bio_schema


def test_0001__convert_with_dots_no_partial_raises(bio_schema):
    """Test conversion with dotted keys and no partial update raises error."""
    doc = {"address.city": "Springfield"}
    with pytest.raises(IllegalDotsNotationActionException):
        _convert_mongo_to_jsonschema(doc, bio_schema, allow_partial_update=False)


def test_0002__convert_with_dots_and_partial_succeeds(bio_schema):
    """Test conversion with dotted keys and partial update flattens and validates."""
    doc = {"address.city": "Metropolis"}
    out_doc, out_schema = _convert_mongo_to_jsonschema(
        doc, bio_schema, allow_partial_update=True
    )
    assert out_doc == {"address": {"city": "Metropolis"}}
    assert out_schema["required"] == []
    assert out_schema["properties"]["address"]["required"] == []


########################################################################################
# _convert_mongo_to_jsonschema() - schema edge cases


def test_0003__convert_with_additional_properties_and_partial():
    """Test conversion allows additionalProperties in partial update."""
    schema = {
        "type": "object",
        "properties": {},
        "additionalProperties": True,
    }
    doc = {"custom.field": "yes"}
    out_doc, out_schema = _convert_mongo_to_jsonschema(
        doc, schema, allow_partial_update=True
    )
    assert out_doc == {"custom": {"field": "yes"}}
    assert out_schema["required"] == []


def test_0004__convert_with_nested_additional_properties_blocked__but_ok():
    """Test partial update fails if nested object blocks additionalProperties."""
    schema = {
        "type": "object",
        "properties": {
            "meta": {
                "type": "object",
                "properties": {"id": {"type": "string"}},
                "additionalProperties": False,
            }
        },
        "required": ["meta"],
    }
    doc = {"meta.extra": "boom"}
    out_doc, out_schema = _convert_mongo_to_jsonschema(
        doc, schema, allow_partial_update=True
    )
    assert out_doc == {"meta": {"extra": "boom"}}
    assert out_schema["properties"]["meta"]["additionalProperties"] is False
    assert out_schema["required"] == []

    # NOTE: the above doc is invalid for jsonschema--but, it's not invalid for conversion
    #
    # see...
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(out_doc, out_schema)


########################################################################################
# _validate()


def test_0100__validate__valid_full_doc(bio_coll: MongoJSONSchemaValidatedCollection):
    """Test _validate with a fully valid document."""
    doc = {"name": "Alice", "age": 30}
    # Should not raise
    bio_coll._validate(doc)


def test_0101__validate__invalid_full_doc(
    bio_coll: MongoJSONSchemaValidatedCollection,
):
    """Test _validate with a full document missing required fields."""
    doc = {"name": "Bob"}  # missing "age"
    with pytest.raises(ValidationError):
        bio_coll._validate(doc)


def test_0102__validate__valid_partial_doc(
    bio_coll: MongoJSONSchemaValidatedCollection,
):
    """Test _validate with valid dotted keys and partial update allowed."""
    doc = {"address.city": "Springfield", "address.zip": "12345"}
    # Should not raise
    bio_coll._validate(doc, allow_partial_update=True)


def test_0103__validate__invalid_partial_doc(
    bio_coll: MongoJSONSchemaValidatedCollection,
):
    """Partial update skips subfield requirements; this should succeed."""
    doc = {"address.city": "Springfield"}  # missing zip
    bio_coll._validate(doc, allow_partial_update=True)


def test_0104__validate__partial_doc_not_allowed(
    bio_coll: MongoJSONSchemaValidatedCollection,
):
    """Test _validate with dotted keys and partial updates disallowed raises error."""
    doc = {"address.city": "Springfield"}
    with pytest.raises(IllegalDotsNotationActionException):
        bio_coll._validate(doc, allow_partial_update=False)


########################################################################################
# _validate() - schema edge cases


def test_0105__validate__additional_properties_rejected():
    """Test _validate fails when unexpected extra fields are present."""
    schema = {
        "type": "object",
        "properties": {"foo": {"type": "string"}},
        "additionalProperties": False,
        "required": ["foo"],
    }
    coll = make_coll(schema)
    with pytest.raises(ValidationError):
        coll._validate({"foo": "bar", "extra": "nope"})


def test_0106__validate__nested_object_missing_subfield():
    """Test _validate fails when nested required subfield is missing."""
    schema = {
        "type": "object",
        "properties": {
            "settings": {
                "type": "object",
                "properties": {"enabled": {"type": "boolean"}},
                "required": ["enabled"],
            }
        },
        "required": ["settings"],
    }
    coll = make_coll(schema)
    with pytest.raises(ValidationError):
        coll._validate({"settings": {}})


def test_0107__validate__array_type_enforced():
    """Test _validate fails when array item type is wrong."""
    schema = {
        "type": "object",
        "properties": {
            "tags": {
                "type": "array",
                "items": {"type": "string"},
            }
        },
        "required": ["tags"],
    }
    coll = make_coll(schema)
    with pytest.raises(ValidationError):
        coll._validate({"tags": [1, 2, 3]})


def test_0108__validate__enum_enforced():
    """Test _validate fails if enum value not allowed."""
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["new", "done"]},
        },
        "required": ["status"],
    }
    coll = make_coll(schema)
    with pytest.raises(ValidationError):
        coll._validate({"status": "archived"})


def test_0109__validate__one_of_match_success():
    """Test _validate succeeds with a valid oneOf branch."""
    schema = {
        "type": "object",
        "properties": {
            "input": {
                "oneOf": [
                    {"type": "string"},
                    {"type": "number"},
                ]
            }
        },
        "required": ["input"],
    }
    coll = make_coll(schema)
    coll._validate({"input": 42})  # Should succeed


def test_0110__validate__one_of_match_failure():
    """Test _validate fails when oneOf has no match."""
    schema = {
        "type": "object",
        "properties": {
            "input": {
                "oneOf": [
                    {"type": "string"},
                    {"type": "number"},
                ]
            }
        },
        "required": ["input"],
    }
    coll = make_coll(schema)
    with pytest.raises(ValidationError):
        coll._validate({"input": {"foo": "bar"}})


def test_0111__validate__partial_update_with_enum_valid():
    """Test _validate succeeds on partial update with enum."""
    schema = {
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": ["A", "B", "C"]},
        },
        "required": ["type"],
    }
    coll = make_coll(schema)
    coll._validate({"type": "B"}, allow_partial_update=True)


def test_0112__validate__partial_update_with_enum_invalid():
    """Test _validate fails on partial update with invalid enum value."""
    schema = {
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": ["A", "B", "C"]},
        },
        "required": ["type"],
    }
    coll = make_coll(schema)
    with pytest.raises(ValidationError):
        coll._validate({"type": "Z"}, allow_partial_update=True)


def test_0113__validate__type_mismatch_raises():
    """Test _validate fails on type mismatch."""
    schema = {
        "type": "object",
        "properties": {"count": {"type": "integer"}},
        "required": ["count"],
    }
    coll = make_coll(schema)
    with pytest.raises(ValidationError):
        coll._validate({"count": "ten"})


def test_0114__validate__object_with_optional_field():
    """Test _validate accepts missing optional field."""
    schema = {
        "type": "object",
        "properties": {
            "foo": {"type": "string"},
            "bar": {"type": "integer"},
        },
        "required": ["foo"],
    }
    coll = make_coll(schema)
    coll._validate({"foo": "hello"})  # bar is optional


def test_0115__validate__deep_nested_dotted_update_succeeds():
    """Test dotted key partial update on deep nested fields succeeds."""
    schema = {
        "type": "object",
        "properties": {
            "a": {
                "type": "object",
                "properties": {
                    "b": {
                        "type": "object",
                        "properties": {"c": {"type": "string"}},
                        "required": ["c"],
                    }
                },
                "required": ["b"],
            }
        },
        "required": ["a"],
    }
    coll = make_coll(schema)
    coll._validate({"a.b.c": "xyz"}, allow_partial_update=True)


########################################################################################
# _validate_mongo_update()


def test_0200__validate_mongo_update__unsupported_operator(
    bio_coll: MongoJSONSchemaValidatedCollection,
):
    """Test _validate_mongo_update with unsupported operator raises error."""
    update = {"$rename": {"name": "full_name"}}
    with pytest.raises(KeyError):
        bio_coll._validate_mongo_update(update)


def test_0201__validate_mongo_update__set(
    bio_coll: MongoJSONSchemaValidatedCollection,
):
    """Test _validate_mongo_update with valid $set operator."""
    update = {"$set": {"name": "Alice", "age": 42}}
    bio_coll._validate_mongo_update(update)


def test_0202__validate_mongo_update__set_invalid(
    bio_coll: MongoJSONSchemaValidatedCollection,
):
    """Invalid value in $set (wrong type) should raise error."""
    update = {"$set": {"age": "not-a-number"}}  # age must be integer
    with pytest.raises(ValidationError):
        bio_coll._validate_mongo_update(update)


def test_0203__validate_mongo_update__push_baseball(team_schema):
    """Test _validate_mongo_update with valid $push operator using baseball theme."""
    coll = make_coll(team_schema)
    update = {"$push": {"team": {"name": "Jack", "position": "Pitcher", "number": 42}}}
    coll._validate_mongo_update(update)


def test_0204__validate_mongo_update__push_baseball_invalid(team_schema):
    """Test _validate_mongo_update with invalid $push operator using baseball theme."""
    coll = make_coll(team_schema)
    update = {"$push": {"team": {"name": "Jack", "position": "Catcher"}}}  # no number
    with pytest.raises(ValidationError):
        coll._validate_mongo_update(update)


########################################################################################
# insert_one()


@pytest.mark.asyncio
async def test_1000__insert_one_calls_validate_and_motor(
    bio_coll: MongoJSONSchemaValidatedCollection,
):
    """Test insert_one calls validation and insert_one."""
    doc = {"name": "Alice", "age": 30}
    bio_coll._validate = MagicMock()  # type: ignore[method-assign]
    bio_coll._collection.insert_one = AsyncMock()  # type: ignore[method-assign]

    result = await bio_coll.insert_one(doc.copy())

    # check calls & result
    bio_coll._validate.assert_called_once_with(doc)
    bio_coll._collection.insert_one.assert_called_once_with(doc)
    assert result == doc


########################################################################################
# insert_many()


@pytest.mark.asyncio
async def test_1100__insert_many_calls_validate_and_motor(
    bio_coll: MongoJSONSchemaValidatedCollection,
):
    """Test insert_many calls validation on each doc."""
    docs = [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
    ]
    bio_coll._validate = MagicMock()  # type: ignore[method-assign]
    bio_coll._collection.insert_many = AsyncMock()  # type: ignore[method-assign]

    result = await bio_coll.insert_many([doc.copy() for doc in docs])

    # check calls & result
    assert result == docs
    assert bio_coll._validate.call_count == 2
    bio_coll._collection.insert_many.assert_called_once_with(docs)


########################################################################################
# find_one()


@pytest.mark.asyncio
async def test_1200__find_one_removes_id_and_returns(
    bio_coll: MongoJSONSchemaValidatedCollection,
):
    """Test find_one removes _id and returns result."""
    bio_coll._collection.find_one = AsyncMock(  # type: ignore[method-assign]
        return_value={"_id": "id", "name": "Alice", "age": 30}
    )

    result = await bio_coll.find_one({"name": "Alice"})

    # check calls & result
    bio_coll._collection.find_one.assert_called_once_with({"name": "Alice"})
    assert result == {"name": "Alice", "age": 30}


@pytest.mark.asyncio
async def test_1201__find_one_not_found_raises(
    bio_coll: MongoJSONSchemaValidatedCollection,
):
    """Test find_one raises DocumentNotFoundException when no document found."""
    bio_coll._collection.find_one = AsyncMock(return_value=None)  # type: ignore[method-assign]

    with pytest.raises(DocumentNotFoundException):
        await bio_coll.find_one({"name": "Missing"})


########################################################################################
# find_one_and_update()


@pytest.mark.asyncio
async def test_1300__find_one_and_update_calls_validate_and_motor(
    bio_coll: MongoJSONSchemaValidatedCollection,
):
    """Test find_one_and_update calls validation and returns updated doc."""
    update = {"$set": {"age": 35}}
    result_doc = {"_id": "x", "name": "Updated", "age": 35}
    bio_coll._validate_mongo_update = MagicMock()  # type: ignore[method-assign]
    bio_coll._collection.find_one_and_update = AsyncMock(return_value=result_doc)  # type: ignore[method-assign]

    result = await bio_coll.find_one_and_update({"name": "Alice"}, update)

    # check calls & result
    bio_coll._validate_mongo_update.assert_called_once_with(update)
    bio_coll._collection.find_one_and_update.assert_called_once_with(
        {"name": "Alice"},
        update,
        return_document=bio_coll._collection.find_one_and_update.call_args.kwargs[
            "return_document"
        ],
    )
    assert result == result_doc


@pytest.mark.asyncio
async def test_1301__find_one_and_update_not_found_raises(
    bio_coll: MongoJSONSchemaValidatedCollection,
):
    """Test find_one_and_update raises DocumentNotFoundException if not found."""
    bio_coll._validate_mongo_update = MagicMock()  # type: ignore[method-assign]
    bio_coll._collection.find_one_and_update = AsyncMock(return_value=None)  # type: ignore[method-assign]

    with pytest.raises(DocumentNotFoundException):
        await bio_coll.find_one_and_update({"name": "Missing"}, {"$set": {"age": 35}})


########################################################################################
# update_many()


@pytest.mark.asyncio
async def test_1400__update_many_calls_validate_and_motor(
    bio_coll: MongoJSONSchemaValidatedCollection,
):
    """Test update_many calls validation and returns modified count."""
    mock_res = MagicMock(matched_count=1, modified_count=3)
    bio_coll._validate_mongo_update = MagicMock()  # type: ignore[method-assign]
    bio_coll._collection.update_many = AsyncMock(return_value=mock_res)  # type: ignore[method-assign]

    count = await bio_coll.update_many({"active": True}, {"$set": {"age": 40}})

    # check calls & result
    bio_coll._validate_mongo_update.assert_called_once_with({"$set": {"age": 40}})
    bio_coll._collection.update_many.assert_called_once_with(
        {"active": True}, {"$set": {"age": 40}}
    )
    assert count == 3


@pytest.mark.asyncio
async def test_1401__update_many_not_found_raises(
    bio_coll: MongoJSONSchemaValidatedCollection,
):
    """Test update_many raises DocumentNotFoundException if no documents matched."""
    bio_coll._validate_mongo_update = MagicMock()  # type: ignore[method-assign]
    bio_coll._collection.update_many = AsyncMock(  # type: ignore[method-assign]
        return_value=MagicMock(matched_count=0)
    )

    with pytest.raises(DocumentNotFoundException):
        await bio_coll.update_many({"active": False}, {"$set": {"age": 40}})


########################################################################################
# find_all()


@pytest.mark.asyncio
async def test_1500__find_all_removes_id(
    bio_coll: MongoJSONSchemaValidatedCollection,
):
    """Test find_all yields documents without _id field."""
    docs = [{"_id": 1, "name": "A"}, {"_id": 2, "name": "B"}]

    async def async_gen():
        for doc in docs:
            yield doc

    bio_coll._collection.find = lambda *_args, **_kwargs: async_gen()  # type: ignore[method-assign]

    # check calls & result
    results = [doc async for doc in bio_coll.find_all({}, ["name"])]
    assert results == [{"name": "A"}, {"name": "B"}]


########################################################################################
# aggregate()


@pytest.mark.asyncio
async def test_1600__aggregate_removes_id(
    bio_coll: MongoJSONSchemaValidatedCollection,
):
    """Test aggregate yields documents without _id field."""
    docs = [{"_id": 1, "val": "X"}, {"_id": 2, "val": "Y"}]

    async def async_gen():
        for doc in docs:
            yield doc

    bio_coll._collection.aggregate = lambda *_args, **_kwargs: async_gen()  # type: ignore[method-assign]

    # check calls & result
    results = [doc async for doc in bio_coll.aggregate([{"$match": {}}])]
    assert results == [{"val": "X"}, {"val": "Y"}]


########################################################################################
# aggregate_one()


@pytest.mark.asyncio
async def test_1700__aggregate_one_returns_first_doc(
    bio_coll: MongoJSONSchemaValidatedCollection,
):
    """Test aggregate_one returns the first document."""
    docs = [{"_id": 1, "val": "X"}, {"_id": 2, "val": "Y"}]

    async def async_gen():
        for doc in docs:
            yield doc

    bio_coll._collection.aggregate = MagicMock(return_value=async_gen())  # type: ignore[method-assign]

    pipeline = [{"$match": {}}]  # type: ignore[var-annotated]
    result = await bio_coll.aggregate_one(pipeline.copy())

    # check calls & result
    bio_coll._collection.aggregate.assert_called_once_with(pipeline + [{"$limit": 1}])
    assert result in [{"val": "X"}, {"val": "Y"}]


@pytest.mark.asyncio
async def test_1701__aggregate_one_not_found_raises(
    bio_coll: MongoJSONSchemaValidatedCollection,
):
    """Test aggregate_one raises DocumentNotFoundException if empty."""

    async def async_gen():
        for _ in []:  # hack for empty async iter
            yield

    bio_coll._collection.aggregate = MagicMock(return_value=async_gen())  # type: ignore[method-assign]

    pipeline = [{"$match": {"val": "none"}}]
    with pytest.raises(DocumentNotFoundException):
        await bio_coll.aggregate_one(pipeline.copy())

    # check calls
    bio_coll._collection.aggregate.assert_called_once_with(pipeline + [{"$limit": 1}])
