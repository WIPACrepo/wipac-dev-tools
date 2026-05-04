"""Integration tests for mongo_jsonschema_tools.py.

Runs against a real MongoDB instance. Connection URL is taken from the
MONGO_URL env var (default: mongodb://localhost:27017).

Skipped by default unless `-m integration` is passed (or unmarked default
config picks them up). Run locally with:
    docker run --rm -p 27017:27017 mongo:7
    pytest -m integration tests/mongo_jsonschema_tools_integration_test.py

Focus areas:
    - Wiring: kwargs/return shapes between wrapper and pymongo (mocks miss this).
    - Each supported $-operator end-to-end against real mongo.
    - DocumentNotFoundException semantics on real misses.
"""

import logging
import os
import uuid

import pytest
import pytest_asyncio
from pymongo import AsyncMongoClient
from wipac_dev_tools.mongo_jsonschema_tools import (
    DocumentNotFoundException,
    MongoJSONSchemaValidatedCollection,
)

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")

# all tests in this file are integration tests
pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


########################################################################################
# fixtures


@pytest_asyncio.fixture
async def mongo_client():
    """Yield a fresh AsyncMongoClient for the test."""
    client = AsyncMongoClient(MONGO_URL)
    try:
        yield client
    finally:
        await client.close()


@pytest_asyncio.fixture
async def raw_collection(mongo_client):
    """Yield an isolated AsyncCollection per test, then drop it."""
    db = mongo_client["wdt_integration_test"]
    # unique name per test -> no cross-test contamination if drop fails
    coll = db[f"coll_{uuid.uuid4().hex}"]
    yield coll
    await coll.drop()


@pytest.fixture
def stadium_schema():
    """Schema for baseball stadium docs used across most integration tests."""
    return {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "capacity": {"type": "integer"},
            "attendance_avg": {"type": "number"},
            "concessions": {"type": "array", "items": {"type": "string"}},
            "location": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "state": {"type": "string"},
                },
                "required": ["city", "state"],
            },
        },
        "required": ["name", "capacity"],
    }


@pytest_asyncio.fixture
async def stadium_coll(raw_collection, stadium_schema):
    """Yield a MongoJSONSchemaValidatedCollection over a fresh raw collection."""
    return MongoJSONSchemaValidatedCollection(
        collection=raw_collection,
        collection_jsonschema_spec=stadium_schema,
        parent_logger=logging.getLogger("integration_test"),
    )


########################################################################################
# insert_one() / find_one() -- round trip


async def test_2000__insert_then_find(
    stadium_coll: MongoJSONSchemaValidatedCollection,
):
    """Round-trip a doc through insert_one + find_one."""
    await stadium_coll.insert_one({"name": "Miller Park", "capacity": 41000})

    found = await stadium_coll.find_one({"name": "Miller Park"})
    assert found == {"name": "Miller Park", "capacity": 41000}


async def test_2001__find_one_missing_raises(
    stadium_coll: MongoJSONSchemaValidatedCollection,
):
    """find_one raises DocumentNotFoundException when no doc matches."""
    with pytest.raises(DocumentNotFoundException):
        await stadium_coll.find_one({"name": "Nonexistent Park"})


async def test_2002__insert_many_round_trip(
    stadium_coll: MongoJSONSchemaValidatedCollection,
):
    """insert_many then find_all yields all docs."""
    docs = [
        {"name": "Miller Park", "capacity": 41000},
        {"name": "Wrigley Field", "capacity": 37000},
        {"name": "Chase Field", "capacity": 47000},
    ]
    await stadium_coll.insert_many([d.copy() for d in docs])

    out = sorted(
        [doc async for doc in stadium_coll.find_all({}, ["name", "capacity"])],
        key=lambda d: d["name"],
    )
    assert out == sorted(docs, key=lambda d: d["name"])


########################################################################################
# find_one_and_update() -- one test per supported $-operator


async def test_2100__set(stadium_coll: MongoJSONSchemaValidatedCollection):
    """$set updates the field and returns the AFTER doc."""
    await stadium_coll.insert_one({"name": "Miller Park", "capacity": 41000})
    out = await stadium_coll.find_one_and_update(
        {"name": "Miller Park"}, {"$set": {"capacity": 41649}}
    )
    assert out["capacity"] == 41649


async def test_2101__set_on_insert_with_upsert(
    stadium_coll: MongoJSONSchemaValidatedCollection,
):
    """$setOnInsert applies only when upsert creates a new doc."""
    # upsert creates new -> setOnInsert applies
    out = await stadium_coll.find_one_and_update(
        {"name": "Brand New Park"},
        {"$setOnInsert": {"name": "Brand New Park", "capacity": 1}},
        upsert=True,
    )
    assert out["capacity"] == 1

    # second call against existing doc -> setOnInsert is a no-op
    out2 = await stadium_coll.find_one_and_update(
        {"name": "Brand New Park"},
        {"$setOnInsert": {"capacity": 99999}},
        upsert=True,
    )
    assert out2["capacity"] == 1  # unchanged


async def test_2102__inc(stadium_coll: MongoJSONSchemaValidatedCollection):
    """$inc increments the field by the given delta."""
    await stadium_coll.insert_one({"name": "Miller Park", "capacity": 10000})
    out = await stadium_coll.find_one_and_update(
        {"name": "Miller Park"}, {"$inc": {"capacity": 5}}
    )
    assert out["capacity"] == 10005


async def test_2103__min_lowers_value(
    stadium_coll: MongoJSONSchemaValidatedCollection,
):
    """$min keeps the smaller of {existing, supplied}."""
    await stadium_coll.insert_one({"name": "Miller Park", "capacity": 10000})

    # 5000 < 10000 -> updates to 5000
    out = await stadium_coll.find_one_and_update(
        {"name": "Miller Park"}, {"$min": {"capacity": 5000}}
    )
    assert out["capacity"] == 5000

    # 7000 > 5000 -> stays at 5000
    out = await stadium_coll.find_one_and_update(
        {"name": "Miller Park"}, {"$min": {"capacity": 7000}}
    )
    assert out["capacity"] == 5000


async def test_2104__max_raises_value(
    stadium_coll: MongoJSONSchemaValidatedCollection,
):
    """$max keeps the larger of {existing, supplied}."""
    await stadium_coll.insert_one({"name": "Miller Park", "capacity": 10000})

    # 50000 > 10000 -> updates to 50000
    out = await stadium_coll.find_one_and_update(
        {"name": "Miller Park"}, {"$max": {"capacity": 50000}}
    )
    assert out["capacity"] == 50000

    # 5000 < 50000 -> stays at 50000
    out = await stadium_coll.find_one_and_update(
        {"name": "Miller Park"}, {"$max": {"capacity": 5000}}
    )
    assert out["capacity"] == 50000


async def test_2105__mul(stadium_coll: MongoJSONSchemaValidatedCollection):
    """$mul multiplies the field by the given factor."""
    await stadium_coll.insert_one(
        {"name": "Miller Park", "capacity": 10000, "attendance_avg": 25000.0}
    )
    out = await stadium_coll.find_one_and_update(
        {"name": "Miller Park"}, {"$mul": {"attendance_avg": 2}}
    )
    assert out["attendance_avg"] == 50000.0  # 25000 * 2


async def test_2106__push(stadium_coll: MongoJSONSchemaValidatedCollection):
    """$push appends to the array."""
    await stadium_coll.insert_one(
        {"name": "Miller Park", "capacity": 10000, "concessions": ["brat"]}
    )
    out = await stadium_coll.find_one_and_update(
        {"name": "Miller Park"}, {"$push": {"concessions": "pretzels"}}
    )
    assert out["concessions"] == ["brat", "pretzels"]


async def test_2107__add_to_set_dedups(
    stadium_coll: MongoJSONSchemaValidatedCollection,
):
    """$addToSet appends only if the value isn't already present."""
    await stadium_coll.insert_one(
        {"name": "Miller Park", "capacity": 10000, "concessions": ["brat"]}
    )

    # new value -> appended
    out = await stadium_coll.find_one_and_update(
        {"name": "Miller Park"}, {"$addToSet": {"concessions": "pretzels"}}
    )
    assert out["concessions"] == ["brat", "pretzels"]

    # duplicate -> ignored
    out = await stadium_coll.find_one_and_update(
        {"name": "Miller Park"}, {"$addToSet": {"concessions": "pretzels"}}
    )
    assert out["concessions"] == ["brat", "pretzels"]


async def test_2108__pop_last(stadium_coll: MongoJSONSchemaValidatedCollection):
    """$pop with 1 removes the last element."""
    await stadium_coll.insert_one(
        {
            "name": "Miller Park",
            "capacity": 10000,
            "concessions": ["brat", "pretzels", "beer"],
        }
    )
    out = await stadium_coll.find_one_and_update(
        {"name": "Miller Park"}, {"$pop": {"concessions": 1}}
    )
    assert out["concessions"] == ["brat", "pretzels"]


async def test_2109__pop_first(stadium_coll: MongoJSONSchemaValidatedCollection):
    """$pop with -1 removes the first element."""
    await stadium_coll.insert_one(
        {
            "name": "Miller Park",
            "capacity": 10000,
            "concessions": ["brat", "pretzels", "beer"],
        }
    )
    out = await stadium_coll.find_one_and_update(
        {"name": "Miller Park"}, {"$pop": {"concessions": -1}}
    )
    assert out["concessions"] == ["pretzels", "beer"]


async def test_2110__pull(stadium_coll: MongoJSONSchemaValidatedCollection):
    """$pull removes ALL elements matching the value."""
    await stadium_coll.insert_one(
        {
            "name": "Miller Park",
            "capacity": 10000,
            # duplicate brat entries to verify $pull removes every match
            "concessions": ["brat", "pretzels", "brat", "beer"],
        }
    )
    out = await stadium_coll.find_one_and_update(
        {"name": "Miller Park"}, {"$pull": {"concessions": "brat"}}
    )
    assert out["concessions"] == ["pretzels", "beer"]


async def test_2111__pull_all(stadium_coll: MongoJSONSchemaValidatedCollection):
    """$pullAll removes any element matching any in the supplied list."""
    await stadium_coll.insert_one(
        {
            "name": "Miller Park",
            "capacity": 10000,
            "concessions": ["brat", "pretzels", "beer", "popcorn"],
        }
    )
    out = await stadium_coll.find_one_and_update(
        {"name": "Miller Park"},
        {"$pullAll": {"concessions": ["brat", "popcorn"]}},
    )
    assert out["concessions"] == ["pretzels", "beer"]


async def test_2120__find_one_and_update_missing_raises(
    stadium_coll: MongoJSONSchemaValidatedCollection,
):
    """find_one_and_update raises when no match (and upsert is off)."""
    with pytest.raises(DocumentNotFoundException):
        await stadium_coll.find_one_and_update(
            {"name": "Ghost Park"}, {"$set": {"capacity": 99}}
        )


async def test_2121__set_with_dotted_partial_preserves_siblings(
    stadium_coll: MongoJSONSchemaValidatedCollection,
):
    """$set with dotted keys updates nested fields without overwriting siblings."""
    await stadium_coll.insert_one(
        {
            "name": "Miller Park",
            "capacity": 41000,
            "location": {"city": "Milwaukee", "state": "WI"},
        }
    )
    # update only the city; state should be preserved
    out = await stadium_coll.find_one_and_update(
        {"name": "Miller Park"}, {"$set": {"location.city": "Madison"}}
    )
    assert out["location"] == {"city": "Madison", "state": "WI"}


########################################################################################
# update_many()


async def test_2200__update_many_inc(
    stadium_coll: MongoJSONSchemaValidatedCollection,
):
    """update_many applies $inc to every matching doc."""
    await stadium_coll.insert_many(
        [
            {"name": "Miller Park", "capacity": 10000},
            {"name": "Wrigley Field", "capacity": 20000},
            {"name": "Chase Field", "capacity": 30000},
        ]
    )

    n = await stadium_coll.update_many({}, {"$inc": {"capacity": 1}})
    assert n == 3

    out = sorted(
        [doc async for doc in stadium_coll.find_all({}, ["capacity"])],
        key=lambda d: d["capacity"],
    )
    assert [d["capacity"] for d in out] == [10001, 20001, 30001]


async def test_2201__update_many_no_match_raises(
    stadium_coll: MongoJSONSchemaValidatedCollection,
):
    """update_many raises when no doc matches."""
    with pytest.raises(DocumentNotFoundException):
        await stadium_coll.update_many({"name": "ghost"}, {"$set": {"capacity": 1}})


########################################################################################
# find_all() / aggregate() / aggregate_one()


async def test_2300__find_all_with_projection(
    stadium_coll: MongoJSONSchemaValidatedCollection,
):
    """find_all yields docs with the projection applied (and _id stripped)."""
    await stadium_coll.insert_many(
        [
            {"name": "Miller Park", "capacity": 10000},
            {"name": "Wrigley Field", "capacity": 20000},
        ]
    )
    out = sorted(
        [doc async for doc in stadium_coll.find_all({}, {"name": 1, "_id": 0})],
        key=lambda d: d["name"],
    )
    # _id stripped, capacity not projected
    assert out == [{"name": "Miller Park"}, {"name": "Wrigley Field"}]


async def test_2301__aggregate_match_and_project(
    stadium_coll: MongoJSONSchemaValidatedCollection,
):
    """aggregate runs through the wrapper and yields filtered/projected docs."""
    await stadium_coll.insert_many(
        [
            {"name": "Miller Park", "capacity": 10000},
            {"name": "Wrigley Field", "capacity": 20000},
        ]
    )
    out = [
        doc
        async for doc in stadium_coll.aggregate(
            [
                {"$match": {"capacity": {"$gte": 15000}}},
                {"$project": {"_id": 0, "name": 1}},
            ]
        )
    ]
    assert out == [{"name": "Wrigley Field"}]


async def test_2302__aggregate_one_returns_first(
    stadium_coll: MongoJSONSchemaValidatedCollection,
):
    """aggregate_one returns the first matching doc and appends $limit:1."""
    await stadium_coll.insert_many(
        [
            {"name": "Miller Park", "capacity": 10000},
            {"name": "Wrigley Field", "capacity": 20000},
        ]
    )
    out = await stadium_coll.aggregate_one([{"$match": {}}, {"$sort": {"capacity": 1}}])
    # smallest-capacity-first sort -> Miller (10000 < 20000)
    assert out["name"] == "Miller Park"


async def test_2303__aggregate_one_missing_raises(
    stadium_coll: MongoJSONSchemaValidatedCollection,
):
    """aggregate_one raises DocumentNotFoundException on no match."""
    with pytest.raises(DocumentNotFoundException):
        await stadium_coll.aggregate_one([{"$match": {"name": "ghost"}}])
