"""Tools for interfacing with mongodb using jsonschema validation."""

import copy
import logging
from typing import Any, AsyncIterator

# mongo imports
try:
    from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
    from pymongo import ReturnDocument
except (ImportError, ModuleNotFoundError) as e:
    raise ImportError(
        "the 'mongo' option must be installed in order to use 'mongo_jsonschema_tools'"
    ) from e

# web imports
try:
    from tornado import web
except (ImportError, ModuleNotFoundError) as e:
    raise ImportError(
        "the 'web' option must be installed in order to use 'mongo_jsonschema_tools'"
    ) from e

# jsonschema imports
try:
    import jsonschema
except (ImportError, ModuleNotFoundError) as e:
    raise ImportError(
        "the 'jsonschema' option must be installed in order to use 'mongo_jsonschema_tools'"
    ) from e


class DocumentNotFoundException(Exception):
    """Raised when document is not found for a particular query."""


class MongoValidatedCollection:
    """For interacting with a mongo collection using jsonschema validation."""

    def __init__(
        self,
        mongo_client: AsyncIOMotorClient,  # type: ignore[valid-type]
        database_name: str,
        collection_name: str,
        collection_jsonschema_spec: dict[str, Any],
        raise_web_errors: bool = False,
        parent_logger: logging.Logger | None = None,
    ) -> None:
        self._collection = AsyncIOMotorCollection(  # type: ignore[var-annotated]
            mongo_client[database_name],  # type: ignore[arg-type]
            collection_name,
        )
        self._schema = collection_jsonschema_spec
        self._raise_web_errors = raise_web_errors

        if parent_logger is not None:
            self.logger = logging.getLogger(
                f"{parent_logger.name}.db.{collection_name.lower()}"
            )
        else:
            self.logger = logging.getLogger(f"{__name__}.{collection_name.lower()}")

        self.collection_name = collection_name

    def _validate(
        self,
        instance: dict,
        allow_partial_update: bool = False,
    ) -> None:
        """Wrap `jsonschema.validate` with logic for mongo syntax."""
        try:
            jsonschema.validate(
                *_mongo_to_jsonschema_prep(instance, self._schema, allow_partial_update)
            )
        except jsonschema.exceptions.ValidationError as e:
            self.logger.exception(e)
            if self._raise_web_errors:
                raise web.HTTPError(
                    status_code=500,
                    log_message=f"{e.__class__.__name__}: {e}",  # to stderr
                    reason="Attempted to insert invalid data into database",  # to client
                ) from e
            else:
                raise

    ####################################################################
    # WRITES
    ####################################################################

    def _validate_mongo_update(self, update: dict[str, Any]) -> None:
        """Validate the data for each given mongo-syntax update operator."""
        for operator in update:
            if operator == "$set":
                self._validate(
                    update[operator],
                    allow_partial_update=True,
                )
            elif operator == "$push":
                self._validate(
                    # validate each value as if it was the whole field's list -- other wise `str != [str]`
                    {k: [v] for k, v in update[operator].items()},
                    allow_partial_update=True,
                )
            # FUTURE: insert more operators here
            else:
                raise KeyError(f"Unsupported mongo-syntax update operator: {operator}")

    async def insert_one(self, doc: dict, **kwargs: Any) -> dict:
        """Insert the doc (dict)."""
        self.logger.debug(f"inserting one: {doc}")

        self._validate(doc)
        await self._collection.insert_one(doc, **kwargs)
        # https://pymongo.readthedocs.io/en/stable/faq.html#writes-and-ids
        doc.pop("_id")

        self.logger.debug(f"inserted one: {doc}")
        return doc

    async def find_one_and_update(
        self,
        query: dict,
        update: dict,
        **kwargs: Any,
    ) -> dict:
        """Update the doc and return updated doc."""
        self.logger.debug(f"update one with query: {query}")

        self._validate_mongo_update(update)
        doc = await self._collection.find_one_and_update(
            query,
            update,
            return_document=ReturnDocument.AFTER,
            **kwargs,
        )
        if not doc:
            raise DocumentNotFoundException()

        self.logger.debug(f"updated one ({query}): {doc}")
        return doc  # type: ignore[no-any-return]

    async def insert_many(self, docs: list[dict], **kwargs: Any) -> list[dict]:
        """Insert multiple docs."""
        self.logger.debug(f"inserting many: {docs}")

        for doc in docs:
            self._validate(doc)

        await self._collection.insert_many(docs, **kwargs)
        # https://pymongo.readthedocs.io/en/stable/faq.html#writes-and-ids
        for doc in docs:
            doc.pop("_id")

        self.logger.debug(f"inserted many: {docs}")
        return docs

    async def update_many(
        self,
        query: dict,
        update: dict,
        **kwargs: Any,
    ) -> int:
        """Update all matching docs."""
        self.logger.debug(f"update many with query: {query}")

        self._validate_mongo_update(update)
        res = await self._collection.update_many(query, update, **kwargs)
        if not res.matched_count:
            raise DocumentNotFoundException()

        self.logger.debug(f"updated many: {query}")
        return res.modified_count

    ####################################################################
    # READS
    ####################################################################

    async def find_one(self, query: dict, **kwargs: Any) -> dict:
        """Find one matching the query."""
        self.logger.debug(f"finding one with query: {query}")

        doc = await self._collection.find_one(query, **kwargs)
        if not doc:
            raise DocumentNotFoundException()
        # https://pymongo.readthedocs.io/en/stable/faq.html#writes-and-ids
        doc.pop("_id")

        self.logger.debug(f"found one: {doc}")
        return doc  # type: ignore[no-any-return]

    async def find_all(
        self,
        query: dict,
        projection: list,
        **kwargs: Any,
    ) -> AsyncIterator[dict]:
        """Find all matching the query."""
        self.logger.debug(f"finding with query: {query}")

        i = 0
        async for doc in self._collection.find(query, projection, **kwargs):
            i += 1
            # https://pymongo.readthedocs.io/en/stable/faq.html#writes-and-ids
            doc.pop("_id")
            self.logger.debug(f"found {doc}")
            yield doc

        self.logger.debug(f"found {i} docs")

    async def aggregate(
        self,
        pipeline: list[dict],
        **kwargs: Any,
    ) -> AsyncIterator[dict]:
        """Find all matching the aggregate pipeline."""
        self.logger.debug(f"finding with aggregate pipeline: {pipeline}")

        i = 0
        async for doc in self._collection.aggregate(pipeline, **kwargs):
            i += 1
            # https://pymongo.readthedocs.io/en/stable/faq.html#writes-and-ids
            doc.pop("_id")
            self.logger.debug(f"found {doc}")
            yield doc

        self.logger.debug(f"found {i} docs")

    async def aggregate_one(
        self,
        pipeline: list[dict],
        **kwargs: Any,
    ) -> dict:
        """Find one matching the aggregate pipeline.

        Appends `{"$limit": 1}` to pipeline.
        """
        self.logger.debug(f"finding one with aggregate pipeline: {pipeline}")

        pipeline.append({"$limit": 1})  # optimization
        async for doc in self.aggregate(pipeline, **kwargs):
            return doc

        raise DocumentNotFoundException()


########################################################################################


def _mongo_to_jsonschema_prep(
    og_dict: dict,
    og_schema: dict,
    allow_partial_update: bool,
) -> tuple[dict, dict]:
    """Converts a mongo-style dotted dict to a nested dict with an augmented schema.

    NOTE: Does not support array/list dot-indexing

    Example:
        in:
            {"book.title": "abc", "book.content": "def", "author": "ghi"}
            {
                "type": "object",
                "properties": {
                    "author": { "type": "string" },
                    "book": {
                        "type": "object",
                        "properties": { "content": { "type": "string" } },
                        "required": [<some>]
                    },
                    "copyright": {
                        "type": "object",
                        "properties": { ... },
                        "required": [<some>]
                    },
                    ...
                },
                "required": [<some>]
            }
        out:
            {"book": {"title": "abc", "content": "def"}, "author": "ghi"}
            {
                "type": "object",
                "properties": {
                    "author": { "type": "string" },
                    "book": {
                        "type": "object",
                        "properties": { "content": { "type": "string" } },
                        "required": []  # NONE!
                    },
                    "copyright": {
                        "type": "object",
                        "properties": { ... },
                        "required": [<some>]  # not changed b/c og_key was not seen in dot notation
                    },
                    ...
                },
                "required": []  # NONE!
            }
    """
    match (allow_partial_update, any("." in k for k in og_dict.keys())):
        # yes partial & yes dots -> proceed to rest of func
        case (True, True):
            schema = copy.deepcopy(og_schema)
            schema["required"] = []
        # yes partial & no dots -> quick exit
        case (True, False):
            schema = copy.deepcopy(og_schema)
            schema["required"] = []
            return og_dict, schema
        # no partial & yes dots -> error
        case (False, True):
            raise web.HTTPError(
                500,
                log_message="Partial updating disallowed but instance contains dotted parent_keys.",
                reason="Internal database schema validation error",
            )
        # no partial & no dots -> immediate exit
        case (False, False):
            return og_dict, og_schema
        # ???
        case _other:
            raise RuntimeError(f"Unknown match: {_other}")

    # https://stackoverflow.com/a/75734554/13156561 (looping logic)
    out = {}  # type: ignore
    for og_key, value in og_dict.items():
        if "." not in og_key:
            out[og_key] = value
            continue
        else:
            # (re)set cursors to root
            cursor = out
            schema_props_cursor = schema["properties"]
            # iterate & attach keys
            *parent_keys, leaf_key = og_key.split(".")
            for k in parent_keys:
                cursor = cursor.setdefault(k, {})
                # mark nested object 'required' as none
                if schema_props_cursor:
                    # ^^^ falsy when not "in" a properties obj, ex: parent only has 'additionalProperties'
                    schema_props_cursor[k]["required"] = []
                    schema_props_cursor = schema_props_cursor[k].get("properties")
            # place value
            cursor[leaf_key] = value
    return out, schema
