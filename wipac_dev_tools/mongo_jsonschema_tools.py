"""Tools for interfacing with mongodb using jsonschema validation."""

import copy
import functools
import logging
from collections.abc import AsyncIterator, Callable
from typing import Any, Final, TypeAlias, cast

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
MongoDoc: TypeAlias = dict[str, Any]  # mongo can carry ObjectId, datetime, Binary, etc


class DocumentNotFoundException(Exception):
    """Raised when document is not found for a particular query."""

    def __init__(self, collection_name: str = "") -> None:
        # NOTES:
        #   - `collection_name` is optional for backwards compatibility
        #   - don't include sensitive info in exception message
        #       > this may be logged and/or sent to a user
        super().__init__(
            f"MongoDB document not found in collection={collection_name}."
            if collection_name
            else "MongoDB document not found."
        )
        self.collection_name = collection_name


class IllegalDotsNotationActionException(Exception):
    """The object contains dotted keys which the mongo action disallows."""

    def __init__(self) -> None:
        super().__init__(
            "The object contains dotted keys which the mongo action disallows."
        )


def do_pop_id(no_id: bool, projection: dict[str, int] | list[str] | None) -> bool:
    """Return whether to pop the `_id` field from the given doc.

    If "_id" is included by the projection, it is not popped. Else, look at `no_id`.
    """
    if isinstance(projection, dict) and projection.get("_id"):  # {_id: 1} vs. {_id: 0}
        return False
    elif isinstance(projection, list) and "_id" in projection:  # ["_id"]
        return False
    else:
        return no_id


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
        self._jsonschema_transformer = _JSONSchemaTransformer(
            collection_jsonschema_spec
        )

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

    def _validate(
        self,
        mongo_obj: MongoDoc,
        allow_partial_update: bool = False,
    ) -> None:
        """Wrap `jsonschema.validate` with logic for mongo syntax."""
        try:
            json_obj, out_schema = _convert_mongo_to_jsonschema(
                mongo_obj,
                self._jsonschema_transformer,
                allow_partial_update,
            )
            jsonschema.validate(json_obj, out_schema)
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
                    update[operator],
                    allow_partial_update=True,
                )
            elif operator == "$inc":
                # Example: "$inc": {"next_attempt": 5, "i": 1}
                self._validate(
                    update[operator],
                    allow_partial_update=True,
                )
            # ARRAY OPERATORS
            elif operator == "$push":
                self._validate(
                    # validate each value as if it was the whole field's list -- other wise `str != [str]`
                    {k: [v] for k, v in update[operator].items()},
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
        if do_pop_id(no_id, kwargs.get("projection")):
            doc.pop("_id", None)

        self.logger.debug(f"inserted one: {doc}")
        return doc

    async def find_one_and_update(
        self,
        query: MongoDoc,
        update: MongoDoc,
        no_id: bool = True,
        **kwargs: Any,
    ) -> MongoDoc:
        """Update the doc and return updated doc.

        Raises `DocumentNotFoundException` if no doc is found.
        """
        self.logger.debug(f"update one with query: {query}")

        self._validate_mongo_update(update)
        doc = await self._collection.find_one_and_update(
            query,
            update,
            return_document=ReturnDocument.AFTER,
            **kwargs,
        )
        if not doc:
            raise DocumentNotFoundException(self.collection_name)
        elif do_pop_id(no_id, kwargs.get("projection")):
            doc.pop("_id", None)

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
        if do_pop_id(no_id, kwargs.get("projection")):
            for doc in docs:
                doc.pop("_id", None)

        self.logger.debug(f"inserted many: {docs}")
        return docs

    async def update_many(
        self,
        query: MongoDoc,
        update: MongoDoc,
        **kwargs: Any,
    ) -> int:
        """Update all matching docs.

        Raises `DocumentNotFoundException` if no doc is found.
        """
        self.logger.debug(f"update many with query: {query}")

        self._validate_mongo_update(update)
        res = await self._collection.update_many(query, update, **kwargs)
        if not res.matched_count:
            raise DocumentNotFoundException(self.collection_name)

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
        """Find one matching the query.

        Raises `DocumentNotFoundException` if no doc is found.
        """
        self.logger.debug(f"finding one with query: {query}")

        doc = await self._collection.find_one(query, **kwargs)
        if not doc:
            raise DocumentNotFoundException(self.collection_name)
        if do_pop_id(no_id, kwargs.get("projection")):
            doc.pop("_id", None)

        self.logger.debug(f"found one: {doc}")
        return doc  # type: ignore[no-any-return]

    async def find_one_field(
        self,
        query: MongoDoc,
        field: str,
        **kwargs: Any,
    ) -> Any:
        """Find one doc matching the query, then return the *value* of `field`.

        **WARNING**: Do not pass in dotted keys, this will raise a `ValueError`.
        The logic to support this is very complex and would need to account for various
        shapes of nested objects, including arrays and mixed types.

        Do not provide `projection` -- this method will override it with `{field: 1}`.

        Raises `DocumentNotFoundException` if no doc is found.
        """
        if "." in field:
            raise ValueError("Dotted keys are not supported for this method.")

        kwargs["projection"] = {field: 1}
        doc = await self.find_one(query, **kwargs)  # ~> DocumentNotFoundException
        return doc[field]

    async def find_all(
        self,
        query: MongoDoc,
        projection: list[str] | dict[str, int],
        no_id: bool = True,
        **kwargs: Any,
    ) -> AsyncIterator[MongoDoc]:
        """Find all matching the query.

        Argument `projection` is required to emphasize this could return A LOT of data.

        Yields nothing if no docs are found.
        """
        self.logger.debug(f"finding with query: {query}")

        pop_id = do_pop_id(no_id, projection)  # invariant per-call; compute once
        i = 0
        async for doc in self._collection.find(query, projection, **kwargs):
            i += 1
            if pop_id:
                doc.pop("_id", None)
            self.logger.debug(f"found {doc}")
            yield doc

        self.logger.debug(f"found {i} docs")

    async def aggregate(
        self,
        pipeline: list[MongoDoc],
        no_id: bool = True,
        **kwargs: Any,
    ) -> AsyncIterator[MongoDoc]:
        """Find all matching the aggregate pipeline.

        Yields nothing if no docs are found.
        """
        self.logger.debug(f"finding with aggregate pipeline: {pipeline}")

        # PyMongo async's AsyncCollection.aggregate() returns a coroutine
        # that must be awaited to obtain the async cursor.
        cursor = await self._collection.aggregate(pipeline, **kwargs)

        i = 0
        async for doc in cursor:
            i += 1
            if do_pop_id(no_id, kwargs.get("projection")):
                doc.pop("_id", None)
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

        Raises `DocumentNotFoundException` if no doc is found.
        """
        self.logger.debug(f"finding one with aggregate pipeline: {pipeline}")

        pipeline.append({"$limit": 1})  # optimization
        async for doc in self.aggregate(pipeline, **kwargs):
            return doc

        raise DocumentNotFoundException(self.collection_name)


########################################################################################


def _has_dotted_keys(dicto: MongoDoc) -> bool:
    """Return True iff any top-level key in `dicto` contains a dot."""
    return any("." in k for k in dicto.keys())


def _convert_mongo_to_jsonschema(
    mongo_dict: MongoDoc,
    jsonschema_transformer: "_JSONSchemaTransformer",
    allow_partial_update: bool,
) -> tuple[MongoDoc, dict[str, Any]]:
    """Prepare a Mongo-style mapping and schema for JSON Schema validation.

    For partial updates, dotted keys are expanded into nested objects and the schema is
    adapted so touched object levels no longer require unspecified sibling fields. For
    non-partial validation, dotted keys raise `IllegalDotsNotationActionException`.

    Returns a tuple of `(normalized_object, schema_for_validation)`.

    NOTE: Does not support array/list dot-indexing
    """
    if allow_partial_update:
        return (
            _mongo_expand_dotted_keys(mongo_dict),
            jsonschema_transformer.unrequire_key_ancestors(mongo_dict),
        )
    else:
        # no partial & yes dots -> error
        if _has_dotted_keys(mongo_dict):
            raise IllegalDotsNotationActionException()
        # no partial & no dots ->  no adaptations needed
        else:
            return mongo_dict, jsonschema_transformer.full_schema


class _JSONSchemaTransformer:
    """Holds a jsonschema spec plus a cached builder for partial-update variants."""

    def __init__(self, full_schema: JSON) -> None:
        # deep-copy so external mutation can't corrupt cached schemas;
        # narrow JSON->dict since jsonschema specs are always objects at the root
        self.full_schema: Final[dict[str, Any]] = cast(
            dict[str, Any], copy.deepcopy(full_schema)
        )

    def unrequire_key_ancestors(self, mongo_dict: MongoDoc) -> dict[str, Any]:
        """Return a deep-copy of `self.full_schema` with `required` cleared at the root
        and along each dotted key's parent chain. Treat as immutable.

        Example:
            in:
                {"book.title": "abc", "book.content": "def", "author": "ghi"}
            self.full_schema:
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
        return self._unrequire_key_ancestors(
            frozenset(k for k in mongo_dict if "." in k)
        )

    @functools.lru_cache(maxsize=64)
    def _unrequire_key_ancestors(self, dotted_keys: frozenset[str]) -> dict[str, Any]:
        """Cached builder for `unrequire_key_ancestors()`.

        `frozenset` key makes cache hits order- and value-independent; `frozenset()`
        is the no-dotted-keys case.
        """
        schema: dict[str, Any] = copy.deepcopy(self.full_schema)  # expensive
        schema["required"] = []
        for dkey in dotted_keys:
            # (re)set schema cursor to root for each key
            schema_props_cursor: dict[str, Any] | None = schema["properties"]
            # leaf is the value slot, not a nested container to descend into
            *parent_keys, _leaf_key = dkey.split(".")
            for k in parent_keys:
                # stop descending if we can't:
                # - cursor falsy -> parent has no 'properties' (ex: only 'additionalProperties')
                # - k not declared -> free-form region, jsonschema won't enforce `required` here anyway
                if not schema_props_cursor or k not in schema_props_cursor:
                    break
                # mark nested object 'required' as none
                schema_props_cursor[k]["required"] = []
                schema_props_cursor = schema_props_cursor[k].get("properties")
        return schema


def _mongo_expand_dotted_keys(mongo_dict: MongoDoc) -> MongoDoc:
    """Expand dotted update keys into a nested object for partial validation.

    Non-dotted keys pass through unchanged.

    NOTE: Does not support array/list dot-indexing

    Example:
        in:
            {"book.title": "abc", "book.content": "def", "author": "ghi"}
        out:
            {"book": {"title": "abc", "content": "def"}, "author": "ghi"}
    """
    # yes partial but no dots -> quick exit
    if not _has_dotted_keys(mongo_dict):
        return mongo_dict

    # https://stackoverflow.com/a/75734554/13156561 (looping logic)
    out_dict: MongoDoc = {}
    for og_key, value in mongo_dict.items():
        if "." not in og_key:
            out_dict[og_key] = value
            continue
        else:
            # (re)set cursor to root
            cursor = out_dict
            # iterate & attach keys
            *parent_keys, leaf_key = og_key.split(".")
            for k in parent_keys:
                cursor = cursor.setdefault(k, {})
            # place value
            cursor[leaf_key] = value

    return out_dict
