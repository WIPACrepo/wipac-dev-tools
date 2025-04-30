"""Tools for interfacing with mongodb using jsonschema validation."""

import copy
import logging
from typing import Any, AsyncIterator, Callable, Union


# mongo imports
try:
    from motor.motor_asyncio import AsyncIOMotorCollection
    from pymongo import ReturnDocument
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
        collection: AsyncIOMotorCollection,
        collection_jsonschema_spec: dict[str, Any],
        parent_logger: Union[logging.Logger, None] = None,
        validation_exception_callback: Union[
            Callable[[Exception], Exception], None
        ] = None,
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

    def _validate(
        self,
        obj: dict,
        allow_partial_update: bool = False,
    ) -> None:
        """Wrap `jsonschema.validate` with logic for mongo syntax."""
        try:
            jsonschema.validate(
                *_convert_mongo_to_jsonschema(obj, self._schema, allow_partial_update)
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

    async def insert_one(
        self,
        doc: dict,
        no_id: bool = True,
        **kwargs: Any,
    ) -> dict:
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
        query: dict,
        update: dict,
        no_id: bool = True,
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
        elif no_id:
            doc.pop("_id", None)  # mongo will put "_id" -- but for testing use None

        self.logger.debug(f"updated one ({query}): {doc}")
        return doc  # type: ignore[no-any-return]

    async def insert_many(
        self,
        docs: list[dict],
        no_id: bool = True,
        **kwargs: Any,
    ) -> list[dict]:
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

    async def find_one(
        self,
        query: dict,
        no_id: bool = True,
        **kwargs: Any,
    ) -> dict:
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
        query: dict,
        projection: list,
        no_id: bool = True,
        **kwargs: Any,
    ) -> AsyncIterator[dict]:
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
        pipeline: list[dict],
        no_id: bool = True,
        **kwargs: Any,
    ) -> AsyncIterator[dict]:
        """Find all matching the aggregate pipeline."""
        self.logger.debug(f"finding with aggregate pipeline: {pipeline}")

        i = 0
        async for doc in self._collection.aggregate(pipeline, **kwargs):
            i += 1
            if no_id:
                doc.pop("_id", None)  # mongo will put "_id" -- but for testing use None
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


def _has_dotted_keys(dicto: dict[str, Any]) -> bool:
    return any("." in k for k in dicto.keys())


def _convert_mongo_to_jsonschema(
    mongo_dict: dict,
    full_jsonschema: dict,
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
                        "required": [<some>]  # not changed b/c key was not seen in dot notation
                    },
                    ...
                },
                "required": []  # NONE!
            }
    """
    if allow_partial_update:
        return _adapt_schema_for_partial_updating(mongo_dict, full_jsonschema)
    else:
        # no partial & yes dots -> error
        if _has_dotted_keys(mongo_dict):
            raise IllegalDotsNotationActionException()
        # no partial & no dots -> immediate exit
        else:
            return mongo_dict, full_jsonschema


def _adapt_schema_for_partial_updating(
    mongo_dict: dict,
    full_jsonschema: dict,
) -> tuple[dict, dict]:
    adapted_schema = copy.deepcopy(full_jsonschema)
    adapted_schema["required"] = []

    # yes partial but no dots -> quick exit
    if not _has_dotted_keys(mongo_dict):
        return mongo_dict, adapted_schema

    # https://stackoverflow.com/a/75734554/13156561 (looping logic)
    out_dict = {}  # type: ignore
    for og_key, value in mongo_dict.items():
        if "." not in og_key:
            out_dict[og_key] = value
            continue
        else:
            # (re)set cursors to root
            cursor = out_dict
            schema_props_cursor = adapted_schema["properties"]
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

    return out_dict, adapted_schema
