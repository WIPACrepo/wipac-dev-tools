"""Tools for interfacing with mongodb using jsonschema validation."""

import copy
import functools
import logging
from collections.abc import AsyncIterator, Callable
from typing import Any, TypeAlias

# mongo imports
try:
    from pymongo import ReturnDocument
    from pymongo.asynchronous.collection import AsyncCollection
except (ImportError, ModuleNotFoundError) as _exc:
    raise ImportError(
        "the 'mongo' option must be installed in order to use 'mongo_jsonschema_tools'"
    ) from _exc

# jsonschema imports
try:
    import jsonschema
except (ImportError, ModuleNotFoundError) as _exc:
    raise ImportError(
        "the 'jsonschema' option must be installed in order to use 'mongo_jsonschema_tools'"
    ) from _exc

JSON: TypeAlias = dict[str, "JSON"] | list["JSON"] | str | int | float | bool | None
MongoDoc: TypeAlias = dict[str, JSON]


class DocumentNotFoundException(Exception):
    """Raised when document is not found for a particular query."""


class IllegalDotsNotationActionException(Exception):
    """The object contains dotted keys which the mongo action disallows."""

    def __init__(self) -> None:
        super().__init__(
            "The object contains dotted keys which the mongo action disallows."
        )


class MongoJSONSchemaValidatedCollection:
    """For interacting with a mongo collection using jsonschema validation for writes.

    A `jsonschema.exceptions.ValidationError` or `IllegalDotsNotationActionException`
    instance is raised, when an object is invalid for given schema and mongo action.
    Use `validation_exception_callback` to raise a specialized exception instead;
    this callback must *return* an exception instance and should account for any/all
    exception types.

    Validation only occurs on writes--not reads.
    """

    def __init__(
        self,
        collection: AsyncCollection,
        collection_jsonschema_spec: JSON,
        parent_logger: logging.Logger | None = None,
        validation_exception_callback: Callable[[Exception], Exception] | None = None,
    ) -> None:
        self._collection = collection
        self._schema = collection_jsonschema_spec

        self.collection_name = collection.name

        if parent_logger is not None:
            self.logger = logging.getLogger(
                f"{parent_logger.name}.db.{self.collection_name.lower()}"
            )
        else:
            self.logger = logging.getLogger(
                f"{__name__}.{self.collection_name.lower()}"
            )

        self.validation_exception_callback = validation_exception_callback

    @functools.cached_property
    def _schema_cleared_root(self) -> JSON:
        """Schema deep-copy with root `required` cleared; reused for the partial-update no-dots fast path.

        Treat as immutable: callers must not mutate this value, or the cache will be
        corrupted for the instance's lifetime. `jsonschema.validate` does not mutate
        the schema it's given, so pass-through is safe.
        """
        cleared = copy.deepcopy(self._schema)
        cleared["required"] = []  # type: ignore[index]
        return cleared

    def _validate(
        self,
        obj: MongoDoc,
        allow_partial_update: bool = False,
    ) -> None:
        """Wrap `jsonschema.validate` with logic for mongo syntax."""
        try:
            jsonschema.validate(
                *_convert_mongo_to_jsonschema(
                    obj,
                    self._schema,
                    self._schema_cleared_root,
                    allow_partial_update,
                )
            )
        except Exception as e:
            self.logger.exception(e)
            if self.validation_exception_callback:
                raise self.validation_exception_callback(e) from e
            else:
                raise e

    ####################################################################
    # WRITES
    ####################################################################

    def _validate_mongo_update(self, update: MongoDoc) -> None:
        """Validate the data for each given mongo-syntax update operator."""
        for operator in update:
            if operator == "$set":
                self._validate(
                    update[operator],  # type: ignore[arg-type]
                    allow_partial_update=True,
                )
            elif operator == "$push":
                self._validate(
                    # validate each value as if it was the whole field's list -- other wise `str != [str]`
                    {k: [v] for k, v in update[operator].items()},  # type: ignore[union-attr]
                    allow_partial_update=True,
                )
            # FUTURE: insert more operators here
            else:
                raise KeyError(f"Unsupported mongo-syntax update operator: {operator}")

    async def insert_one(
        self,
        doc: MongoDoc,
        no_id: bool = True,
        **kwargs: Any,
    ) -> MongoDoc:
        """Insert the doc (dict)."""
        self.logger.debug(f"inserting one: {doc}")

        self._validate(doc)
        await self._collection.insert_one(doc, **kwargs)
        if no_id:
            doc.pop("_id", None)  # mongo will put "_id" -- but for testing use None

        self.logger.debug(f"inserted one: {doc}")
        return doc

    async def find_one_and_update(
        self,
        query: MongoDoc,
        update: MongoDoc,
        no_id: bool = True,
        **kwargs: Any,
    ) -> MongoDoc:
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
        elif no_id:
            doc.pop("_id", None)  # mongo will put "_id" -- but for testing use None

        self.logger.debug(f"updated one ({query}): {doc}")
        return doc  # type: ignore[no-any-return]

    async def insert_many(
        self,
        docs: list[MongoDoc],
        no_id: bool = True,
        **kwargs: Any,
    ) -> list[MongoDoc]:
        """Insert multiple docs."""
        self.logger.debug(f"inserting many: {docs}")

        for doc in docs:
            self._validate(doc)

        await self._collection.insert_many(docs, **kwargs)
        if no_id:
            for doc in docs:
                doc.pop("_id", None)  # mongo will put "_id" -- but for testing use None

        self.logger.debug(f"inserted many: {docs}")
        return docs

    async def update_many(
        self,
        query: MongoDoc,
        update: MongoDoc,
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

    async def find_one(
        self,
        query: MongoDoc,
        no_id: bool = True,
        **kwargs: Any,
    ) -> MongoDoc:
        """Find one matching the query."""
        self.logger.debug(f"finding one with query: {query}")

        doc = await self._collection.find_one(query, **kwargs)
        if not doc:
            raise DocumentNotFoundException()
        if no_id:
            doc.pop("_id", None)  # mongo will put "_id" -- but for testing use None

        self.logger.debug(f"found one: {doc}")
        return doc  # type: ignore[no-any-return]

    async def find_all(
        self,
        query: MongoDoc,
        projection: list[str],
        no_id: bool = True,
        **kwargs: Any,
    ) -> AsyncIterator[MongoDoc]:
        """Find all matching the query."""
        self.logger.debug(f"finding with query: {query}")

        i = 0
        async for doc in self._collection.find(query, projection, **kwargs):
            i += 1
            if no_id:
                doc.pop("_id", None)  # mongo will put "_id" -- but for testing use None
            self.logger.debug(f"found {doc}")
            yield doc

        self.logger.debug(f"found {i} docs")

    async def aggregate(
        self,
        pipeline: list[MongoDoc],
        no_id: bool = True,
        **kwargs: Any,
    ) -> AsyncIterator[MongoDoc]:
        """Find all matching the aggregate pipeline."""
        self.logger.debug(f"finding with aggregate pipeline: {pipeline}")

        # PyMongo async's AsyncCollection.aggregate() returns a coroutine
        # that must be awaited to obtain the async cursor.
        cursor = await self._collection.aggregate(pipeline, **kwargs)

        i = 0
        async for doc in cursor:
            i += 1
            if no_id:
                doc.pop("_id", None)  # mongo will put "_id" -- but for testing use None
            self.logger.debug(f"found {doc}")
            yield doc

        self.logger.debug(f"found {i} docs")

    async def aggregate_one(
        self,
        pipeline: list[MongoDoc],
        **kwargs: Any,
    ) -> MongoDoc:
        """Find one matching the aggregate pipeline.

        Appends `{"$limit": 1}` to pipeline.
        """
        self.logger.debug(f"finding one with aggregate pipeline: {pipeline}")

        pipeline.append({"$limit": 1})  # optimization
        async for doc in self.aggregate(pipeline, **kwargs):
            return doc

        raise DocumentNotFoundException()


########################################################################################


def _has_dotted_keys(dicto: MongoDoc) -> bool:
    """Return True iff any top-level key in `dicto` contains a dot."""
    return any("." in k for k in dicto.keys())


def _convert_mongo_to_jsonschema(
    mongo_dict: MongoDoc,
    full_jsonschema: JSON,
    schema_cleared_root: JSON,
    allow_partial_update: bool,
) -> tuple[MongoDoc, JSON]:
    """Prepare a Mongo-style mapping and schema for JSON Schema validation.

    For partial updates, dotted keys are expanded into nested objects and the schema is
    adapted so touched object levels no longer require unspecified sibling fields. For
    non-partial validation, dotted keys raise `IllegalDotsNotationActionException`.

    `schema_cleared_root` is the cached deep-copy of `full_jsonschema` with the root
    `required` cleared, used for the partial-update no-dots fast path.

    Returns a tuple of `(normalized_object, schema_for_validation)`.

    NOTE: Does not support array/list dot-indexing
    """
    if allow_partial_update:
        return _adapt_schema_for_partial_updating(
            mongo_dict, full_jsonschema, schema_cleared_root
        )
    else:
        # no partial & yes dots -> error
        if _has_dotted_keys(mongo_dict):
            raise IllegalDotsNotationActionException()
        # no partial & no dots -> immediate exit
        else:
            return mongo_dict, full_jsonschema


def _adapt_schema_for_partial_updating(
    mongo_dict: MongoDoc,
    full_jsonschema: JSON,
    schema_cleared_root: JSON,
) -> tuple[MongoDoc, JSON]:
    """Expand dotted update keys and relax `required` constraints for partial validation.

    Returns a nested object built from `mongo_dict` and a schema whose root `required`
    list is cleared. For dotted paths, traversed nested object schemas under
    `properties` also have `required` cleared.

    Fast path: if `mongo_dict` has no dotted keys, returns the pre-computed
    `schema_cleared_root` directly — no deep-copy. For dotted-keys, a fresh deep-copy
    of `full_jsonschema` is made so nested mutations don't leak into the cache.

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
                        "required": []  # cleared for partial validation
                    },
                    "copyright": {
                        "type": "object",
                        "properties": { ... },
                        "required": [<some>]  # unchanged because this branch was not traversed
                    },
                    ...
                },
                "required": []  # cleared for partial validation
            }
    """
    # yes partial but no dots -> fast path; reuse the cached cleared-root schema
    if not _has_dotted_keys(mongo_dict):
        return mongo_dict, schema_cleared_root

    # yes partial & yes dots -> fresh deep-copy (we will mutate nested `required` below)
    adapted_schema = copy.deepcopy(full_jsonschema)
    adapted_schema["required"] = []  # type: ignore[index]

    # https://stackoverflow.com/a/75734554/13156561 (looping logic)
    out_dict: MongoDoc = {}
    for og_key, value in mongo_dict.items():
        if "." not in og_key:
            out_dict[og_key] = value
            continue
        else:
            # (re)set cursors to root
            cursor = out_dict
            schema_props_cursor = adapted_schema["properties"]  # type: ignore[index]
            # iterate & attach keys
            *parent_keys, leaf_key = og_key.split(".")
            for k in parent_keys:
                cursor = cursor.setdefault(k, {})  # type: ignore[assignment]
                # mark nested object 'required' as none
                if schema_props_cursor:
                    # ^^^ falsy when not "in" a properties obj, ex: parent only has 'additionalProperties'
                    schema_props_cursor[k]["required"] = []
                    schema_props_cursor = schema_props_cursor[k].get("properties")
            # place value
            cursor[leaf_key] = value

    return out_dict, adapted_schema
