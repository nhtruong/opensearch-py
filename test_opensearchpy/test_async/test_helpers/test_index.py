# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.
#
# Modifications Copyright OpenSearch Contributors. See
# GitHub history for details.

import string
from random import choice

import pytest
from pytest import raises

from opensearchpy import Date, Text, analyzer
from opensearchpy._async.helpers.document import AsyncDocument
from opensearchpy._async.helpers.index import AsyncIndex

pytestmark = pytest.mark.asyncio


class Post(AsyncDocument):
    title = Text()
    published_from = Date()


async def test_multiple_doc_types_will_combine_mappings():
    class User(AsyncDocument):
        username = Text()

    i = AsyncIndex("i")
    i.document(Post)
    i.document(User)
    assert {
        "mappings": {
            "properties": {
                "title": {"type": "text"},
                "username": {"type": "text"},
                "published_from": {"type": "date"},
            }
        }
    } == i.to_dict()


async def test_search_is_limited_to_index_name():
    i = AsyncIndex("my-index")
    s = i.search()

    assert s._index == ["my-index"]


async def test_cloned_index_has_copied_settings_and_using():
    client = object()
    i = AsyncIndex("my-index", using=client)
    i.settings(number_of_shards=1)

    i2 = i.clone("my-other-index")

    assert "my-other-index" == i2._name
    assert client is i2._using
    assert i._settings == i2._settings
    assert i._settings is not i2._settings


async def test_cloned_index_has_analysis_attribute():
    """
    Regression test for Issue #582 in which `Index.clone()` was not copying
    over the `_analysis` attribute.
    """
    client = object()
    i = AsyncIndex("my-index", using=client)

    random_analyzer_name = "".join((choice(string.ascii_letters) for _ in range(100)))
    random_analyzer = analyzer(
        random_analyzer_name, tokenizer="standard", filter="standard"
    )

    i.analyzer(random_analyzer)

    i2 = i.clone("my-clone-index")

    assert i.to_dict()["settings"]["analysis"] == i2.to_dict()["settings"]["analysis"]


async def test_settings_are_saved():
    i = AsyncIndex("i")
    i.settings(number_of_replicas=0)
    i.settings(number_of_shards=1)

    assert {"settings": {"number_of_shards": 1, "number_of_replicas": 0}} == i.to_dict()


async def test_registered_doc_type_included_in_to_dict():
    i = AsyncIndex("i", using="alias")
    i.document(Post)

    assert {
        "mappings": {
            "properties": {
                "title": {"type": "text"},
                "published_from": {"type": "date"},
            }
        }
    } == i.to_dict()


async def test_registered_doc_type_included_in_search():
    i = AsyncIndex("i", using="alias")
    i.document(Post)

    s = i.search()

    assert s._doc_type == [Post]


async def test_aliases_add_to_object():
    random_alias = "".join((choice(string.ascii_letters) for _ in range(100)))
    alias_dict = {random_alias: {}}

    index = AsyncIndex("i", using="alias")
    index.aliases(**alias_dict)

    assert index._aliases == alias_dict


async def test_aliases_returned_from_to_dict():
    random_alias = "".join((choice(string.ascii_letters) for _ in range(100)))
    alias_dict = {random_alias: {}}

    index = AsyncIndex("i", using="alias")
    index.aliases(**alias_dict)

    assert index._aliases == index.to_dict()["aliases"] == alias_dict


async def test_analyzers_added_to_object():
    random_analyzer_name = "".join((choice(string.ascii_letters) for _ in range(100)))
    random_analyzer = analyzer(
        random_analyzer_name, tokenizer="standard", filter="standard"
    )

    index = AsyncIndex("i", using="alias")
    index.analyzer(random_analyzer)

    assert index._analysis["analyzer"][random_analyzer_name] == {
        "filter": ["standard"],
        "type": "custom",
        "tokenizer": "standard",
    }


async def test_analyzers_returned_from_to_dict():
    random_analyzer_name = "".join((choice(string.ascii_letters) for _ in range(100)))
    random_analyzer = analyzer(
        random_analyzer_name, tokenizer="standard", filter="standard"
    )
    index = AsyncIndex("i", using="alias")
    index.analyzer(random_analyzer)

    assert index.to_dict()["settings"]["analysis"]["analyzer"][
        random_analyzer_name
    ] == {"filter": ["standard"], "type": "custom", "tokenizer": "standard"}


async def test_conflicting_analyzer_raises_error():
    i = AsyncIndex("i")
    i.analyzer("my_analyzer", tokenizer="whitespace", filter=["lowercase", "stop"])

    with raises(ValueError):
        i.analyzer("my_analyzer", tokenizer="keyword", filter=["lowercase", "stop"])


async def test_index_template_can_have_order():
    i = AsyncIndex("i-*")
    it = i.as_template("i", order=2)

    assert {"index_patterns": ["i-*"], "order": 2} == it.to_dict()
